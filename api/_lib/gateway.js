"use strict";

const crypto = require("node:crypto");
const net = require("node:net");
const dns = require("node:dns/promises");
const https = require("node:https");

const COOKIE = "__Host-linuxcore_session";
const SESSION_SECONDS = 8 * 60 * 60;
const MAX_BODY_BYTES = 128 * 1024;
const MAX_RESPONSE_BYTES = 2 * 1024 * 1024;
const UPSTREAM_TIMEOUT_MS = 55000;
const LOGIN_MAX_CLIENTS = 2048;
const LOGIN_WINDOW_SECONDS = 15 * 60;
const LOGIN_MAX_ATTEMPTS = 5;
const loginAttempts = new Map();

const blockedIPv4 = new net.BlockList();
[
  ["0.0.0.0", 8], ["10.0.0.0", 8], ["100.64.0.0", 10], ["127.0.0.0", 8],
  ["169.254.0.0", 16], ["172.16.0.0", 12], ["192.0.0.0", 24],
  ["192.0.2.0", 24], ["192.88.99.0", 24], ["192.168.0.0", 16],
  ["198.18.0.0", 15], ["198.51.100.0", 24], ["203.0.113.0", 24],
  ["224.0.0.0", 4], ["240.0.0.0", 4]
].forEach(([address, prefix]) => blockedIPv4.addSubnet(address, prefix, "ipv4"));

const blockedIPv6 = new net.BlockList();
[
  ["::", 128], ["::1", 128], ["::ffff:0:0", 96], ["64:ff9b:1::", 48],
  ["100::", 64], ["2001:db8::", 32], ["fc00::", 7], ["fe80::", 10], ["ff00::", 8]
].forEach(([address, prefix]) => blockedIPv6.addSubnet(address, prefix, "ipv6"));
const nonGlobalIPv6 = new net.BlockList();
[["::", 3], ["4000::", 2], ["8000::", 1]].forEach(([address, prefix]) =>
  nonGlobalIPv6.addSubnet(address, prefix, "ipv6")
);

const API_RULES = [
  [/^\/api\/v1\/(health|metrics|diagnostics|storage|processes|network)$/, "GET"],
  [/^\/api\/v1\/services$/, "GET"],
  [/^\/api\/v1\/services\/[A-Za-z0-9_.@:-]+\/action$/, "POST"],
  [/^\/api\/v1\/containers$/, "GET"],
  [/^\/api\/v1\/containers\/[A-Za-z0-9_.-]+\/action$/, "POST"],
  [/^\/api\/v1\/terminal\/commands$/, "GET"],
  [/^\/api\/v1\/terminal\/run$/, "POST"],
  [/^\/api\/v1\/recovery\/check$/, "GET"],
  [/^\/api\/v1\/recovery\/run$/, "POST"],
  [/^\/api\/v1\/ai\/status$/, "GET"],
  [/^\/api\/v1\/ai\/chat$/, "POST"]
];

function digest(value) {
  return crypto.createHash("sha256").update(String(value)).digest();
}

function safeEqual(left, right) {
  const a = digest(left);
  const b = digest(right);
  return crypto.timingSafeEqual(a, b) &&
    String(left).length === String(right).length;
}

function sign(value, secret) {
  return crypto.createHmac("sha256", secret).update(value).digest("base64url");
}

function sessionCookie(secret, now) {
  const payload = Buffer.from(JSON.stringify({ iat: now })).toString("base64url");
  return payload + "." + sign(payload, secret);
}

function validSession(cookie, secret, now) {
  if (!cookie || !secret || secret.length < 32) return false;
  const parts = cookie.split(".");
  if (parts.length !== 2 || !safeEqual(parts[1], sign(parts[0], secret))) return false;
  try {
    const payload = JSON.parse(Buffer.from(parts[0], "base64url").toString("utf8"));
    return Number.isSafeInteger(payload.iat) &&
      payload.iat <= now + 60 &&
      now - payload.iat >= 0 &&
      now - payload.iat < SESSION_SECONDS;
  } catch (_) {
    return false;
  }
}

function readCookie(header, name) {
  for (const part of String(header || "").split(";")) {
    const index = part.indexOf("=");
    if (index < 0) continue;
    if (part.slice(0, index).trim() === name) return part.slice(index + 1).trim();
  }
  return "";
}

function json(res, status, body, extraHeaders) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store, max-age=0");
  res.setHeader("Pragma", "no-cache");
  res.setHeader("X-Content-Type-Options", "nosniff");
  for (const [key, value] of Object.entries(extraHeaders || {})) res.setHeader(key, value);
  res.end(JSON.stringify(body));
}

function bodyBuffer(req) {
  if (Buffer.isBuffer(req.body)) return req.body;
  if (typeof req.body === "string") return Buffer.from(req.body);
  if (req.body && typeof req.body === "object") return Buffer.from(JSON.stringify(req.body));
  return Buffer.alloc(0);
}

function requestPath(req) {
  const parts = req.query && req.query.path;
  if (!Array.isArray(parts) || !parts.length) return "";
  if (parts.some((part) => typeof part !== "string" || !part || part === "." || part === ".." || part.includes("/") || part.includes("\\"))) return "";
  return "/api/" + parts.join("/");
}

function validOrigin(req) {
  const origin = req.headers && req.headers.origin;
  const host = req.headers && req.headers.host;
  if (!origin || !host) return false;
  try {
    const parsed = new URL(origin);
    return parsed.protocol === "https:" && parsed.host.toLowerCase() === String(host).toLowerCase();
  } catch (_) {
    return false;
  }
}

function isPublicAddress(address) {
  const family = net.isIP(address);
  if (family === 4) return !blockedIPv4.check(address, "ipv4");
  if (family === 6) return !blockedIPv6.check(address, "ipv6") &&
    !nonGlobalIPv6.check(address, "ipv6");
  return false;
}

function safeUpstream(value) {
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.username || url.password || url.search || url.hash) return null;
    const hostValue = url.hostname.toLowerCase();
    const host = hostValue.startsWith("[") ? hostValue.slice(1, -1) : hostValue;
    if (net.isIP(host) || !host.includes(".") ||
        host === "localhost" || host.endsWith(".localhost") ||
        host.endsWith(".local") || host.endsWith(".internal") ||
        host.endsWith(".lan") || host.endsWith(".home.arpa")) return null;
    url.pathname = url.pathname.replace(/\/+$/, "");
    return url;
  } catch (_) {
    return null;
  }
}

function loginRateLimited(req, now) {
  const suppliedIp = String((req.headers || {})["x-real-ip"] || "").trim();
  const clientIp = net.isIP(suppliedIp) ? suppliedIp : "";
  // Vercel's edge IP header is optional in local tests; platform WAF remains the
  // authoritative shared rate limiter because serverless instances are ephemeral.
  if (!clientIp) return false;

  for (const [client, entry] of loginAttempts) {
    if (now - entry.start >= LOGIN_WINDOW_SECONDS || now < entry.start) loginAttempts.delete(client);
  }

  const key = clientIp;
  let current = loginAttempts.get(key);
  if (!current && loginAttempts.size >= LOGIN_MAX_CLIENTS) {
    const oldest = loginAttempts.keys().next().value;
    if (oldest !== undefined) loginAttempts.delete(oldest);
  }
  if (!current) current = { count: 0, start: now };
  if (now - current.start >= LOGIN_WINDOW_SECONDS || now < current.start) {
    current.count = 0;
    current.start = now;
  }
  current.count += 1;
  loginAttempts.delete(key);
  loginAttempts.set(key, current);
  return current.count > LOGIN_MAX_ATTEMPTS;
}

function readBoundedBody(stream, limit = MAX_RESPONSE_BYTES) {
  return (async () => {
    const chunks = [];
    let total = 0;
    for await (const chunk of stream) {
      const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
      if (total + bytes.length > limit) {
        if (typeof stream.destroy === "function") stream.destroy();
        const error = new Error("Upstream response exceeded the gateway limit.");
        error.code = "ERR_UPSTREAM_RESPONSE_TOO_LARGE";
        throw error;
      }
      total += bytes.length;
      chunks.push(bytes);
    }
    return Buffer.concat(chunks, total);
  })();
}

function requestPinned(requestImpl, target, requestOptions, addressEntry) {
  return new Promise((resolve, reject) => {
    const hostname = target.hostname;
    const family = addressEntry.family || net.isIP(addressEntry.address);
    const pinnedLookup = (requestedHostname, lookupOptions, callback) => {
      if (String(requestedHostname).toLowerCase() !== hostname.toLowerCase()) {
        callback(new Error("Unexpected upstream lookup hostname."));
        return;
      }
      const resolved = { address: addressEntry.address, family };
      if (lookupOptions && lookupOptions.all) callback(null, [resolved]);
      else callback(null, resolved.address, resolved.family);
    };

    const request = requestImpl(target, {
      method: requestOptions.method,
      headers: requestOptions.headers,
      agent: false,
      servername: hostname,
      rejectUnauthorized: true,
      lookup: pinnedLookup,
      timeout: UPSTREAM_TIMEOUT_MS
    }, (response) => {
      readBoundedBody(response).then((body) => {
        resolve({
          statusCode: response.statusCode || 502,
          headers: response.headers || {},
          body
        });
      }).catch(reject);
    });

    request.on("error", reject);
    request.on("timeout", () => request.destroy(new Error("LinuxCore upstream timed out.")));
    if (requestOptions.body && requestOptions.body.length) request.write(requestOptions.body);
    request.end();
  });
}

function createGatewayHandler(options) {
  const env = options.env || process.env;
  const requestImpl = options.requestImpl || https.request;
  const lookupImpl = options.lookupImpl || ((hostname, settings) => dns.lookup(hostname, settings));
  const now = options.now || (() => Math.floor(Date.now() / 1000));

  return async function gateway(req, res) {
    const method = String(req.method || "GET").toUpperCase();
    const path = requestPath(req);
    const secret = String(env.LINUXCORE_SESSION_SECRET || "");
    const password = String(env.LINUXCORE_LOGIN_PASSWORD || "");
    const token = String(env.LINUXCORE_ACCESS_TOKEN || "");
    const cookie = readCookie(req.headers && req.headers.cookie, COOKIE);
    const authenticated = validSession(cookie, secret, now());

    if (path === "/api/auth/session") {
      if (method !== "GET") return json(res, 405, { detail: "Method not allowed." }, { Allow: "GET" });
      return json(res, 200, { authenticated });
    }

    if (path === "/api/auth/login") {
      if (method !== "POST") return json(res, 405, { detail: "Method not allowed." }, { Allow: "POST" });
      if (!validOrigin(req)) return json(res, 403, { detail: "Request origin rejected." });
      if (loginRateLimited(req, now())) return json(res, 429, { detail: "Too many sign-in attempts. Try again later." }, { "Retry-After": String(LOGIN_WINDOW_SECONDS) });
      if (secret.length < 32 || password.length < 12) return json(res, 503, { detail: "Gateway login is not configured securely." });
      const raw = bodyBuffer(req);
      if (raw.length > 4096) return json(res, 413, { detail: "Request body too large." });
      let input;
      try { input = JSON.parse(raw.toString("utf8")); } catch (_) { return json(res, 400, { detail: "Invalid JSON body." }); }
      if (!input || typeof input.password !== "string" || input.password.length > 256 ||
          !safeEqual(input.password, password)) {
        return json(res, 401, { detail: "Invalid password." });
      }
      const value = sessionCookie(secret, now());
      return json(res, 200, { authenticated: true }, {
        "Set-Cookie": COOKIE + "=" + value + "; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=" + SESSION_SECONDS
      });
    }

    if (path === "/api/auth/logout") {
      if (method !== "POST") return json(res, 405, { detail: "Method not allowed." }, { Allow: "POST" });
      if (!validOrigin(req)) return json(res, 403, { detail: "Request origin rejected." });
      if (!authenticated) return json(res, 200, { authenticated: false }, {
        "Set-Cookie": COOKIE + "=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0"
      });
      return json(res, 200, { authenticated: false }, {
        "Set-Cookie": COOKIE + "=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0"
      });
    }

    if (!path.startsWith("/api/v1/")) return json(res, 404, { detail: "Not found." });
    if (method === "POST" && !validOrigin(req)) return json(res, 403, { detail: "Request origin rejected." });
    if (!authenticated) return json(res, 401, { detail: "Authentication required." });
    const rule = API_RULES.find(([pattern, allowedMethod]) => pattern.test(path) && allowedMethod === method);
    if (!rule) return json(res, 404, { detail: "API route or method is not allowed by the gateway." });
    if (!token || token.length < 32) return json(res, 503, { detail: "Upstream API authentication is not configured." });

    const upstream = safeUpstream(env.LINUXCORE_UPSTREAM_URL);
    if (!upstream) return json(res, 503, { detail: "A valid HTTPS LinuxCore upstream is not configured." });

    const rawBody = method === "POST" ? bodyBuffer(req) : Buffer.alloc(0);
    if (rawBody.length > MAX_BODY_BYTES) return json(res, 413, { detail: "Request body too large." });
    if (method === "POST" && rawBody.length && !/^application\/json(?:;|$)/i.test(String(req.headers["content-type"] || ""))) {
      return json(res, 415, { detail: "Only JSON request bodies are accepted." });
    }

    let resolvedAddresses;
    try {
      resolvedAddresses = await lookupImpl(upstream.hostname, { all: true, verbatim: true });
    } catch (_) {
      return json(res, 502, { detail: "LinuxCore upstream hostname could not be resolved." });
    }
    if (!Array.isArray(resolvedAddresses) || resolvedAddresses.length === 0 ||
        resolvedAddresses.some((entry) => !entry || !isPublicAddress(entry.address) ||
          (entry.family !== undefined && entry.family !== net.isIP(entry.address)))) {
      return json(res, 503, { detail: "LinuxCore upstream must resolve only to public IP addresses." });
    }

    const basePath = upstream.pathname.replace(/\\/+$/, "");
    const target = new URL(basePath + path, upstream.origin);
    let upstreamResponse;
    try {
      upstreamResponse = await requestPinned(requestImpl, target, {
        method,
        headers: {
          "Authorization": "Bearer " + token,
          "Accept": "application/json",
          ...(method === "POST" ? { "Content-Type": "application/json" } : {})
        },
        body: method === "POST" ? rawBody : Buffer.alloc(0)
      }, resolvedAddresses[0]);
    } catch (error) {
      if (error && error.code === "ERR_UPSTREAM_RESPONSE_TOO_LARGE") {
        return json(res, 502, { detail: "Upstream response exceeded the gateway limit." });
      }
      return json(res, 502, { detail: "LinuxCore upstream is unavailable." });
    }

    res.statusCode = upstreamResponse.statusCode;
    res.setHeader("Content-Type", upstreamResponse.headers["content-type"] || "application/json");
    res.setHeader("Cache-Control", "no-store, max-age=0");
    res.setHeader("Pragma", "no-cache");
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.end(upstreamResponse.body);
  };
}

module.exports = {
  COOKIE, SESSION_SECONDS, API_RULES, createGatewayHandler, loginRateLimited,
  validSession, safeUpstream, isPublicAddress, requestPath, validOrigin
};

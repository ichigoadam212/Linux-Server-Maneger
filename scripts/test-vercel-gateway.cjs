"use strict";

const test = require("node:test");
const { EventEmitter } = require("node:events");
const { Readable } = require("node:stream");
const assert = require("node:assert/strict");
const { createGatewayHandler, validSession, safeUpstream, isPublicAddress, requestPath, loginRateLimited } = require("../api/_lib/gateway");

const NOW = 1_800_000_000;
const ENV = {
  LINUXCORE_LOGIN_PASSWORD: "correct-horse-battery-staple",
  LINUXCORE_SESSION_SECRET: "s".repeat(48),
  LINUXCORE_ACCESS_TOKEN: "t".repeat(48),
  LINUXCORE_UPSTREAM_URL: "https://linuxcore.example.net"
};

function response() {
  return {
    headers: {},
    setHeader(name, value) { this.headers[name.toLowerCase()] = value; },
    end(value) { this.body = value; this.ended = true; }
  };
}

function request(path, method, options = {}) {
  return {
    method: method || "GET",
    query: { path: path.split("/").filter(Boolean).slice(1) },
    headers: {
      host: "preview.example.vercel.app",
      origin: "https://preview.example.vercel.app",
      ...(options.headers || {})
    },
    body: options.body
  };
}

async function invoke(handler, req) {
  const res = response();
  await handler(req, res);
  return { status: res.statusCode, headers: res.headers, body: res.body ? JSON.parse(res.body.toString()) : null };
}

function makeTransport(options = {}) {
  let captured = null;
  let responseStream = null;
  const requestImpl = (url, requestOptions, callback) => {
    captured = { url: String(url), options: requestOptions, body: Buffer.alloc(0) };
    const request = new EventEmitter();
    request.write = (chunk) => {
      captured.body = Buffer.concat([captured.body, Buffer.from(chunk)]);
      return true;
    };
    request.end = () => {
      const chunks = options.chunks || [Buffer.from(options.body || '{"status":"ok"}')];
      responseStream = Readable.from(chunks);
      responseStream.statusCode = options.status || 200;
      responseStream.headers = options.headers || { "content-type": "application/json" };
      callback(responseStream);
    };
    request.destroy = (error) => {
      if (error) request.emit("error", error);
    };
    return request;
  };
  return {
    requestImpl,
    get captured() { return captured; },
    get responseStream() { return responseStream; }
  };
}

test("session signatures expire and reject tampering", () => {
  const handler = createGatewayHandler({ env: ENV, now: () => NOW });
  assert.equal(validSession("", ENV.LINUXCORE_SESSION_SECRET, NOW), false);
  assert.equal(safeUpstream("http://linuxcore.example.net"), null);
  assert.equal(safeUpstream("https://127.0.0.1:8000"), null);
  assert.equal(safeUpstream("https://[::1]:8000"), null);
  assert.equal(isPublicAddress("8.8.8.8"), true);
  assert.equal(isPublicAddress("10.0.0.8"), false);
  assert.equal(isPublicAddress("169.254.1.2"), false);
  assert.equal(isPublicAddress("::1"), false);
  assert.equal(isPublicAddress("fc00::1"), false);
  assert.equal(isPublicAddress("2606:4700:4700::1111"), true);
  assert.equal(requestPath({ query: { path: ["v1", "..", "metrics"] } }), "");
});

test("login creates a secure HttpOnly SameSite=Strict session cookie", async () => {
  const handler = createGatewayHandler({ env: ENV, now: () => NOW });
  const result = await invoke(handler, request("/api/auth/login", "POST", {
    body: { password: ENV.LINUXCORE_LOGIN_PASSWORD }
  }));
  assert.equal(result.status, 200);
  assert.equal(result.body.authenticated, true);
  const cookie = result.headers["set-cookie"];
  assert.match(cookie, /HttpOnly/);
  assert.match(cookie, /Secure/);
  assert.match(cookie, /SameSite=Strict/);
  assert.match(cookie, /Path=\//);
});

test("login rejects invalid password and cross-origin requests", async () => {
  const handler = createGatewayHandler({ env: ENV, now: () => NOW });
  const wrong = await invoke(handler, request("/api/auth/login", "POST", { body: { password: "wrong-password" } }));
  assert.equal(wrong.status, 401);
  const cross = request("/api/auth/login", "POST", { body: { password: ENV.LINUXCORE_LOGIN_PASSWORD } });
  cross.headers.origin = "https://attacker.invalid";
  const rejected = await invoke(handler, cross);
  assert.equal(rejected.status, 403);
});

test("session endpoint reports unauthenticated without leaking details", async () => {
  const handler = createGatewayHandler({ env: ENV, now: () => NOW });
  const result = await invoke(handler, request("/api/auth/session"));
  assert.deepEqual(result.body, { authenticated: false });
  assert.equal(result.headers["cache-control"], "no-store, max-age=0");
});

test("API proxy pins its HTTPS connection to the validated DNS address", async () => {
  let dnsLookups = 0;
  const transport = makeTransport({ body: '{"status":"ok"}' });
  const handler = createGatewayHandler({
    env: ENV,
    now: () => NOW,
    lookupImpl: async () => {
      dnsLookups += 1;
      return [{ address: "93.184.216.34", family: 4 }];
    },
    requestImpl: transport.requestImpl
  });
  const unauthenticated = await invoke(handler, request("/api/v1/health"));
  assert.equal(unauthenticated.status, 401);

  const login = await invoke(handler, request("/api/auth/login", "POST", {
    body: { password: ENV.LINUXCORE_LOGIN_PASSWORD }
  }));
  const cookie = login.headers["set-cookie"].split(";")[0];
  const authorized = await invoke(handler, request("/api/v1/health", "GET", { headers: { cookie } }));
  assert.equal(authorized.status, 200);
  assert.deepEqual(authorized.body, { status: "ok" });
  assert.equal(dnsLookups, 1);
  assert.equal(transport.captured.url, "https://linuxcore.example.net/api/v1/health");
  assert.equal(transport.captured.options.headers.Authorization, "Bearer " + ENV.LINUXCORE_ACCESS_TOKEN);
  assert.equal(transport.captured.options.agent, false);
  assert.equal(transport.captured.options.servername, "linuxcore.example.net");
  assert.equal(transport.captured.options.rejectUnauthorized, true);
  assert.equal(transport.captured.options.timeout, 55000);

  const pinned = await new Promise((resolve, reject) => {
    transport.captured.options.lookup("linuxcore.example.net", {}, (error, address, family) => {
      if (error) reject(error);
      else resolve({ address, family });
    });
  });
  assert.deepEqual(pinned, { address: "93.184.216.34", family: 4 });
  const allPinned = await new Promise((resolve, reject) => {
    transport.captured.options.lookup("linuxcore.example.net", { all: true }, (error, addresses) => {
      if (error) reject(error);
      else resolve(addresses);
    });
  });
  assert.deepEqual(allPinned, [{ address: "93.184.216.34", family: 4 }]);
});

test("proxy forwards allowlisted JSON POST bodies with the server-side token", async () => {
  const transport = makeTransport({ body: '{"accepted":true}' });
  const handler = createGatewayHandler({
    env: ENV,
    now: () => NOW,
    lookupImpl: async () => [{ address: "93.184.216.34", family: 4 }],
    requestImpl: transport.requestImpl
  });
  const login = await invoke(handler, request("/api/auth/login", "POST", {
    body: { password: ENV.LINUXCORE_LOGIN_PASSWORD }
  }));
  const cookie = login.headers["set-cookie"].split(";")[0];
  const payload = JSON.stringify({ action: "restart" });
  const result = await invoke(handler, request("/api/v1/services/test.service/action", "POST", {
    headers: { cookie, "content-type": "application/json" },
    body: payload
  }));
  assert.equal(result.status, 200);
  assert.deepEqual(result.body, { accepted: true });
  assert.equal(transport.captured.options.method, "POST");
  assert.equal(transport.captured.options.headers["Content-Type"], "application/json");
  assert.equal(transport.captured.options.headers.Authorization, "Bearer " + ENV.LINUXCORE_ACCESS_TOKEN);
  assert.equal(transport.captured.body.toString(), payload);
});

test("managed LinuxCore inventory and action routes are allowlisted", async () => {
  const transport = makeTransport({ body: '{"available":true,"items":[]}' });
  const handler = createGatewayHandler({
    env: ENV,
    now: () => NOW,
    lookupImpl: async () => [{ address: "93.184.216.34", family: 4 }],
    requestImpl: transport.requestImpl
  });
  const login = await invoke(handler, request("/api/auth/login", "POST", {
    body: { password: ENV.LINUXCORE_LOGIN_PASSWORD }
  }));
  const cookie = login.headers["set-cookie"].split(";")[0];

  const inventory = await invoke(handler, request("/api/v1/managed-services", "GET", {
    headers: { cookie }
  }));
  assert.equal(inventory.status, 200);
  assert.equal(transport.captured.url, "https://linuxcore.example.net/api/v1/managed-services");

  const payload = JSON.stringify({ action: "restart" });
  const action = await invoke(handler, request("/api/v1/managed-services/action", "POST", {
    headers: { cookie, "content-type": "application/json" },
    body: payload
  }));
  assert.equal(action.status, 200);
  assert.equal(transport.captured.url, "https://linuxcore.example.net/api/v1/managed-services/action");
  assert.equal(transport.captured.options.method, "POST");
  assert.equal(transport.captured.body.toString(), payload);
});

test("proxy rejects unlisted endpoints, wrong methods, and oversized bodies", async () => {
  const handler = createGatewayHandler({ env: ENV, now: () => NOW });
  const login = await invoke(handler, request("/api/auth/login", "POST", {
    body: { password: ENV.LINUXCORE_LOGIN_PASSWORD }
  }));
  const cookie = login.headers["set-cookie"].split(";")[0];
  const badPath = await invoke(handler, request("/api/v1/admin", "GET", { headers: { cookie } }));
  assert.equal(badPath.status, 404);
  const badMethod = await invoke(handler, request("/api/v1/metrics", "POST", {
    headers: { cookie, "content-type": "application/json" }, body: { anything: true }
  }));
  assert.equal(badMethod.status, 404);
  const large = await invoke(handler, request("/api/v1/ai/chat", "POST", {
    headers: { cookie, "content-type": "application/json" }, body: "x".repeat(140_000)
  }));
  assert.equal(large.status, 413);
});

test("logout expires the session cookie", async () => {
  const handler = createGatewayHandler({ env: ENV, now: () => NOW });
  const result = await invoke(handler, request("/api/auth/logout", "POST"));
  assert.equal(result.status, 200);
  assert.match(result.headers["set-cookie"], /Max-Age=0/);
});


test("gateway fails closed when server-side secrets are missing", async () => {
  const handler = createGatewayHandler({ env: {}, now: () => NOW });
  const login = await invoke(handler, request("/api/auth/login", "POST", {
    body: { password: "not-a-real-password" }
  }));
  assert.equal(login.status, 503);
});

test("login throttle blocks repeated attempts from one edge client", async () => {
  const handler = createGatewayHandler({ env: ENV, now: () => NOW });
  let last;
  for (let attempt = 0; attempt < 6; attempt += 1) {
    last = await invoke(handler, request("/api/auth/login", "POST", {
      headers: { "x-real-ip": "203.0.113.77" },
      body: { password: "wrong-password" }
    }));
  }
  assert.equal(last.status, 429);
});


test("proxy refuses DNS names resolving to private or mixed public/private addresses", async () => {
  let fetchCalled = false;
  const handler = createGatewayHandler({
    env: ENV,
    now: () => NOW,
    lookupImpl: async () => [
      { address: "93.184.216.34", family: 4 },
      { address: "10.0.0.12", family: 4 }
    ],
    requestImpl: () => {
      fetchCalled = true;
      throw new Error("Transport must not be called for a mixed DNS answer.");
    }
  });
  const login = await invoke(handler, request("/api/auth/login", "POST", {
    body: { password: ENV.LINUXCORE_LOGIN_PASSWORD }
  }));
  const cookie = login.headers["set-cookie"].split(";")[0];
  const result = await invoke(handler, request("/api/v1/health", "GET", { headers: { cookie } }));
  assert.equal(result.status, 503);
  assert.equal(fetchCalled, false);
});

test("upstream response limit is enforced while streaming", async () => {
  const transport = makeTransport({
    chunks: [Buffer.alloc(2 * 1024 * 1024), Buffer.from("x")]
  });
  const handler = createGatewayHandler({
    env: ENV,
    now: () => NOW,
    lookupImpl: async () => [{ address: "93.184.216.34", family: 4 }],
    requestImpl: transport.requestImpl
  });
  const login = await invoke(handler, request("/api/auth/login", "POST", {
    body: { password: ENV.LINUXCORE_LOGIN_PASSWORD }
  }));
  const cookie = login.headers["set-cookie"].split(";")[0];
  const result = await invoke(handler, request("/api/v1/health", "GET", { headers: { cookie } }));
  assert.equal(result.status, 502);
  assert.match(result.body.detail, /response exceeded the gateway limit/i);
  assert.equal(transport.responseStream.destroyed, true);
});

test("login attempt storage stays bounded when clients vary their IP", () => {
  const first = "2001:db8:ffff::1";
  assert.equal(loginRateLimited({ headers: { "x-real-ip": first } }, NOW), false);
  for (let index = 0; index < 2100; index += 1) {
    const ip = "2001:db8:1::" + (index + 1).toString(16);
    loginRateLimited({ headers: { "x-real-ip": ip } }, NOW);
  }
  for (let attempt = 0; attempt < 5; attempt += 1) {
    assert.equal(loginRateLimited({ headers: { "x-real-ip": first } }, NOW), false);
  }
  assert.equal(loginRateLimited({ headers: { "x-real-ip": first } }, NOW), true);
  assert.equal(loginRateLimited({ headers: { "x-real-ip": "not-an-ip" } }, NOW), false);
});

test("proxy fails closed when upstream DNS resolution fails", async () => {
  const handler = createGatewayHandler({
    env: ENV,
    now: () => NOW,
    lookupImpl: async () => { throw new Error("DNS unavailable"); },
    requestImpl: () => { throw new Error("Transport must not be called after DNS failure."); }
  });
  const login = await invoke(handler, request("/api/auth/login", "POST", {
    body: { password: ENV.LINUXCORE_LOGIN_PASSWORD }
  }));
  const cookie = login.headers["set-cookie"].split(";")[0];
  const result = await invoke(handler, request("/api/v1/health", "GET", { headers: { cookie } }));
  assert.equal(result.status, 502);
});

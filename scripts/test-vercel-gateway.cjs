"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { createGatewayHandler, validSession, safeUpstream, requestPath } = require("../api/_lib/gateway");

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

test("session signatures expire and reject tampering", () => {
  const handler = createGatewayHandler({ env: ENV, now: () => NOW });
  assert.equal(validSession("", ENV.LINUXCORE_SESSION_SECRET, NOW), false);
  assert.equal(safeUpstream("http://linuxcore.example.net"), null);
  assert.equal(safeUpstream("https://127.0.0.1:8000"), null);
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

test("API proxy requires session and forwards only allowlisted paths with server token", async () => {
  let captured;
  const handler = createGatewayHandler({
    env: ENV,
    now: () => NOW,
    fetchImpl: async (url, init) => {
      captured = { url: String(url), init };
      return new Response(JSON.stringify({ status: "ok" }), {
        status: 200, headers: { "content-type": "application/json" }
      });
    }
  });
  const unauthenticated = await invoke(handler, request("/api/v1/health"));
  assert.equal(unauthenticated.status, 401);

  const login = await invoke(handler, request("/api/auth/login", "POST", {
    body: { password: ENV.LINUXCORE_LOGIN_PASSWORD }
  }));
  const cookie = login.headers["set-cookie"].split(";")[0];
  const authorizedRequest = request("/api/v1/health", "GET", { headers: { cookie } });
  const authorized = await invoke(handler, authorizedRequest);
  assert.equal(authorized.status, 200);
  assert.equal(captured.url, "https://linuxcore.example.net/api/v1/health");
  assert.equal(captured.init.headers.Authorization, "Bearer " + ENV.LINUXCORE_ACCESS_TOKEN);
  assert.equal(captured.init.redirect, "manual");
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

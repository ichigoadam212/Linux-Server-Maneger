# LinuxCore Operations and Security Runbook

## Scope

LinuxCore is a local-first manager for the current unprivileged Linux user-space. It is designed for Debian/Ubuntu environments, including ARM64 PRoot deployments. It is not a host root manager and does not administer Android itself.

## Normal lifecycle

From the repository root:

```bash
bash scripts/doctor.sh
bash scripts/start.sh
bash scripts/status.sh
bash scripts/smoke-test.sh
```

Open `http://127.0.0.1:8080` on the same device. The API is at `http://127.0.0.1:8000`.

To stop LinuxCore:

```bash
bash scripts/stop.sh
```

## Remote API access boundary

LinuxCore remains loopback-only by default. The local start script binds the API to `127.0.0.1`; local dashboard requests continue to work without a remote token.

If the API is deliberately placed behind a trusted HTTPS reverse proxy or a server-side gateway, configure `LINUXCORE_ACCESS_TOKEN` in the backend environment with a random value of at least 32 characters. Every `/api/*` request must then include a bearer token, including requests arriving through a localhost reverse proxy (which prevents a proxy from becoming an authentication bypass):

```http
Authorization: Bearer <LINUXCORE_ACCESS_TOKEN>
```

When the token is missing or shorter than 32 characters, remote API requests are rejected; a configured but weak token also fails closed. Once a token is configured, loopback requests must present it too. A configured token is compared in constant time. The API does not trust `X-Forwarded-For` to decide whether a request is local. Keep the token only in the Linux backend environment and the gateway's encrypted server-side environment; never put it in frontend JavaScript, Git, a URL, or a client-visible response.

Generate a token on the server without sharing it:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

This is an API-to-gateway trust boundary, not a complete public login system. A public dashboard still needs an authenticated user-facing access layer at the gateway (for example, an approved Vercel deployment protection or a dedicated login/session layer) before any public deployment. Do not expose the VPS API directly to the internet.

## Vercel authenticated gateway

The repository now includes a Vercel Node function at `api/[...path].js` and a static dashboard output configuration in `vercel.json`. The gateway is intentionally fail-closed until all four server-side Vercel environment variables are configured:

- `LINUXCORE_LOGIN_PASSWORD`: a unique password of at least 12 characters for dashboard access.
- `LINUXCORE_SESSION_SECRET`: at least 32 random characters used to sign sessions.
- `LINUXCORE_UPSTREAM_URL`: the HTTPS origin/base path of the LinuxCore VPS API; private/local IPs and non-HTTPS URLs are rejected.
- `LINUXCORE_ACCESS_TOKEN`: the same strong bearer token configured in the VPS backend environment.

The password and secrets belong only in Vercel's encrypted server-side environment and the backend token belongs in the VPS backend environment. Never add them to Git, browser code, URLs, or chat. The gateway uses an eight-hour `HttpOnly; Secure; SameSite=Strict; Path=/` cookie, checks same-origin POSTs, restricts methods and API paths, caps request/response bodies, disables caching, and forwards the bearer token only from the server function. Login throttling in the function is best-effort only because serverless instances are ephemeral; configure Vercel Firewall rate limiting and keep deployment protection enabled before exposing any Preview or Production deployment. The function has a 60-second maximum duration to fit the current Hobby project limits; the upstream request aborts after 55 seconds.

This gateway is not yet live. No Vercel project has been created or deployed, and no VPS origin or credentials have been configured. The linked Vercel team is on Hobby: Standard Vercel Authentication protects Preview/deployment URLs but does not protect a Production custom domain. Do not treat that feature as production login; the gateway's own login must be configured and verified before a production domain is attached. The Vercel project must be protected before the first deployment; never deploy the control dashboard publicly without verifying the protection settings.

## Persistent user-level operation

On a Linux host with a reachable systemd user manager, install the optional service:

```bash
bash scripts/install-user-service.sh
systemctl --user status linuxcore.service
```

The unit runs as the current unprivileged user. It starts the existing loopback-only API and dashboard, then the foreground supervisor periodically verifies both. Repeated failures cause the supervisor to exit so systemd can apply its bounded restart policy. The installer does not enable lingering, grant root privileges, alter firewall rules, or expose ports publicly. For boot-time startup and operation after logout, the VPS administrator must separately enable systemd user lingering for this account after reviewing the host's policy.

To disable it:

```bash
systemctl --user disable --now linuxcore.service
```

If systemd user sessions are unavailable (common in PRoot/Andronix), use the foreground fallback:

```bash
bash scripts/linuxcore-supervisor.sh run
```

Keep the Linux session alive. The supervisor uses a 10-second default check interval and exits after five consecutive failed checks; both values have bounded environment-variable overrides. This fallback is not a daemon and cannot survive Android suspending or killing its parent Linux environment. Do not start more than one supervisor for the same repository.

## Validation

The Security page reads `GET /api/v1/diagnostics` to show live capability checks for the current user-space: process privilege level, architecture, Python version, systemd user-manager availability, rootless container runtime, network counters, and the fixed diagnostic tools. Optional host capabilities may be unavailable in PRoot; this is reported as unavailable rather than treated as a project failure.

The Security-page diagnostics request allows 30 seconds because capability discovery is sequential and may include bounded systemd, Podman, and Docker probes. A slow optional runtime should not cause the browser to abandon the diagnostics response before those checks finish.

The overview loads the live `systemd --user` inventory and diagnostics capabilities. It does not display fabricated service events or sample network graph data. No event-history API is implemented yet.

Run the local static security checks:

```bash
bash scripts/security-check.sh
```

Run backend tests:

```bash
backend/.venv/bin/python -m pytest backend/test_main.py -v
```

The security script checks loopback binding declarations, the unprivileged service-installer boundary, obvious unsafe subprocess/CORS patterns, tracked populated environment files, local environment-file permissions, shell syntax, Python compilation, and frontend JavaScript syntax when Node.js is installed. These are guardrails, not a full penetration test or proof that the host is secure.

## Recovery behavior and limits

`bash scripts/recover.sh` backs up only `backend/.env` (when present), checks required project files, and invokes LinuxCore's own start/status scripts. If the script exits unsuccessfully, it restores or removes the environment file to match its prior state.

Recovery does **not** restore source code, databases, container volumes, package installations, Android settings, system services, or unrelated files. The environment-file backup is not a complete system backup. Store separate backups of any application data you care about.

Backups are stored in `.runtime/backups` and should be treated as sensitive because they may contain the DeepSeek API key. Keep the directory private and do not upload it to GitHub.

## Security boundaries

- Keep both services bound to `127.0.0.1`; do not change to `0.0.0.0` for convenience.
- The dashboard Content Security Policy blocks remote scripts, objects, frames, and non-loopback API connections. Inline styles remain allowed for live metric bars.
- CORS is a browser policy, not authentication. Other local processes may still be able to call a loopback API.
- API routes return `Cache-Control: no-store` and `Pragma: no-cache` so browsers and compliant intermediaries should not retain host metrics, inventories, or AI responses.
- Do not expose this development service to Wi-Fi, the public internet, a reverse proxy, or a tunnel unless the authenticated Vercel gateway, TLS upstream, WAF rate limiting, and project protection have been configured and reviewed.
- Never add raw shell input, arbitrary file paths, root escalation, or system-wide service control to the API.
- Service controls are limited to discovered `systemd --user` units.
- Container controls are limited to discovered rootless Podman/rootless Docker containers.
- Keep `backend/.env` out of Git and restrict it to owner-only permissions.
- AI requests leave the device when DeepSeek is configured. Only opt in to sending aggregate host context when needed; never send secrets.

## PRoot / Android limitations

PRoot may not provide systemd user sessions, rootless container runtimes, full network counters, stable background execution, or accurate host-wide metrics. LinuxCore reports unsupported capabilities as unavailable. It cannot guarantee operation after Android suspends or kills the Linux app.

## Incident response

1. Stop LinuxCore with `bash scripts/stop.sh`.
2. Keep `.runtime/api.log`, `.runtime/web.log`, and any relevant terminal output for diagnosis; inspect them locally before sharing and redact secrets.
3. Run `bash scripts/doctor.sh` and `bash scripts/security-check.sh`.
4. Restart with `bash scripts/start.sh`, then run `bash scripts/smoke-test.sh`.
5. If the issue persists, do not repeatedly invoke recovery; capture the exact error and investigate its cause first.

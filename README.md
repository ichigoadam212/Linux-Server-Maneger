# LinuxCore Server Manager

Cyber-style, bilingual (Arabic / English) local website for monitoring and managing a Linux user-space environment. This repository is not an Android application and does not produce an APK.

**Version:** 0.7.0  
**Status:** Dashboard, read-only monitoring, scoped user-service/container controls, fixed diagnostic commands, controlled recovery, and a Python loopback-only Static Site are implemented. GitHub CI exercises Debian 13 (Trixie) under PRoot; the Redmi/Android phone still requires manual testing.

## Architecture

- **Linux host:** Debian/Ubuntu ARM64 user-space Linux environment.
- **Backend:** Python + FastAPI. Monitoring is read-only; operational actions are explicitly allowlisted.
- **Frontend:** Static HTML/CSS/JavaScript website opened in a browser.
- **Optional AI:** DeepSeek chat proxy. The API key stays in the backend environment.
- **JARVIS:** Separate project and runtime. Sharing a Linux user-space environment does not merge source code or grant Android privileges.
- **Android bridge:** Not implemented in this repository. It must be a separately permissioned Android component.

The dashboard and API bind to 127.0.0.1 by default. Do not expose this development build to a public network.

## Implemented

- Responsive cyber dashboard with Arabic/English UI and RTL support.
- Overview panels load current user-service inventory and real environment capability checks; fabricated activity entries and static network sparkline samples are not presented as live data.
- Live CPU, memory, disk, host identity, uptime, storage, process and network views.
- Live environment diagnostics for architecture, Python runtime, privilege level, user-service manager, rootless container runtime, network counters and allowlisted diagnostic tools.
- Graceful handling when the Linux environment restricts /proc network counters.
- **Services:** LinuxCore's own API and dashboard processes are discovered through checkout-owned PID files and verified process identities; the page offers lifecycle controls that call only this checkout's start/stop scripts. Separately, start/stop/restart controls remain limited to units discovered by an available unprivileged systemd --user manager. No system-wide or Android service control.
- **Containers:** Discover and start/stop/restart only containers visible through rootless Podman or rootless Docker. Rootful Docker is intentionally not used.
- **Static site deployment:** Run one editable HTML page using a fixed Python standard-library HTTP server, with no container runtime requirement. It binds only to `127.0.0.1`, serves only `/` and `/index.html` plus a health endpoint, applies a restrictive CSP, caps page and log size, and supports start/stop/restart, editing, logs and one-step rollback. Page and process state live in owner-only files under `.runtime/deployments`; a write-ahead journal recovers interrupted edit/rollback transactions. The site is a separate process: stop it from the dashboard before stopping LinuxCore. It does not auto-start after a reboot or a killed PRoot session; start it again from the dashboard.
- **Terminal:** Fixed read-only diagnostic presets (pwd, system information, storage, memory, uptime and process summary). No free-form shell input or arbitrary command endpoint.
- **Recovery:** Backs up backend/.env with restrictive permissions, checks required project files, then runs the project's own start/status scripts. If recovery fails, it restores the prior backend/.env (or removes a newly created one). It does not modify Android settings, system services, firewall rules or unrelated files.
- Optional DeepSeek chat with explicit opt-in for aggregate host context.
- Server-side API key handling; the browser never receives the key.
- API responses use `Cache-Control: no-store` and `Pragma: no-cache` to discourage browser and intermediary caching of host data and AI responses.
- AI remains advisory-only and cannot execute commands or modify the host.
- Debian/Ubuntu setup, start, stop, status, diagnostic, recovery and static security-check scripts.
- Optional foreground supervisor with bounded health retries and graceful child cleanup, plus an opt-in systemd user service installer that refuses root/overwrite and rolls back failed installation attempts.
- Local dashboard API calls pass through a loopback-only same-origin proxy that reads the optional backend token server-side; the browser never receives the bearer token.
- Remote API requests are denied by default and require a server-side bearer token when routed through a trusted HTTPS gateway; the token is never exposed to the browser.
- The Vercel adapter provides a password login, signed HttpOnly/Secure/SameSite=Strict session cookie, same-origin write checks, allowlisted API routes, bounded JSON payloads, HTTPS-only upstream validation, DNS checks against private/reserved IP ranges and server-side bearer-token forwarding.
- The gateway pins outbound HTTPS connections to prevalidated public DNS addresses, streams upstream responses with a 2 MiB ceiling, and bounds its per-instance login-throttle map.
- Automated backend tests, startup identity checks, controlled recovery rollback tests, safe shutdown and supervisor tests, frontend contract checks and shell syntax validation in GitHub Actions.

## Repository layout

    frontend/                 Website files
    api/                      Vercel login/session gateway and allowlisted API proxy
    backend/                  FastAPI service and tests
    scripts/                  Linux setup and lifecycle scripts
    docs/                     Deployment and shared-host notes
    .github/workflows/        CI workflow

## Run in Debian / Andronix / another Debian-based user-space distro

From the repository directory:

    bash scripts/doctor.sh
    bash scripts/start.sh

Open the dashboard on the same device:

    http://127.0.0.1:8080

Backend health (direct API requests require the configured bearer token once remote protection is enabled):

    http://127.0.0.1:8000/api/v1/health

For local checks that read the token safely from backend/.env, use bash scripts/status.sh or bash scripts/smoke-test.sh. The browser dashboard uses the same-origin loopback proxy and never receives the token.

Check both services:

    bash scripts/status.sh

Run a non-destructive end-to-end check after both services are online:

    bash scripts/smoke-test.sh

The smoke test checks API health, metrics, module endpoints, recovery preflight, and dashboard assets. It does not restart services or change settings.

Run static local security checks:

    bash scripts/security-check.sh

See `docs/OPERATIONS_SECURITY.md` for lifecycle, recovery limits, security boundaries and incident-response steps.

Run controlled recovery:

    bash scripts/recover.sh

Stop both LinuxCore services:

    bash scripts/stop.sh


### Deploy and roll back the local Static Site

Start LinuxCore, then open `http://127.0.0.1:8080` and select **Static Site** in the sidebar. This feature is a separate Python standard-library server and does not use the Containers page or require Podman/Docker. The default port is `18081`; both the API and site bind only to `127.0.0.1`.

Use **Deploy site**, edit the single HTML page, and select **Save page**. **Roll back page** restores the previous saved page and refreshes the editor. **Start**, **Stop**, and **Restart** control only the Python child whose PID, process start time, and exact command line match LinuxCore metadata. The site process is separate from the dashboard/API and can outlive them; stop the site in the dashboard before `bash scripts/stop.sh`. It does not auto-start after reboot or after the PRoot session is killed. Runtime files live under the private, ignored `.runtime/deployments` directory in this checkout.

### Copy-paste target-device check

Run inside the existing Debian/PRoot shell on the phone (open it through your existing Termux Linux launcher). Replace the checkout path. If the working tree has edits, preserve/review them before switching branches.

```sh
cd /path/to/Linux-Server-Maneger
git status --short --branch
git fetch origin main feature/rootless-app-deployments
git switch feature/rootless-app-deployments 2>/dev/null || git switch --track -c feature/rootless-app-deployments origin/feature/rootless-app-deployments
git pull --ff-only origin feature/rootless-app-deployments
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
uname -a
python3 --version
bash scripts/doctor.sh
```

If LinuxCore is already running an older checkout, stop any deployed site from the **Static Site** page first. Then restart the dashboard and API so the running Python process loads the updated code:

```sh
bash scripts/stop.sh
bash scripts/start.sh
bash scripts/smoke-test.sh
```

Open the dashboard and deploy on `18081`. Before that, test a port conflict: in a second Debian terminal run this temporary loopback-only listener, then attempt to deploy on `18082` from the Static Site page. Expect a conflict error and no site to be deployed on that port. Stop the listener with Ctrl-C, then continue with deployment on `18081`.

```sh
python3 -c 'import socket,time; s=socket.socket(); s.bind(("127.0.0.1",18082)); s.listen(); print("reserved 127.0.0.1:18082"); time.sleep(120)'
```

Check the API and deployed page, edit it through the local proxy, then roll it back:

```sh
SITE_PORT=18081
curl --fail --show-error http://127.0.0.1:8080/api/v1/health
curl --fail --show-error "http://127.0.0.1:$SITE_PORT/healthz"
curl --fail --show-error "http://127.0.0.1:$SITE_PORT/"
curl -sS -o /dev/null -w 'POST status: %{http_code}\\n' -X POST "http://127.0.0.1:$SITE_PORT/"
curl --path-as-is -sS -o /dev/null -w 'Traversal status: %{http_code}\\n' "http://127.0.0.1:$SITE_PORT/../../etc/passwd"
curl --fail --show-error -X PUT -H 'Content-Type: application/json' \
  --data '{"content":"<!doctype html><html><body><h1>Phone test</h1></body></html>"}' \
  http://127.0.0.1:8080/api/v1/apps/static-site/content
curl --fail --show-error "http://127.0.0.1:$SITE_PORT/"
curl --fail --show-error -X POST -H 'Content-Type: application/json' \
  --data '{"confirm":true}' http://127.0.0.1:8080/api/v1/apps/static-site/rollback
curl --fail --show-error "http://127.0.0.1:$SITE_PORT/"
```

The edited page should contain `Phone test`; after rollback the original page should return. Verify Stop, Start, and Restart through the dashboard (or the allowlisted local API action):

```sh
curl --fail --show-error -X POST -H 'Content-Type: application/json' --data '{"action":"stop"}' \
  http://127.0.0.1:8080/api/v1/apps/static-site/action
if curl --fail --silent --max-time 2 "http://127.0.0.1:$SITE_PORT/healthz"; then
  echo "FAIL: site still responds after Stop"; exit 1
else
  echo "OK: site is stopped"
fi
curl --fail --show-error -X POST -H 'Content-Type: application/json' --data '{"action":"start"}' \
  http://127.0.0.1:8080/api/v1/apps/static-site/action
curl --fail --show-error -X POST -H 'Content-Type: application/json' --data '{"action":"restart"}' \
  http://127.0.0.1:8080/api/v1/apps/static-site/action
curl --fail --show-error "http://127.0.0.1:$SITE_PORT/healthz"
curl --fail --show-error http://127.0.0.1:8080/api/v1/apps/static-site/logs
```

If `ss` fails in PRoot, use Python to test loopback connections and inspect the kernel TCP tables for the actual local bind addresses. For these listeners every displayed address must be `127.0.0.1` (or `::1` if a service intentionally supports IPv6; LinuxCore expects IPv4 loopback here). A wildcard such as `0.0.0.0` or `::` is a failure.

```sh
python3 - <<'PY'
import socket
ports = {8000, 8080, 18081}
for port in sorted(ports):
    sock = socket.socket()
    sock.settimeout(1)
    result = sock.connect_ex(("127.0.0.1", port))
    sock.close()
    print(f"127.0.0.1:{port}: " + ("reachable" if result == 0 else "not listening"))

tables = (("/proc/net/tcp", socket.AF_INET), ("/proc/net/tcp6", socket.AF_INET6))
for table, family in tables:
    try:
        rows = open(table, encoding="ascii").read().splitlines()[1:]
    except OSError as error:
        print(f"{table}: unavailable ({error})")
        continue
    for row in rows:
        fields = row.split()
        if len(fields) < 4 or fields[3] != "0A":
            continue
        address_hex, port_hex = fields[1].split(":")
        port = int(port_hex, 16)
        if port not in ports:
            continue
        raw = bytes.fromhex(address_hex)
        if family == socket.AF_INET:
            address = socket.inet_ntop(family, raw[::-1])
        else:
            address = socket.inet_ntop(family, b"".join(raw[i:i+4][::-1] for i in range(0, 16, 4)))
        print(f"listener: {address}:{port}")
PY
```

Expected: API health, site health, and the page return HTTP 200; the health body is `linuxcore-site-ok`; POST returns 405; traversal returns 404; the edited page contains `Phone test` before rollback and the original page returns afterward; Stop returns stopped and makes the health request fail; Start/Restart restore HTTP 200. The socket check shows the three expected ports reachable on loopback, and the TCP table shows only `127.0.0.1:8000`, `127.0.0.1:8080`, and `127.0.0.1:18081`. Logs show method/status but no request path or query. Report the branch/commit, Debian/Python/PRoot versions, HTTP status/output, and relevant error text; redact tokens and private data.

CI runs backend, proxy, frontend contract, shell/security and smoke checks on GitHub-hosted Linux; its integration job uses Debian 13 under PRoot. These do not execute on the Android phone. The phone check above remains pending until you run it on-device.
### Keep LinuxCore running in a Linux user session

On a VPS or Linux distribution with a working systemd user manager, install the optional user service:

    bash scripts/install-user-service.sh

Check it with:

    systemctl --user status linuxcore.service

The service runs as the current user, starts the local API and a loopback-only same-origin dashboard/API proxy, checks them periodically, and lets systemd restart the supervisor after repeated failures. It does not grant root access or change the loopback-only network binding. For it to start at boot and remain active after logout, a VPS administrator must separately enable systemd user lingering for this account; the installer deliberately does not change that host policy.

In PRoot/Andronix environments without a systemd user manager, run the supervisor in the foreground:

    bash scripts/linuxcore-supervisor.sh run

Keep that terminal/session alive. The supervisor retries failed start/health checks at a bounded interval and exits after repeated failures; it cannot keep running if Android kills or suspends the Linux environment. Do not run multiple supervisors for the same repository.

To disable the systemd user service:

    systemctl --user disable --now linuxcore.service

The start script creates a virtual environment without requiring Android root. If Python's venv module or pip is missing, install the corresponding packages inside the Linux distribution using the package manager and its available permissions. Some Andronix/PRoot environments restrict package installation, systemd user sessions, container runtimes, or host metrics. Unsupported capabilities are reported as unavailable instead of being simulated.

The scripts can be invoked with bash; executable file permissions are not required.

## Operational API

- GET /api/v1/health
- GET /api/v1/metrics
- GET /api/v1/diagnostics
- GET /api/v1/storage
- GET /api/v1/processes
- GET /api/v1/network
- GET /api/v1/services
- POST /api/v1/services/{unit}/action
- GET /api/v1/managed-services
- POST /api/v1/managed-services/action
- GET /api/v1/containers
- GET /api/v1/apps/static-site and /content
- POST /api/v1/apps/static-site/deploy, /action, /rollback
- PUT /api/v1/apps/static-site/content
- GET /api/v1/apps/static-site/logs
- POST /api/v1/containers/{container_id}/action
- GET /api/v1/terminal/commands
- POST /api/v1/terminal/run
- GET /api/v1/recovery/check
- POST /api/v1/recovery/run
- GET /api/v1/ai/status
- POST /api/v1/ai/chat

Local interactive API docs: http://127.0.0.1:8000/docs.

## Optional DeepSeek setup

The dashboard and monitoring API work without a DeepSeek key. To enable chat:

1. Create backend/.env from backend/.env.example.
2. Add DEEPSEEK_API_KEY to backend/.env.
3. Keep that file private. It is ignored by Git.

Supported model IDs: deepseek-flash and deepseek-v4-pro.

If the optional host context checkbox is enabled, only aggregate CPU, memory, disk, uptime, hostname, platform and a limited storage summary are shared. Process command lines, environment variables, usernames and secrets are excluded.

## Security boundaries

- Localhost-only binding by default.
- A restrictive dashboard Content Security Policy blocks remote scripts and non-loopback API connections.
- No arbitrary shell execution and no user-supplied command strings.
- Service actions are restricted to discovered systemd --user units.
- Container actions require an accessible rootless runtime and a container present in its current inventory.
- Static-site content is a single UTF-8 HTML page capped at 64 KiB. The fixed server binds only to 127.0.0.1, rejects other paths and unsupported methods, and verifies its recorded process identity before stop signals.
- No sudo, root escalation, system-wide service control, firewall changes, package-manager endpoint, or Android system access.
- AI is advisory-only and must not be treated as an execution agent.
- Recovery operates only on this repository's own local startup scripts and backs up the backend environment file before running them.
- Never commit API keys, passwords, private keys or populated environment files.
- The default API remains loopback-only. Remote API requests fail closed unless a strong server-side bearer token is configured; a public dashboard still needs a user login/session gateway, TLS, rate limiting, audit logging and secure secret storage.

## Environment-specific limitations

- systemd --user may be absent in Andronix/PRoot; its separate service section reports the specific missing manager/session-bus reason. LinuxCore's own API/dashboard processes remain visible through PID-verified inventory and can be started/stopped/restarted using only this checkout's lifecycle scripts.
- Rootless Podman or rootless Docker may not be installed; container controls then report unavailable. Static-site hosting uses Python and works without those runtimes, including in Debian/PRoot.
- Static-site hosting serves one page only. It does not upload assets, provide TLS, or start automatically after reboot; Android may stop it when the Linux session is killed.
- The Terminal page is a diagnostic console, not an unrestricted interactive shell.
- Network counters may be unavailable when Android/PRoot restricts /proc/net/dev.
- DeepSeek chat requires the user's own API key.
- Public Vercel access requires the gateway's four server-side variables, a protected Vercel project, platform-level login rate limiting/WAF, HTTPS VPS origin, and server-side secret configuration. The API bearer token alone is not a public login system.
- The gateway's in-memory sign-in throttle is only a best-effort per-instance guard; configure Vercel Firewall rate limiting before any external access. On the current Hobby team, Vercel Authentication protects Preview/deployment URLs but not a Production custom domain; the gateway login must be configured and verified before production.
- The systemd user service requires an active systemd user manager; it is not available in many PRoot sessions.
- The foreground supervisor needs its parent Linux session to remain alive; Android background persistence, exact resource readings and startup behavior require testing on the target phone.
- JARVIS shared-runtime integration and the Android bridge are separate work and are not implemented here.
- Recovery can restart LinuxCore-owned processes, but it cannot guarantee repair of Android, the Linux distribution itself, or unrelated services.

## Validation status

### Automated code acceptance

- [x] Backend API and input-validation tests pass in GitHub Actions.
- [x] Frontend JavaScript syntax and live-data contract checks pass.
- [x] Shell syntax, startup identity, recovery rollback, safe shutdown, supervisor and systemd user-service installer tests pass.
- [x] Remote API tests verify default-deny, bearer-token validation, weak-token rejection, forwarded-IP spoofing resistance and loopback-proxy token enforcement.
- [x] End-to-end smoke tests pass in both open and token-protected modes through the same-origin local proxy.
- [x] Local proxy tests cover server-side token forwarding, fixed loopback origin, allowlisted paths, body limits, dotenv parsing and redirects.
- [x] Startup/status/recovery/smoke probes support backend bearer tokens without exposing them to browser code.
- [x] Static security checks cover loopback binding, CORS, CSP, tracked secrets and runtime-file exclusions.
- [x] Authenticated gateway implementation and isolated Node tests are present. External gateway deployment is not part of local phone acceptance.
- [x] GitHub Actions CI validates the gateway transport and authentication, local proxy, static security checks, loopback smoke tests in both API modes, the backend API suite, and a real static-site HTTP deployment in PRoot.

### Final local target-device acceptance — pending phone execution

CI validates backend/frontend/shell/security behavior and runs the deployment API against a live Python server inside Debian 13 (Trixie) under PRoot. It does not exercise Android networking, browser behavior, backgrounding, or Termux/PRoot process lifetime. No phone-side test has been run in this environment; the copy-paste checklist above is the required device check.

- [ ] Pull this branch on the target phone, start LinuxCore and run `bash scripts/smoke-test.sh`.
- [ ] Confirm the dashboard and Arabic/English layout in the phone browser.
- [ ] Record which user-service manager and rootless container runtime are actually available on the phone.
- [ ] Deploy the static page from the dashboard and confirm the loopback URL in the phone browser.
- [ ] Test edit/rollback, port-conflict recovery, and stop/start behavior on the phone.
- [ ] Confirm lifecycle behavior when Android backgrounds or kills the Linux environment.

### Deferred: optional VPS and public hosting

These are not prerequisites for local phone testing and remain intentionally deferred. No VPS is connected to Termalin or SentinelX, and no Vercel settings or deployment changes are part of this stage.

- [ ] Validate systemd user-service lifecycle and lingering on a compatible VPS.
- [ ] Configure a real HTTPS VPS origin and matching server-side bearer token before enabling remote gateway access.
- [ ] Configure Vercel server-side secrets and platform-level login rate limiting only after the owner explicitly resumes the Vercel work and approves any usage-based charges.
- [ ] Run end-to-end gateway-to-VPS tests after a real host is connected.

## License

No license has been selected yet.

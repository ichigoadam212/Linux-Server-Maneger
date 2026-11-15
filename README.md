# LinuxCore Server Manager

Cyber-style, bilingual (Arabic / English) local website for monitoring and managing a Linux user-space environment. This repository is not an Android application and does not produce an APK.

**Version:** 0.7.0  
**Status:** Dashboard, read-only monitoring, scoped user-service/container controls, fixed diagnostic commands, and controlled recovery are implemented. Target-device checks remain environment-specific.

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
- **Services:** Discover and start/stop/restart only services listed by the current unprivileged systemd --user manager. No system-wide or root service control.
- **Containers:** Discover and start/stop/restart only containers visible through rootless Podman or rootless Docker. Rootful Docker is intentionally not used.
- **Terminal:** Fixed read-only diagnostic presets (pwd, system information, storage, memory, uptime and process summary). No free-form shell input or arbitrary command endpoint.
- **Recovery:** Backs up backend/.env with restrictive permissions, checks required project files, then runs the project's own start/status scripts. If recovery fails, it restores the prior backend/.env (or removes a newly created one). It does not modify Android settings, system services, firewall rules or unrelated files.
- Optional DeepSeek chat with explicit opt-in for aggregate host context.
- Server-side API key handling; the browser never receives the key.
- API responses use `Cache-Control: no-store` and `Pragma: no-cache` to discourage browser and intermediary caching of host data and AI responses.
- AI remains advisory-only and cannot execute commands or modify the host.
- Debian/Ubuntu setup, start, stop, status, diagnostic, recovery and static security-check scripts.
- Optional foreground supervisor with bounded health retries, plus an opt-in systemd user service installer for persistent Linux user sessions.
- Remote API requests are denied by default and require a server-side bearer token when routed through a trusted HTTPS gateway; the token is never exposed to the browser.
- The Vercel adapter provides a password login, signed HttpOnly/Secure/SameSite=Strict session cookie, same-origin write checks, allowlisted API routes, bounded JSON payloads, HTTPS-only upstream validation and server-side bearer-token forwarding.
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

Backend health:

    http://127.0.0.1:8000/api/v1/health

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

### Keep LinuxCore running in a Linux user session

On a VPS or Linux distribution with a working systemd user manager, install the optional user service:

    bash scripts/install-user-service.sh

Check it with:

    systemctl --user status linuxcore.service

The service runs as the current user, starts the local API/dashboard, checks them periodically, and lets systemd restart the supervisor after repeated failures. It does not grant root access or change the loopback-only network binding. For it to start at boot and remain active after logout, a VPS administrator must separately enable systemd user lingering for this account; the installer deliberately does not change that host policy.

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
- GET /api/v1/containers
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
- No sudo, root escalation, system-wide service control, firewall changes, package-manager endpoint, or Android system access.
- AI is advisory-only and must not be treated as an execution agent.
- Recovery operates only on this repository's own local startup scripts and backs up the backend environment file before running them.
- Never commit API keys, passwords, private keys or populated environment files.
- The default API remains loopback-only. Remote API requests fail closed unless a strong server-side bearer token is configured; a public dashboard still needs a user login/session gateway, TLS, rate limiting, audit logging and secure secret storage.

## Environment-specific limitations

- systemd --user may be absent in Andronix/PRoot; service controls then report unavailable.
- Rootless Podman or rootless Docker may not be installed; container controls then report unavailable.
- The Terminal page is a diagnostic console, not an unrestricted interactive shell.
- Network counters may be unavailable when Android/PRoot restricts /proc/net/dev.
- DeepSeek chat requires the user's own API key.
- Public Vercel access requires the gateway's four server-side variables, a protected Vercel project, platform-level login rate limiting/WAF, HTTPS VPS origin, and server-side secret configuration. The API bearer token alone is not a public login system.
- The gateway's in-memory sign-in throttle is only a best-effort per-instance guard; configure Vercel Firewall rate limiting before any external access.
- The systemd user service requires an active systemd user manager; it is not available in many PRoot sessions.
- The foreground supervisor needs its parent Linux session to remain alive; Android background persistence, exact resource readings and startup behavior require testing on the target phone.
- JARVIS shared-runtime integration and the Android bridge are separate work and are not implemented here.
- Recovery can restart LinuxCore-owned processes, but it cannot guarantee repair of Android, the Linux distribution itself, or unrelated services.

## Validation checklist

- [x] Backend API and input-validation tests pass in CI.
- [x] Frontend JavaScript syntax and live-data contract checks pass in CI.
- [x] Latest CI run passes shell syntax, startup identity, recovery rollback, safe shutdown, supervisor retry/cleanup and systemd user-service installer tests.
- [x] Remote API tests verify default-deny, bearer-token validation, weak-token rejection, forwarded-IP spoofing resistance and loopback-proxy token enforcement.
- [x] CI starts an isolated loopback API/dashboard pair and passes the full non-destructive smoke test.
- [x] Static security checks pass, including loopback binding, CORS, CSP, tracked-secret and runtime-ignore checks.
- [ ] Validate actual systemd user-service lifecycle on a compatible VPS/Linux host; CI uses an isolated systemctl fixture and cannot validate host policy or lingering.
- [x] Implement the Vercel password/session gateway, allowlisted API proxy, HTTPS upstream validation, same-origin write protection and isolated Node tests.
- [ ] Create/link a Vercel project only after its deployment protection and firewall rate limiting are confirmed. No LinuxCore Vercel project or deployment has been created.
- [ ] Set Vercel server-side variables: LINUXCORE_LOGIN_PASSWORD, LINUXCORE_SESSION_SECRET, LINUXCORE_UPSTREAM_URL and LINUXCORE_ACCESS_TOKEN; configure matching backend token on the VPS.
- [ ] Validate the actual VPS TLS origin, systemd lifecycle, and end-to-end gateway-to-VPS connection.
- [ ] **Final device stage:** run `bash scripts/smoke-test.sh` on the target phone after pulling the reviewed branch.
- [ ] **Final device stage:** confirm the dashboard and Arabic/English layout in the phone browser.
- [ ] **Final device stage:** record which user services and rootless container runtime are actually available on the phone.
- [ ] **Final device stage:** verify start/stop/recovery and background/resume behavior on Android.

## License

No license has been selected yet.

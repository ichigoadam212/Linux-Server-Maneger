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
- Live CPU, memory, disk, host identity, uptime, storage, process and network views.
- Graceful handling when the Linux environment restricts /proc network counters.
- **Services:** Discover and start/stop/restart only services listed by the current unprivileged systemd --user manager. No system-wide or root service control.
- **Containers:** Discover and start/stop/restart only containers visible through rootless Podman or rootless Docker. Rootful Docker is intentionally not used.
- **Terminal:** Fixed read-only diagnostic presets (pwd, system information, storage, memory, uptime and process summary). No free-form shell input or arbitrary command endpoint.
- **Recovery:** Backs up backend/.env with restrictive permissions, checks required project files, then runs the project's own start/status scripts. If recovery fails, it restores the prior backend/.env (or removes a newly created one). It does not modify Android settings, system services, firewall rules or unrelated files.
- Optional DeepSeek chat with explicit opt-in for aggregate host context.
- Server-side API key handling; the browser never receives the key.
- AI remains advisory-only and cannot execute commands or modify the host.
- Debian/Ubuntu setup, start, stop, status, diagnostic and recovery scripts.
- Automated backend tests and frontend/shell syntax checks in GitHub Actions.

## Repository layout

    frontend/                 Website files
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

Run controlled recovery:

    bash scripts/recover.sh

Stop both LinuxCore services:

    bash scripts/stop.sh

The start script creates a virtual environment without requiring Android root. If Python's venv module or pip is missing, install the corresponding packages inside the Linux distribution using the package manager and its available permissions. Some Andronix/PRoot environments restrict package installation, systemd user sessions, container runtimes, or host metrics. Unsupported capabilities are reported as unavailable instead of being simulated.

The scripts can be invoked with bash; executable file permissions are not required.

## Operational API

- GET /api/v1/health
- GET /api/v1/metrics
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
- No arbitrary shell execution and no user-supplied command strings.
- Service actions are restricted to discovered systemd --user units.
- Container actions require an accessible rootless runtime and a container present in its current inventory.
- No sudo, root escalation, system-wide service control, firewall changes, package-manager endpoint, or Android system access.
- AI is advisory-only and must not be treated as an execution agent.
- Recovery operates only on this repository's own local startup scripts and backs up the backend environment file before running them.
- Never commit API keys, passwords, private keys or populated environment files.
- Do not expose this development service to a public network. Remote access requires a separate authenticated design, TLS, authorization, rate limiting, audit logging and secure secret storage.

## Environment-specific limitations

- systemd --user may be absent in Andronix/PRoot; service controls then report unavailable.
- Rootless Podman or rootless Docker may not be installed; container controls then report unavailable.
- The Terminal page is a diagnostic console, not an unrestricted interactive shell.
- Network counters may be unavailable when Android/PRoot restricts /proc/net/dev.
- DeepSeek chat requires the user's own API key.
- Android background persistence, exact resource readings and startup behavior require testing on the target phone.
- JARVIS shared-runtime integration and the Android bridge are separate work and are not implemented here.
- Recovery can restart LinuxCore-owned processes, but it cannot guarantee repair of Android, the Linux distribution itself, or unrelated services.

## Validation checklist

- [x] Backend API tests and input-validation tests are part of CI.
- [x] Frontend JavaScript syntax check is part of CI.
- [x] All shell scripts, including recovery, are syntax-checked in CI.
- [ ] Run `bash scripts/smoke-test.sh` on the target phone after pulling the current branch.
- [ ] Confirm the dashboard in the phone browser.
- [ ] Verify which user services and rootless container runtime are available on the phone.
- [ ] Confirm start/stop/recovery behavior after Android backgrounds the Linux app.

## License

No license has been selected yet.

# LinuxCore Server Manager

Cyber-style, bilingual (Arabic / English) **local website** for monitoring a Linux user-space environment. This repository is not an Android application and does not produce an APK.

**Version:** 0.6.0  
**Status:** Dashboard and read-only API are implemented. Target-device checks remain environment-specific.

## Architecture

- **Linux host:** Debian/Ubuntu ARM64 user-space Linux environment.
- **Backend:** Python + FastAPI. Monitoring endpoints are read-only.
- **Frontend:** Static HTML/CSS/JavaScript website opened in a browser.
- **Optional AI:** DeepSeek chat proxy. The API key stays in the backend environment.
- **JARVIS:** Separate project and runtime. Sharing a Linux user-space environment does not merge source code or grant Android privileges.
- **Android bridge:** Separate future integration, limited to Android interfaces explicitly granted by the user.

The dashboard and API bind to 127.0.0.1 by default. This development build is not intended to be exposed to a public network.

## Implemented

- Responsive cyber dashboard with Arabic/English UI and RTL support.
- Live CPU, memory, disk, host identity and uptime metrics.
- Read-only storage, process and network endpoints.
- Graceful handling when the Linux environment restricts /proc network counters.
- Optional DeepSeek chat with explicit opt-in for aggregate host context.
- Server-side API key handling; the browser never receives the key.
- AI is advisory-only. It cannot execute shell commands or modify the host.
- Debian/Ubuntu setup, start, stop, status and diagnostic scripts.
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

Stop both services:

    bash scripts/stop.sh

The start script creates a virtual environment without requiring Android root. If Python's venv module or pip is missing, install the corresponding packages inside the Linux distribution using the package manager and its available permissions. This does not grant Android root access. Some Andronix/PRoot environments restrict package installation or access to host metrics; the dashboard reports unavailable data instead of inventing values.

The scripts can be invoked with bash; executable file permissions are not required.

## Optional DeepSeek setup

The dashboard and monitoring API work without a DeepSeek key. To enable chat:

1. Create backend/.env from backend/.env.example.
2. Add DEEPSEEK_API_KEY to backend/.env.
3. Keep that file private. It is ignored by Git.

Supported model IDs: deepseek-flash and deepseek-v4-pro.

The browser calls the local backend. The backend sends requests to DeepSeek. If the optional host context checkbox is enabled, the request may include aggregate CPU, memory, disk, uptime, hostname, platform and a limited storage summary. Process command lines, environment variables, usernames and secrets are excluded.

Official documentation:
- [DeepSeek Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/)
- [DeepSeek model list](https://api-docs.deepseek.com/api/list-models/)

## API endpoints

- GET /api/v1/health
- GET /api/v1/metrics
- GET /api/v1/storage
- GET /api/v1/processes
- GET /api/v1/network
- GET /api/v1/ai/status
- POST /api/v1/ai/chat

Local interactive API docs: http://127.0.0.1:8000/docs.

## Security boundaries

- Localhost-only binding by default.
- No arbitrary shell execution, remote terminal, privileged operations, package installation, firewall changes or service mutation endpoint.
- No remote pairing is implemented.
- AI is advisory-only and must not be treated as an execution agent.
- Never commit API keys, passwords, private keys or populated environment files.
- Do not expose this development service to a public network. Remote access requires a separate authenticated design, TLS, authorization, rate limiting, audit logging and secure secret storage.

## Known limitations / deferred work

These are intentionally not represented as completed features:

- Service discovery waits until the target distro's init system is identified.
- Container discovery is not enabled; Docker/Podman are not assumed in a rootless phone environment.
- The Terminal page is intentionally disabled; no shell execution endpoint exists.
- Network counters may be unavailable when Android/PRoot restricts /proc/net/dev.
- DeepSeek chat requires the user's own API key.
- Android background persistence, exact resource readings and startup behavior require device testing.
- JARVIS shared-runtime integration and the Android bridge are separate future work.
- Autonomous repair/recovery is not implemented.

## Validation checklist

- [x] Backend API tests pass in the development environment.
- [x] Frontend JavaScript syntax check is part of CI.
- [x] Shell script syntax checks are part of CI.
- [ ] Re-run tests on the target phone after pulling the current branch.
- [ ] Confirm the dashboard in the phone browser.
- [ ] Verify CPU, memory and disk readings against the target environment.
- [ ] Confirm service stop/start behavior after Android backgrounding.

## License

No license has been selected yet.

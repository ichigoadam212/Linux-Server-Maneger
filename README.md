# LinuxCore Server Manager

Cyber-style, bilingual (Arabic / English) **website** for monitoring a Linux environment. This repository is not an Android application and does not produce an APK.

**Version:** 0.5.0  
**Status:** Prepared for a local ARM64 Linux user-space environment; device validation is still pending.

## Architecture

- **Linux host:** one Debian/Ubuntu ARM64 user-space Linux environment can host both LinuxCore and the JARVIS Linux core.
- **LinuxCore backend:** Python + FastAPI, read-only monitoring endpoints, optional DeepSeek proxy.
- **LinuxCore frontend:** static HTML/CSS/JavaScript website opened in the phone browser.
- **JARVIS:** remains a separate project/service. Sharing the same Linux environment does not merge its code or grant Android-level privileges.
- **Android bridge:** remains a separate, limited integration. Without Android root, Linux cannot directly control protected Android system functions.

The website and backend bind to `127.0.0.1` by default. Do not expose this development build to a public network.

## What is implemented

- Responsive cyber dashboard with Arabic/English interface and RTL support.\n- Live overview cards for hostname, platform and uptime when the local host is connected.
- FastAPI health, metrics, storage, process and network endpoints.
- Optional DeepSeek chat assistant through a server-side proxy.
- Explicit opt-in for sharing a limited aggregate host snapshot with DeepSeek.
- API key is read from the backend environment; it is never returned to the browser.
- AI is advisory-only: no shell execution, tool execution, service mutation or host changes.
- Debian/Ubuntu setup, start, stop, status and environment-check scripts.
- Automated backend tests in GitHub Actions.

## Repository layout

    frontend/                 Website files
    backend/                  FastAPI service and tests
    scripts/                  Linux setup and lifecycle scripts
    docs/                     Deployment and shared-host notes
      SHARED_LINUX_ARCHITECTURE.md
    .github/workflows/        CI workflow

## First setup in a Debian/Ubuntu Linux environment

From the repository root:

    chmod +x scripts/*.sh
    ./scripts/doctor.sh
    ./scripts/install-debian.sh
    ./scripts/start.sh

Open the website in the phone browser:

    http://127.0.0.1:8080

Check services:

    ./scripts/status.sh

Stop services:

    ./scripts/stop.sh

The installer uses the Linux environment's package manager. It does not request or use Android root access. On a rootless user-space distro, package-manager permissions are scoped to that Linux environment.

## DeepSeek (optional)

Monitoring works without an API key. To enable AI chat:

1. Copy `backend/.env.example` to `backend/.env`.
2. Add your own `DEEPSEEK_API_KEY` to `backend/.env`.
3. Keep `backend/.env` private; it is ignored by Git.

Supported model IDs are `deepseek-flash` and `deepseek-v4-pro`. The browser calls the local backend; it never receives the key. The optional host snapshot contains aggregate CPU, memory, disk, uptime, platform and a limited storage summary. It excludes process command lines, environment variables and secrets.

Official documentation:
- [DeepSeek Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/)
- [DeepSeek model list](https://api-docs.deepseek.com/api/list-models/)

## API endpoints

- `GET /api/v1/health`
- `GET /api/v1/metrics`
- `GET /api/v1/storage`
- `GET /api/v1/processes`
- `GET /api/v1/network`
- `GET /api/v1/ai/status`
- `POST /api/v1/ai/chat`

API documentation is available locally at `http://127.0.0.1:8000/docs`.

## Security boundaries

- Localhost-only binding is the default.
- No arbitrary shell execution, remote terminal, privileged operations, package installation, firewall changes or service start/stop endpoint is exposed.
- No remote pairing is implemented.
- Before any remote access: authenticated pairing, authorization, TLS, rate limiting, audit logging, origin validation and secure secret storage are required.
- Review AI suggestions before using them. The AI does not execute actions.
- Never commit API keys, passwords, private keys or populated environment files.

## Work that must wait for the phone's Linux environment

These items cannot be honestly completed or verified before the target distro exists:

- Confirm exact distro, architecture, process visibility and available permissions.
- Run the setup scripts and verify Python dependencies on the phone.
- Verify actual CPU/RAM/storage/network readings in that environment.
- Discover its init system and supported services.
- Check whether any container runtime exists; containers are not assumed on a rootless phone setup.
- Validate startup persistence and Android background-process behavior.
- Complete JARVIS integration against the actual shared Linux runtime.
- Perform device-specific security and performance tests.

## Roadmap

- [x] Website dashboard and Arabic/English UI\n- [x] Live host identity and uptime overview
- [x] Read-only host monitoring API
- [x] Optional DeepSeek assistant
- [x] Privacy-limited, opt-in AI host context
- [x] Debian/Ubuntu ARM64 preparation scripts
- [ ] Phone distro validation and runtime integration
- [ ] Authenticated host pairing (only if remote access is needed)
- [ ] Read-only service discovery adapted to the actual init system
- [ ] JARVIS shared-runtime integration and Android bridge validation

## License

No license has been selected yet.

# LinuxCore Server Manager

Cyber-style, bilingual (Arabic / English) dashboard and local-first Linux host monitoring API.

**Version:** 0.2.0  
**Status:** Development prototype — read-only monitoring foundation.

## Implemented

- Responsive cyber dashboard with Arabic/English interface and RTL support.
- FastAPI backend with health and host metrics endpoints.
- Read-only storage mount inventory.
- Read-only process inventory (no command lines or environment variables are exposed).
- Network interface counters and link state.
- Automated backend tests through GitHub Actions.
- No shell endpoint, privileged actions, service mutation, or remote administration.

## Project structure

    frontend/
      index.html
      styles.css
      app.js
    backend/
      main.py
      requirements.txt
      requirements-dev.txt
      test_main.py
    .github/workflows/
      ci.yml

## Run locally

Python 3.10+ is recommended.

### Backend

    cd backend
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements-dev.txt
    uvicorn main:app --host 127.0.0.1 --port 8000

### Dashboard

In a second terminal from the repository root:

    python3 -m http.server 8080 --directory frontend --bind 127.0.0.1

Open http://127.0.0.1:8080

API documentation is available locally at http://127.0.0.1:8000/docs.

## API

- GET /api/v1/health — health and mode.
- GET /api/v1/metrics — CPU, memory, root filesystem, uptime and aggregate network counters.
- GET /api/v1/storage — mounted filesystem usage.
- GET /api/v1/processes — limited process inventory; excludes command lines and environment variables.
- GET /api/v1/network — per-interface byte and packet counters plus link state.

All endpoints are read-only. The API binds to localhost during development.

## Security boundaries

- Do not expose this development API to the public internet.
- Remote host pairing is not implemented yet.
- Before remote access, implement authenticated pairing, authorization, TLS, rate limiting, audit logging, origin validation and secure secret storage.
- Never commit passwords, tokens, private keys, or environment files.
- No arbitrary shell execution, terminal proxy, service start/stop, package installation, firewall changes, or privileged operations are exposed.
- Service and container control will require a separate permission model and explicit confirmation design.

## Remaining work that depends on the target Linux environment

- Verify actual runtime behavior on the user's Linux installation.
- Confirm supported init system and service inventory.
- Confirm container runtime availability and permissions.
- Validate mount visibility and network interface behavior on the target device.
- Configure a safe host pairing flow and local startup integration.
- Perform device-specific performance and security testing.

## Roadmap

- [x] Cyber dashboard foundation
- [x] Arabic / English interface
- [x] Local read-only host metrics
- [x] Storage inventory API
- [x] Process inventory API
- [x] Network interface inventory API
- [x] Automated API tests and CI workflow
- [ ] Target-device integration and runtime validation
- [ ] Authenticated host pairing
- [ ] Read-only service and container discovery
- [ ] Audited, permission-gated administration workflows

## License

No license has been selected yet.

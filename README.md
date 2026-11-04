# LinuxCore Server Manager

Cyber-style, bilingual (Arabic / English) website dashboard and local-first Linux host monitoring API.

**Version:** 0.3.0  
**Status:** Development prototype — read-only monitoring with optional AI assistance.

## Implemented

- Responsive cyber dashboard with Arabic/English interface and RTL support.
- FastAPI backend with health and host metrics endpoints.
- Read-only storage mount, process, and network interface inventory.
- Optional DeepSeek chat assistant through a server-side API proxy.
- Optional aggregate host metrics context for AI analysis, sent only when explicitly enabled per request.
- API key is read from the backend environment and never returned to the browser.
- AI is advisory-only: no shell execution, tool execution, service mutation, or system changes.
- Automated backend tests through GitHub Actions.

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
      .env.example
    .github/workflows/
      ci.yml

## Run locally

Python 3.10+ is recommended.

### Backend

    cd backend
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements-dev.txt

Set the API key in the backend process environment (do not put it in frontend files or commit it):

    export DEEPSEEK_API_KEY="your-key"
    export DEEPSEEK_MODEL="deepseek-flash"

Then start the API:

    uvicorn main:app --host 127.0.0.1 --port 8000

The assistant remains unavailable but the monitoring API still works when no key is configured.

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
- GET /api/v1/ai/status — DeepSeek configuration status; never returns the key.
- POST /api/v1/ai/chat — bounded chat proxy; accepts user/assistant messages and optional aggregate host context.

## DeepSeek setup

The integration uses the official DeepSeek Chat Completions endpoint and the model IDs `deepseek-flash` (default) or `deepseek-v4-pro`. The key is stored only in the backend environment as `DEEPSEEK_API_KEY`.

The browser calls the local backend. It never calls DeepSeek directly and never receives the API key. Host context is opt-in for each chat request and contains aggregate CPU, memory, disk, uptime, platform, and a limited storage summary. It excludes process command lines, environment variables, usernames, and secrets.

See the [official DeepSeek API documentation](https://api-docs.deepseek.com/api/create-chat-completion/) and [quick start](https://api-docs.deepseek.com/quick_start/agent_integrations/).

## Security boundaries

- Do not expose this development API to the public internet.
- Remote host pairing is not implemented yet.
- Before remote access, implement authenticated pairing, authorization, TLS, rate limiting, audit logging, origin validation and secure secret storage.
- Never commit passwords, tokens, private keys, API keys, or environment files.
- No arbitrary shell execution, AI tool execution, terminal proxy, service start/stop, package installation, firewall changes, or privileged operations are exposed.
- AI responses are suggestions, not verified actions or a substitute for reviewing commands before running them.

## Remaining work that depends on the target Linux environment

- Verify actual runtime behavior on the target Linux installation.
- Confirm supported init system and service inventory.
- Confirm container runtime availability and permissions.
- Validate mount visibility and network interface behavior on the target device.
- Configure a safe host pairing flow and local startup integration.
- Perform device-specific performance and security testing.

## Roadmap

- [x] Cyber dashboard foundation
- [x] Arabic / English interface
- [x] Local read-only host metrics
- [x] Storage, process, and network inventory APIs
- [x] Automated API tests and CI workflow
- [x] Optional DeepSeek assistant proxy
- [x] Opt-in, privacy-limited host context for AI analysis
- [ ] Target-device integration and runtime validation
- [ ] Authenticated host pairing
- [ ] Read-only service and container discovery
- [ ] Audited, permission-gated administration workflows

## License

No license has been selected yet.

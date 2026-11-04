# LinuxCore Server Manager

Cyber-style, bilingual (Arabic / English) dashboard for local Linux server administration.

**Version:** 0.1.0  
**Status:** Prototype — dashboard preview with an optional read-only local metrics API.

## Included in this version

- Responsive cyber-themed dashboard.
- Arabic and English interface with right-to-left layout support.
- Sample CPU, memory, storage, network, service, and activity panels.
- FastAPI endpoint for reading live CPU, memory, and disk metrics from the Linux host.
- Demo fallback when the local API is unavailable.
- No remote shell execution or destructive server controls.

## Project structure

    frontend/
      index.html
      styles.css
      app.js
    backend/
      main.py
      requirements.txt
    .gitignore
    README.md

## Run locally

### 1. Start the backend API

Python 3.10+ is recommended.

    cd backend
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn main:app --host 127.0.0.1 --port 8000

### 2. Start the dashboard

Open a second terminal from the repository root:

    python3 -m http.server 8080 --directory frontend --bind 127.0.0.1

Open http://127.0.0.1:8080

The dashboard tries to read metrics from the local API at 127.0.0.1:8000. If the API is unavailable, sample data remains visible.

## Security baseline

- Keep the API bound to localhost during development.
- Do not expose this dashboard or API to the public internet yet.
- Add authentication, authorization, TLS, rate limiting, and audit logging before enabling remote access.
- Never commit passwords, tokens, private keys, or .env files.
- This version intentionally does not execute shell commands or perform privileged actions.

## Roadmap

- [x] Cyber dashboard foundation
- [x] Arabic / English interface
- [x] Local read-only host metrics
- [ ] Authenticated host pairing
- [ ] Live service inventory and carefully scoped service controls
- [ ] Storage and container management
- [ ] Audited, permission-gated administration workflows
- [ ] Security monitoring and backup management

## License

No license has been selected yet.

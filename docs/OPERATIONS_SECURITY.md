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

## Validation

Run the local static security checks:

```bash
bash scripts/security-check.sh
```

Run backend tests:

```bash
backend/.venv/bin/python -m pytest backend/test_main.py -v
```

The security script checks loopback binding declarations, obvious unsafe subprocess/CORS patterns, tracked populated environment files, local environment-file permissions, shell syntax, Python compilation, and frontend JavaScript syntax when Node.js is installed. These are guardrails, not a full penetration test or proof that the host is secure.

## Recovery behavior and limits

`bash scripts/recover.sh` backs up only `backend/.env` (when present), checks required project files, and invokes LinuxCore's own start/status scripts. If the script exits unsuccessfully, it restores or removes the environment file to match its prior state.

Recovery does **not** restore source code, databases, container volumes, package installations, Android settings, system services, or unrelated files. The environment-file backup is not a complete system backup. Store separate backups of any application data you care about.

Backups are stored in `.runtime/backups` and should be treated as sensitive because they may contain the DeepSeek API key. Keep the directory private and do not upload it to GitHub.

## Security boundaries

- Keep both services bound to `127.0.0.1`; do not change to `0.0.0.0` for convenience.
- CORS is a browser policy, not authentication. Other local processes may still be able to call a loopback API.
- Do not expose this development service to Wi-Fi, the public internet, a reverse proxy, or a tunnel.
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

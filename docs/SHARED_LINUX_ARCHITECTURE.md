# Shared Linux environment with JARVIS

## Decision

Use one Debian/Ubuntu ARM64 Linux user-space installation on the phone as the common base for both projects. Do not install a second Linux root filesystem just for LinuxCore.

This is a shared operating environment, not a merged application:
- Keep the JARVIS source tree and runtime/configuration separate.
- Keep LinuxCore in its own repository directory and Python virtual environment.
- Run each project as a separate process/service with its own logs and configuration.
- Assign non-conflicting local ports.
- LinuxCore's dashboard remains a website opened in the Android browser; it is not an APK.

## Suggested directory layout

    ~/linux-workspace/
      jarvis/                 # JARVIS project (separate repository)
      linux-server-manager/   # this repository

Each project owns its own dependencies. Do not install one project's Python packages into the other's virtual environment.

## LinuxCore local endpoints
- Website: http://127.0.0.1:8080
- Backend API: http://127.0.0.1:8000

Both bind to loopback only. Do not change them to 0.0.0.0 for convenience.

## Android and no-root boundary

A user-space Linux distribution is not a second native Android boot. Without Android root or a supported device-specific boot chain, LinuxCore/JARVIS run inside the permissions and process-lifetime limits of the chosen user-space environment.

The Android Bridge must remain a separately permissioned component. It can only use Android interfaces that the user explicitly grants; it cannot bypass Android's protected system boundaries.

## What can only be finalized on the phone

The exact distro app/runtime is not locked by this repository. After installing the Linux environment, verify:
1. It is ARM64 and Debian/Ubuntu-based (or adapt the package installer).
2. Python 3, venv, pip, curl and git work.
3. The website and API start and stop correctly.
4. psutil reports meaningful metrics inside that environment.
5. The Android browser can open the loopback website.
6. JARVIS and LinuxCore can coexist without port or memory conflicts.
7. Background execution and restart behavior are acceptable on the phone.

Do not assume Docker, systemd, unrestricted process visibility, or persistent background execution until those checks pass.
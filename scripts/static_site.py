#!/usr/bin/env python3
"""Serve one private, loopback-only static page without a container runtime."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import stat
from urllib.parse import urlsplit

MAX_PAGE_BYTES = 65536
MAX_LOG_BYTES = 262144
HEALTH_BODY = b"linuxcore-site-ok"
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; "
    "form-action 'self'; frame-ancestors 'none'"
)


def port_value(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be a number") from exc
    if not 1024 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1024 and 65535")
    return port


def read_page(index: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(index, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_PAGE_BYTES:
            raise ValueError("invalid page file")
        with os.fdopen(fd, "rb", closefd=False) as page:
            body = page.read(MAX_PAGE_BYTES + 1)
        if len(body) > MAX_PAGE_BYTES:
            raise ValueError("page exceeds its size limit")
        return body
    finally:
        os.close(fd)


def append_access_log(path: Path, line: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return
        if info.st_size >= MAX_LOG_BYTES:
            os.ftruncate(fd, 0)
        os.write(fd, line[:512])
    finally:
        os.close(fd)


def handler_for(site_dir: Path):
    index = site_dir / "index.html"
    access_log = site_dir / "static-site.log"

    class SiteHandler(BaseHTTPRequestHandler):
        server_version = "LinuxCoreSite"
        sys_version = ""
        protocol_version = "HTTP/1.0"

        def setup(self):
            self.request.settimeout(5)
            super().setup()

        def _respond(self, status: int, body: bytes, content_type: str):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", CSP)
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def do_GET(self):
            self._serve()

        def do_HEAD(self):
            self._serve()

        def _serve(self):
            request_path = urlsplit(self.path).path
            if request_path == "/healthz":
                self._respond(200, HEALTH_BODY, "text/plain; charset=utf-8")
                return
            if request_path not in {"/", "/index.html"}:
                self._respond(404, b"Not found\n", "text/plain; charset=utf-8")
                return
            try:
                body = read_page(index)
            except FileNotFoundError:
                self._respond(404, b"Site page not found\n", "text/plain; charset=utf-8")
                return
            except ValueError:
                self._respond(500, b"Site page is invalid\n", "text/plain; charset=utf-8")
                return
            except OSError:
                self._respond(503, b"Site page unavailable\n", "text/plain; charset=utf-8")
                return
            self._respond(200, body, "text/html; charset=utf-8")

        def do_POST(self):
            self._respond(405, b"Method not allowed\n", "text/plain; charset=utf-8")

        def do_PUT(self):
            self._respond(405, b"Method not allowed\n", "text/plain; charset=utf-8")

        def do_DELETE(self):
            self._respond(405, b"Method not allowed\n", "text/plain; charset=utf-8")

        def log_request(self, code="-", size="-"):
            # Request URLs and query strings can contain secrets; omit them.
            line = f"{self.client_address[0]} {self.command} {code}\n".encode("ascii", "replace")
            try:
                append_access_log(access_log, line)
            except OSError:
                pass

        def log_message(self, _format, *_args):
            return

    return SiteHandler


def serve(port: int, site_dir: Path):
    if not 1024 <= port <= 65535:
        raise SystemExit("port must be between 1024 and 65535")
    if not site_dir.is_absolute() or site_dir.is_symlink() or not site_dir.is_dir():
        raise SystemExit("site directory must be an existing, non-symlink absolute directory")
    server = HTTPServer(("127.0.0.1", port), handler_for(site_dir))
    server.timeout = 1
    server.socket.settimeout(5)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--port", required=True, type=port_value)
    run_parser.add_argument("--site-dir", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "run":
        serve(args.port, args.site_dir)


if __name__ == "__main__":
    main()

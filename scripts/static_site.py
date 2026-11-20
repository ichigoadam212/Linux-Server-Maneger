#!/usr/bin/env python3
"""Serve LinuxCore's one local static page without a container runtime."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

MAX_PAGE_BYTES = 65536
HEALTH_BODY = b"linuxcore-site-ok"
CSP = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"


def port_value(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be a number") from exc
    if not 1024 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1024 and 65535")
    return port


def handler_for(site_dir: Path):
    index = site_dir / "index.html"

    class SiteHandler(BaseHTTPRequestHandler):
        server_version = "LinuxCoreSite"
        sys_version = ""
        protocol_version = "HTTP/1.0"

        def _respond(self, status: int, body: bytes, content_type: str):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", CSP)
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
                if index.is_symlink() or not index.is_file():
                    self._respond(404, b"Site page not found\n", "text/plain; charset=utf-8")
                    return
                body = index.read_bytes()
            except OSError:
                self._respond(503, b"Site page unavailable\n", "text/plain; charset=utf-8")
                return
            if len(body) > MAX_PAGE_BYTES:
                self._respond(500, b"Site page exceeds its size limit\n", "text/plain; charset=utf-8")
                return
            self._respond(200, body, "text/html; charset=utf-8")

        def do_POST(self):
            self._respond(405, b"Method not allowed\n", "text/plain; charset=utf-8")

        def do_PUT(self):
            self._respond(405, b"Method not allowed\n", "text/plain; charset=utf-8")

        def do_DELETE(self):
            self._respond(405, b"Method not allowed\n", "text/plain; charset=utf-8")

        def log_request(self, code="-", size="-"):
            # Do not put request URLs (which can contain sensitive query values) in logs.
            print(f"{self.client_address[0]} {self.command} {code}", flush=True)

        def log_message(self, _format, *_args):
            return

    return SiteHandler


def serve(port: int, site_dir: Path):
    if not site_dir.is_absolute() or site_dir.is_symlink() or not site_dir.is_dir():
        raise SystemExit("site directory must be an existing, non-symlink absolute directory")
    server = HTTPServer(("127.0.0.1", port), handler_for(site_dir))
    server.timeout = 1
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

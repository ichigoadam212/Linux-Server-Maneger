#!/usr/bin/env python3
"""Loopback-only static dashboard server with a fixed-path local API proxy."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

try:
    from dotenv import dotenv_values
except ImportError:
    dotenv_values = None

API_ORIGIN = "http://127.0.0.1:8000"
MAX_REQUEST_BYTES = 128 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
API_RULES = [
    (re.compile(r"^/api/v1/(health|metrics|diagnostics|storage|processes|network)$"), "GET"),
    (re.compile(r"^/api/v1/services$"), "GET"),
    (re.compile(r"^/api/v1/services/[A-Za-z0-9_.@:-]+/action$"), "POST"),
    (re.compile(r"^/api/v1/managed-services$"), "GET"),
    (re.compile(r"^/api/v1/managed-services/action$"), "POST"),
    (re.compile(r"^/api/v1/containers$"), "GET"),
    (re.compile(r"^/api/v1/containers/[A-Za-z0-9_.-]+/action$"), "POST"),
    (re.compile(r"^/api/v1/terminal/commands$"), "GET"),
    (re.compile(r"^/api/v1/terminal/run$"), "POST"),
    (re.compile(r"^/api/v1/recovery/check$"), "GET"),
    (re.compile(r"^/api/v1/recovery/run$"), "POST"),
    (re.compile(r"^/api/v1/ai/status$"), "GET"),
    (re.compile(r"^/api/v1/ai/chat$"), "POST"),
]


def load_access_token(root: Path) -> str:
    token = os.environ.get("LINUXCORE_ACCESS_TOKEN", "").strip()
    if not token and dotenv_values is not None:
        token = str(dotenv_values(root / "backend" / ".env").get("LINUXCORE_ACCESS_TOKEN") or "").strip()
    if token and not re.fullmatch(r"[A-Za-z0-9_-]{32,}", token):
        raise ValueError("LINUXCORE_ACCESS_TOKEN must be a URL-safe token of at least 32 characters.")
    return token


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = build_opener(ProxyHandler({}), NoRedirect())


def forward_api_request(method: str, path: str, body: bytes, content_type: str, token: str):
    parsed = urlsplit(path)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or parsed.path != path:
        return 400, "application/json", b'{"detail":"Invalid API path."}'
    if not any(pattern.fullmatch(path) and allowed == method for pattern, allowed in API_RULES):
        return 404, "application/json", b'{"detail":"API route or method is not allowed."}'
    if len(body) > MAX_REQUEST_BYTES:
        return 413, "application/json", b'{"detail":"Request body too large."}'
    if method == "POST" and body and not re.match(r"^application/json(?:;|$)", content_type, re.I):
        return 415, "application/json", b'{"detail":"Only JSON request bodies are accepted."}'

    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if method == "POST":
        headers["Content-Type"] = "application/json"
    request = Request(API_ORIGIN + path, data=(body if method == "POST" and body else None),
                      headers=headers, method=method)
    try:
        with OPENER.open(request, timeout=55) as response:
            payload = response.read(MAX_RESPONSE_BYTES + 1)
            status = response.status
            response_type = response.headers.get("Content-Type", "application/json")
    except HTTPError as error:
        payload = error.read(MAX_RESPONSE_BYTES + 1)
        status = error.code
        response_type = error.headers.get("Content-Type", "application/json")
    except (URLError, TimeoutError, OSError):
        return 502, "application/json", b'{"detail":"LinuxCore API is unavailable."}'

    if len(payload) > MAX_RESPONSE_BYTES:
        return 502, "application/json", b'{"detail":"API response exceeded the local proxy limit."}'
    return status, response_type, payload


class LinuxCoreHandler(SimpleHTTPRequestHandler):
    server_version = "LinuxCoreLocal/1.0"

    def do_GET(self):
        if urlsplit(self.path).path.startswith("/api/"):
            self._proxy_api()
        else:
            super().do_GET()

    def do_POST(self):
        self._proxy_api()

    def _proxy_api(self):
        parsed = urlsplit(self.path)
        if parsed.query or parsed.fragment or parsed.scheme or parsed.netloc:
            self._send_json(400, {"detail": "Query strings and absolute API URLs are not allowed."})
            return
        length_header = self.headers.get("Content-Length", "0")
        try:
            length = int(length_header)
        except (TypeError, ValueError):
            self._send_json(400, {"detail": "Invalid content length."})
            return
        if length < 0 or length > MAX_REQUEST_BYTES:
            self._send_json(413, {"detail": "Request body too large."})
            return
        if self.headers.get("Transfer-Encoding"):
            self._send_json(411, {"detail": "Chunked request bodies are not accepted."})
            return
        body = self.rfile.read(length) if length else b""
        try:
            token = load_access_token(Path(__file__).resolve().parent.parent)
        except ValueError as error:
            self._send_json(503, {"detail": str(error)})
            return
        status, content_type, payload = forward_api_request(
            self.command, parsed.path, body, self.headers.get("Content-Type", ""), token
        )
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Keep request paths/statuses visible but never log headers or secrets.
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    if args.bind != "127.0.0.1":
        parser.error("The local dashboard proxy may bind only to loopback.")
    directory = Path(args.directory).resolve()
    if not directory.is_dir() or not (directory / "index.html").is_file():
        parser.error("The frontend directory must contain index.html.")
    try:
        load_access_token(Path(__file__).resolve().parent.parent)
    except ValueError as error:
        parser.error(str(error))
    handler = lambda *h_args, **h_kwargs: LinuxCoreHandler(*h_args, directory=str(directory), **h_kwargs)
    server = ThreadingHTTPServer((args.bind, args.port), handler)
    server.daemon_threads = True
    print(f"LinuxCore local dashboard/proxy listening on {args.bind}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

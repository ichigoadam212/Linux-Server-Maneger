#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().with_name("local-web.py")
SPEC = importlib.util.spec_from_file_location("linuxcore_local_web", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

TOKEN = "aB3_cD4-eF5_gH6-iJ7_kL8-mN9_pQ0-rS1_tU2"


class FakeResponse:
    def __init__(self, body=b'{"status":"ok"}', status=200):
        self.body = body
        self.status = status
        self.headers = {"Content-Type": "application/json"}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size=-1):
        return self.body if size < 0 else self.body[:size]


class FakeOpener:
    def __init__(self, response=None):
        self.response = response or FakeResponse()
        self.request = None
        self.timeout = None

    def open(self, request, timeout):
        self.request = request
        self.timeout = timeout
        return self.response


class LocalProxyTests(unittest.TestCase):
    def test_token_is_read_from_dotenv_without_executing_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            env_file = root / "backend" / ".env"
            env_file.parent.mkdir()
            marker = root / "must-not-exist"
            env_file.write_text(
                f'LINUXCORE_ACCESS_TOKEN="{TOKEN}"\nMALICIOUS="$(touch {marker})"\n',
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(MODULE.load_access_token(root), TOKEN)
            self.assertFalse(marker.exists())

    def test_environment_token_takes_precedence_and_weak_token_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "backend").mkdir()
            (root / "backend" / ".env").write_text("LINUXCORE_ACCESS_TOKEN=" + TOKEN + "\n")
            override = "zY9_xW8-vU7_tS6-rQ5_pO4-nM3_lK2-jI1_hG0"
            with patch.dict(os.environ, {"LINUXCORE_ACCESS_TOKEN": override}, clear=True):
                self.assertEqual(MODULE.load_access_token(root), override)
            with patch.dict(os.environ, {"LINUXCORE_ACCESS_TOKEN": "short"}, clear=True):
                with self.assertRaises(ValueError):
                    MODULE.load_access_token(root)

    def test_health_proxy_adds_token_server_side_and_uses_fixed_loopback_origin(self):
        fake = FakeOpener()
        with patch.object(MODULE, "OPENER", fake):
            status, content_type, body = MODULE.forward_api_request(
                "GET", "/api/v1/health", b"", "", TOKEN
            )
        self.assertEqual(status, 200)
        self.assertEqual(content_type, "application/json")
        self.assertEqual(body, b'{"status":"ok"}')
        self.assertEqual(fake.request.full_url, "http://127.0.0.1:8000/api/v1/health")
        self.assertEqual(fake.request.get_header("Authorization"), "Bearer " + TOKEN)
        self.assertEqual(fake.timeout, 55)

    def test_without_token_no_authorization_header_is_forwarded(self):
        fake = FakeOpener()
        with patch.object(MODULE, "OPENER", fake):
            MODULE.forward_api_request("GET", "/api/v1/health", b"", "", "")
        self.assertIsNone(fake.request.get_header("Authorization"))

    def test_post_forwards_only_json_to_allowlisted_route(self):
        fake = FakeOpener()
        payload = b'{"command":"pwd"}'
        with patch.object(MODULE, "OPENER", fake):
            result = MODULE.forward_api_request(
                "POST", "/api/v1/terminal/run", payload, "application/json", TOKEN
            )
        self.assertEqual(result[0], 200)
        self.assertEqual(fake.request.data, payload)
        self.assertEqual(fake.request.get_header("Content-type"), "application/json")

    def test_static_site_routes_are_allowlisted_including_page_updates(self):
        fake = FakeOpener()
        page = b'{"content":"<h1>Site</h1>"}'
        with patch.object(MODULE, "OPENER", fake):
            status, _, body = MODULE.forward_api_request(
                "PUT", "/api/v1/apps/static-site/content", page, "application/json", TOKEN
            )
        self.assertEqual(status, 200)
        self.assertEqual(fake.request.full_url, "http://127.0.0.1:8000/api/v1/apps/static-site/content")
        self.assertEqual(fake.request.get_method(), "PUT")
        self.assertEqual(fake.request.data, page)
        self.assertEqual(fake.request.get_header("Content-type"), "application/json")

    def test_unlisted_path_and_wrong_method_are_rejected_before_network(self):
        fake = FakeOpener()
        with patch.object(MODULE, "OPENER", fake):
            not_allowed = MODULE.forward_api_request("GET", "/api/v1/admin", b"", "", TOKEN)
            wrong_method = MODULE.forward_api_request("POST", "/api/v1/metrics", b"{}", "application/json", TOKEN)
        self.assertEqual(not_allowed[0], 404)
        self.assertEqual(wrong_method[0], 404)
        self.assertIsNone(fake.request)

    def test_query_strings_non_json_and_oversized_bodies_are_rejected(self):
        fake = FakeOpener()
        with patch.object(MODULE, "OPENER", fake):
            query = MODULE.forward_api_request("GET", "/api/v1/health?debug=1", b"", "", TOKEN)
            content_type = MODULE.forward_api_request("POST", "/api/v1/ai/chat", b"{}", "text/plain", TOKEN)
            oversized = MODULE.forward_api_request(
                "POST", "/api/v1/ai/chat", b"x" * (MODULE.MAX_REQUEST_BYTES + 1),
                "application/json", TOKEN
            )
        self.assertEqual(query[0], 400)
        self.assertEqual(content_type[0], 415)
        self.assertEqual(oversized[0], 413)
        self.assertIsNone(fake.request)

    def test_oversized_upstream_response_fails_closed(self):
        fake = FakeOpener(FakeResponse(b"x" * (MODULE.MAX_RESPONSE_BYTES + 1)))
        with patch.object(MODULE, "OPENER", fake):
            result = MODULE.forward_api_request("GET", "/api/v1/health", b"", "", TOKEN)
        self.assertEqual(result[0], 502)

    def test_no_redirect_handler_is_installed(self):
        self.assertTrue(any(isinstance(handler, MODULE.NoRedirect) for handler in MODULE.OPENER.handlers))


    def test_managed_service_routes_are_allowlisted_for_inventory_and_actions(self):
        fake = FakeOpener()
        action_body = b'{"action":"restart"}'
        with patch.object(MODULE, "OPENER", fake):
            inventory = MODULE.forward_api_request(
                "GET", "/api/v1/managed-services", b"", "", TOKEN
            )
            action = MODULE.forward_api_request(
                "POST", "/api/v1/managed-services/action", action_body,
                "application/json", TOKEN
            )
        self.assertEqual(inventory[0], 200)
        self.assertEqual(fake.request.full_url, "http://127.0.0.1:8000/api/v1/managed-services/action")
        self.assertEqual(action[0], 200)
        self.assertEqual(fake.request.data, action_body)



if __name__ == "__main__":
    unittest.main(verbosity=2)

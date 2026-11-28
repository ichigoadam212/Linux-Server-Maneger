#!/usr/bin/env python3
"""Regression tests for the AST-based Python security guard."""

import unittest

from check_python_security import inspect_source


class PythonSecurityTests(unittest.TestCase):
    def test_fixed_argument_subprocess_call_is_allowed(self):
        source = """
import subprocess
subprocess.run(["uname", "-a"], check=False)
"""
        self.assertEqual(inspect_source(source), [])

    def test_subprocess_shell_true_is_rejected(self):
        source = """
import subprocess
subprocess.run("uname -a", shell=True)
"""
        self.assertTrue(any("enable a shell" in item for item in inspect_source(source)))

    def test_dynamically_selected_shell_mode_is_rejected(self):
        source = """
from subprocess import run as execute
execute(["uname", "-a"], shell=use_shell)
"""
        self.assertTrue(any("enable a shell" in item for item in inspect_source(source)))

    def test_shell_wrappers_are_rejected(self):
        source = """
import subprocess
import os
subprocess.getoutput("uname -a")
os.system("uname -a")
"""
        findings = inspect_source(source)
        self.assertTrue(any("subprocess call must not invoke" in item for item in findings))
        self.assertTrue(any("shell-execution helper os.system" in item for item in findings))

    def test_asyncio_shell_subprocess_is_rejected(self):
        source = """
import asyncio
asyncio.create_subprocess_shell("uname -a")
"""
        self.assertTrue(any("create_subprocess_shell" in item for item in inspect_source(source)))

    def test_wildcard_cors_origin_is_rejected(self):
        source = """
app.add_middleware(CORSMiddleware, allow_origins=["*"])
"""
        self.assertTrue(any("wildcard CORS allow_origins" in item for item in inspect_source(source)))

    def test_broad_cors_regex_is_rejected(self):
        source = """
app.add_middleware(CORSMiddleware, allow_origin_regex="https?://.*")
"""
        self.assertTrue(any("accepts untrusted origins" in item for item in inspect_source(source)))

    def test_wildcard_methods_and_headers_are_rejected(self):
        source = """
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:8080"], allow_methods=["*"], allow_headers=["*"])
"""
        findings = inspect_source(source)
        self.assertTrue(any("wildcard CORS allow_methods" in item for item in findings))
        self.assertTrue(any("wildcard CORS allow_headers" in item for item in findings))

    def test_dynamic_cors_origin_configuration_is_rejected(self):
        source = """
app.add_middleware(CORSMiddleware, allow_origins=trusted_origins)
"""
        self.assertTrue(any("must be a literal allowlist" in item for item in inspect_source(source)))

    def test_unpacked_cors_settings_are_rejected(self):
        source = """
from fastapi.middleware.cors import CORSMiddleware as Cors
app.add_middleware(Cors, **settings)
"""
        self.assertTrue(any("unpacked CORS settings" in item for item in inspect_source(source)))

    def test_explicit_local_cors_allowlist_is_allowed(self):
        source = """
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8080", "http://localhost:8080"],
    allow_methods=["GET", "POST"],
    allow_headers=["Accept", "Content-Type"],
)
"""
        self.assertEqual(inspect_source(source), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

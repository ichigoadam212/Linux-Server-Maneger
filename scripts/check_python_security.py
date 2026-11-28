#!/usr/bin/env python3
"""AST-based checks for unsafe Python subprocess and broad CORS configuration."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

_SUBPROCESS_METHODS = {
    "run", "Popen", "call", "check_call", "check_output",
    "getoutput", "getstatusoutput",
}
_ALWAYS_SHELL_SUBPROCESS_METHODS = {"getoutput", "getstatusoutput"}
_OS_SHELL_METHODS = {"system", "popen"}
_UNTRUSTED_ORIGINS = (
    "https://attacker.invalid",
    "http://attacker.invalid",
    "https://evil.example",
)


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _imports(tree: ast.AST) -> tuple[set[str], set[str], set[str], set[str], set[str]]:
    subprocess_modules = {"subprocess"}
    subprocess_functions: set[str] = set()
    os_modules = {"os"}
    os_functions: set[str] = set()
    cors_names = {"CORSMiddleware"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "subprocess":
                    subprocess_modules.add(alias.asname or "subprocess")
                elif alias.name == "os":
                    os_modules.add(alias.asname or "os")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "subprocess":
                subprocess_functions.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name in _SUBPROCESS_METHODS
                )
            elif node.module == "os":
                os_functions.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name in _OS_SHELL_METHODS
                )
            elif node.module and node.module.endswith("middleware.cors"):
                cors_names.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name == "CORSMiddleware"
                )

    return subprocess_modules, subprocess_functions, os_modules, os_functions, cors_names


def _is_wildcard(value: object) -> bool:
    if isinstance(value, str):
        return value.strip() == "*"
    if isinstance(value, (list, tuple, set)):
        return any(_is_wildcard(item) for item in value)
    return False


def _literal(node: ast.AST) -> tuple[bool, object]:
    try:
        return True, ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return False, None


def inspect_source(source: str, filename: str = "<source>") -> list[str]:
    """Return line-specific security findings for one Python source string."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        return [f"{filename}:{exc.lineno or 1}: Python syntax could not be inspected: {exc.msg}"]

    subprocess_modules, subprocess_functions, os_modules, os_functions, cors_names = _imports(tree)
    findings: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        function_name = _dotted_name(node.func)
        shell_keyword = next((item for item in node.keywords if item.arg == "shell"), None)

        is_subprocess_call = (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in subprocess_modules
            and node.func.attr in _SUBPROCESS_METHODS
        ) or (
            isinstance(node.func, ast.Name)
            and node.func.id in subprocess_functions
        )
        is_always_shell = (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in _ALWAYS_SHELL_SUBPROCESS_METHODS
        ) or (
            isinstance(node.func, ast.Name)
            and node.func.id in subprocess_functions
            and node.func.id in _ALWAYS_SHELL_SUBPROCESS_METHODS
        )
        if is_subprocess_call and (
            is_always_shell
            or (
                shell_keyword is not None
                and not (
                    _literal(shell_keyword.value)[0]
                    and _literal(shell_keyword.value)[1] is False
                )
            )
        ):
            findings.append(
                f"{filename}:{node.lineno}: subprocess call must not invoke or enable a shell"
            )

        is_os_shell_call = (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in os_modules
            and node.func.attr in _OS_SHELL_METHODS
        ) or (
            isinstance(node.func, ast.Name)
            and node.func.id in os_functions
        ) or function_name.endswith("create_subprocess_shell")
        if is_os_shell_call:
            findings.append(
                f"{filename}:{node.lineno}: shell-execution helper {function_name} is not allowed"
            )

        first_arg_is_cors = bool(node.args) and (
            _dotted_name(node.args[0]).split(".")[-1] in cors_names
        )
        is_cors_middleware = (
            function_name.split(".")[-1] in cors_names
            or (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_middleware"
                and first_arg_is_cors
            )
        )
        cors_keywords = {
            item.arg: item.value
            for item in node.keywords
            if item.arg in {"allow_origins", "allow_origin_regex", "allow_methods", "allow_headers"}
        }
        if is_cors_middleware and any(item.arg is None for item in node.keywords):
            findings.append(
                f"{filename}:{node.lineno}: unpacked CORS settings cannot be statically verified"
            )
        if not cors_keywords:
            continue

        if "allow_origins" in cors_keywords:
            known, origins = _literal(cors_keywords["allow_origins"])
            if not known:
                findings.append(
                    f"{filename}:{node.lineno}: CORS allow_origins must be a literal allowlist"
                )
            elif _is_wildcard(origins):
                findings.append(
                    f"{filename}:{node.lineno}: wildcard CORS allow_origins is not allowed"
                )

        for key in ("allow_methods", "allow_headers"):
            if key in cors_keywords:
                known, value = _literal(cors_keywords[key])
                if not known:
                    findings.append(
                        f"{filename}:{node.lineno}: CORS {key} must be a literal allowlist"
                    )
                elif _is_wildcard(value):
                    findings.append(
                        f"{filename}:{node.lineno}: wildcard CORS {key} is not allowed"
                    )

        if "allow_origin_regex" in cors_keywords:
            known, pattern = _literal(cors_keywords["allow_origin_regex"])
            if not known or not isinstance(pattern, str):
                findings.append(
                    f"{filename}:{node.lineno}: CORS allow_origin_regex must be a literal, reviewed pattern"
                )
            else:
                try:
                    compiled = re.compile(pattern)
                except re.error:
                    findings.append(
                        f"{filename}:{node.lineno}: CORS allow_origin_regex is invalid"
                    )
                else:
                    if any(compiled.fullmatch(origin) for origin in _UNTRUSTED_ORIGINS):
                        findings.append(
                            f"{filename}:{node.lineno}: CORS allow_origin_regex accepts untrusted origins"
                        )

    return findings


def python_files(paths: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            files.add(path)
        elif path.is_dir():
            files.update(
                item for item in path.rglob("*.py")
                if "__pycache__" not in item.parts
            )
    return sorted(files)


def check_paths(paths: list[Path]) -> list[str]:
    files = python_files(paths)
    if not files:
        return ["No Python files were found in the requested security-check paths."]

    findings: list[str] = []
    for path in files:
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(f"{path}: could not read Python source: {exc}")
            continue
        findings.extend(inspect_source(source, str(path)))
    return findings


def main(argv: list[str]) -> int:
    if not argv:
        print("Usage: check_python_security.py PATH [PATH ...]", file=sys.stderr)
        return 2

    paths = [Path(item) for item in argv]
    findings = check_paths(paths)
    if findings:
        for finding in findings:
            print(f"FAIL: {finding}", file=sys.stderr)
        return 1

    count = len(python_files(paths))
    print(
        "OK: no shell-enabled subprocess calls or broad CORS settings "
        f"detected in {count} Python file(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

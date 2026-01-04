"""Vite Doctor - Diagnostic Tool.

This module provides a best-effort diagnostic utility that checks Litestar ↔ Vite configuration alignment.
Regex patterns used for vite.config parsing are compiled at import time to avoid repeated compilation overhead.
"""

import os
import re
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]
from litestar.serialization import decode_json, encode_json
from rich.console import Group
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.table import Table

from litestar_vite.config import ExternalDevServer, TypeGenConfig

if TYPE_CHECKING:
    from litestar_vite.config import ViteConfig


def _str_list_factory() -> list[str]:
    """Return an empty ``list[str]`` (typed for pyright).

    Returns:
        An empty list.
    """
    return []


_VITE_CONFIG_PATTERNS: dict[str, re.Pattern[str]] = {
    "asset_url": re.compile(r"""assetUrl\s*:\s*['"]([^'"]+)['"]"""),
    "bundle_dir": re.compile(r"""bundleDir\s*:\s*['"]([^'"]+)['"]"""),
    "resource_dir": re.compile(r"""resourceDir\s*:\s*['"]([^'"]+)['"]"""),
    "static_dir": re.compile(r"""staticDir\s*:\s*['"]([^'"]+)['"]"""),
    "hot_file": re.compile(r"""hotFile\s*:\s*['"]([^'"]+)['"]"""),
    "inertia_mode": re.compile(r"""inertiaMode\s*:\s*(true|false)"""),
    "types_enabled": re.compile(r"""types\s*:\s*{\s*enabled\s*:\s*(true|false)"""),
    "types_output": re.compile(r"""output\s*:\s*['"]([^'"]+)['"]"""),
    "types_openapi": re.compile(r"""openapiPath\s*:\s*['"]([^'"]+)['"]"""),
    "types_routes": re.compile(r"""routesPath\s*:\s*['"]([^'"]+)['"]"""),
    "types_generate_zod": re.compile(r"""generateZod\s*:\s*(true|false)"""),
    "types_generate_sdk": re.compile(r"""generateSdk\s*:\s*(true|false)"""),
}

_LITESTAR_CONFIG_START = re.compile(r"\blitestar\s*\(\s*{", re.MULTILINE)


def _format_ts_literal(value: Any) -> str:
    """Format a Python value as a TypeScript literal for basic primitives.

    Returns:
        A TypeScript literal string.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{s}'"


def _extract_braced_block(source: str, open_brace_index: int) -> tuple[str, int, int] | None:
    """Extract a balanced braced block from ``source`` starting at ``open_brace_index``.

    Best-effort parser intended for typical vite.config.* formatting. Ignores braces
    inside quoted strings.

    Returns:
        A tuple of (extracted block, start index, end index), or None if not found.
    """
    if open_brace_index < 0 or open_brace_index >= len(source) or source[open_brace_index] != "{":
        return None

    depth = 0
    in_string: str | None = None
    escape = False

    for i in range(open_brace_index, len(source)):
        ch = source[i]
        if in_string is not None:
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == in_string:
                in_string = None
            continue

        if ch in {"'", '"', "`"}:
            in_string = ch
            continue

        if ch == "{":
            depth += 1
            continue
        if ch == "}":
            depth -= 1
            if depth == 0:
                return source[open_brace_index : i + 1], open_brace_index, i + 1

    return None


def _rel_to_root(path: Path | None, root: Path) -> str:
    """Return a stable string representation of ``path`` relative to ``root`` when possible.

    Args:
        path: Candidate path to render.
        root: Root directory for relative rendering.

    Returns:
        A relative path string when ``path`` is under ``root``, otherwise a short fallback representation.
    """
    if path is None:
        return ""
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        parts = path.resolve().parts
        return "/".join(parts[-3:])


@dataclass
class DoctorIssue:
    """Represents a detected configuration issue."""

    check: str
    severity: Literal["error", "warning"]
    message: str
    fix_hint: str
    auto_fixable: bool = False
    context: dict[str, Any] | None = None


@dataclass
class ParsedViteConfig:
    """Parsed values from vite.config.* file."""

    path: Path
    content: str
    litestar_config_block: str | None = None
    has_litestar_config: bool = False
    asset_url: str | None = None
    bundle_dir: str | None = None
    resource_dir: str | None = None
    static_dir: str | None = None
    hot_file: str | None = None
    inertia_mode: bool | None = None
    types_setting: Literal["auto"] | bool | None = None
    inputs: list[str] = field(default_factory=_str_list_factory)
    types_enabled: bool | None = None
    types_output: str | None = None
    types_openapi_path: str | None = None
    types_routes_path: str | None = None
    types_generate_zod: bool | None = None
    types_generate_sdk: bool | None = None


class ViteDoctor:
    """Diagnose and fix Vite configuration issues."""

    def __init__(self, config: "ViteConfig", verbose: bool = False) -> None:
        self.config = config
        self.verbose = verbose
        self.issues: list[DoctorIssue] = []
        self.vite_config_path: Path | None = None
        self.parsed_config: ParsedViteConfig | None = None
        self.bridge_path: Path | None = None
        self.bridge_config: dict[str, Any] | None = None

    def run(
        self, fix: bool = False, no_prompt: bool = False, *, show_config: bool = False, runtime_checks: bool = False
    ) -> bool:
        """Run diagnostics and optionally fix issues.

        When ``fix=True``, auto-fixable issues may be applied and the checks will be run again to produce an accurate
        final status.

        Returns:
            True if healthy (after fixes), False if issues remain.
        """
        self.issues = []
        self.vite_config_path = None
        self.parsed_config = None
        self.bridge_path = None
        self.bridge_config = None

        console.rule("[blue]Vite[/] Doctor Diagnostics", align="left")

        self._locate_vite_config()
        if not self.vite_config_path or not self.parsed_config:
            console.print("[red]✗ Could not locate or parse vite.config.* file[/]")
            return False

        self._locate_bridge_file()
        self._maybe_load_bridge_config()

        self._print_config_snapshot(show_bridge=show_config)

        self._check_litestar_plugin_config()
        self._check_bridge_file()
        self._check_paths_exist()
        self._check_asset_url()
        self._check_hot_file()
        self._check_bundle_dir()
        self._check_resource_dir()
        self._check_static_dir()
        self._check_inertia_mode()
        self._check_types_setting_alignment()
        self._check_input_paths()
        self._check_typegen_paths()
        self._check_typegen_flags()
        self._check_plugin_spread()
        self._check_dist_files()
        self._check_hotfile_presence()
        self._check_manifest_presence()
        self._check_typegen_artifacts()
        self._check_env_alignment()

        self._check_node_modules()
        if runtime_checks:
            self._check_hotfile_presence()
            self._check_vite_server_reachable()

        self._print_report()

        errors = [i for i in self.issues if i.severity == "error"]
        warnings = [i for i in self.issues if i.severity != "error"]

        if not self.issues:
            console.print("\n[green]✓ No issues found. Configuration looks healthy.[/]")
            return True

        if not errors and warnings:
            console.print(f"\n[green]✓ No errors found.[/] [yellow]{len(warnings)} warning(s) detected.[/]")

        if fix:
            fixed = self._apply_fixes(no_prompt)
            if not fixed:
                return False
            return self.run(fix=False, no_prompt=no_prompt, show_config=show_config)

        return not errors

    def _locate_vite_config(self) -> None:
        """Find and parse the vite.config file."""
        root = self.config.root_dir or Path.cwd()
        for ext in [".ts", ".js", ".mts", ".mjs"]:
            path = root / f"vite.config{ext}"
            if path.exists():
                self.vite_config_path = path
                content = path.read_text()
                self.parsed_config = self._parse_vite_config(path, content)
                if self.verbose:
                    console.print(f"[dim]Found config at {path}[/]")
                return

    def _locate_bridge_file(self) -> None:
        """Locate the .litestar.json bridge file."""
        root = self.config.root_dir or Path.cwd()
        self.bridge_path = root / ".litestar.json"

    def _maybe_load_bridge_config(self) -> None:
        """Load .litestar.json if present."""
        if self.bridge_path is None or not self.bridge_path.exists():
            return
        try:
            decoded = decode_json(self.bridge_path.read_bytes())
            if isinstance(decoded, dict):
                self.bridge_config = decoded
        except Exception as e:  # noqa: BLE001 - diagnostic tool
            self.bridge_config = {"__error__": str(e)}

    def _parse_vite_config(self, path: Path, content: str) -> ParsedViteConfig:
        """Regex-based parsing of vite.config content.

        Parsing is restricted to the ``litestar({ ... })`` config block when present to reduce false positives.
        Inputs and type settings are parsed best-effort to allow slightly different formatting styles.

        Returns:
            ParsedViteConfig instance with extracted values.
        """
        parsed = ParsedViteConfig(path=path, content=content, inputs=[])

        config_source = content
        match = _LITESTAR_CONFIG_START.search(content)
        if match:
            open_brace_index = content.find("{", match.start())
            extracted = _extract_braced_block(content, open_brace_index)
            if extracted is not None:
                block, _, _ = extracted
                parsed.litestar_config_block = block
                parsed.has_litestar_config = True
                config_source = block

        input_single = re.search(r"""input\s*:\s*['"]([^'"]+)['"]""", config_source)
        if input_single:
            parsed.inputs.append(input_single.group(1))
        input_array = re.search(r"""input\s*:\s*\[([^\]]*)\]""", config_source, flags=re.DOTALL)
        if input_array:
            parsed.inputs.extend(re.findall(r"""['"]([^'"]+)['"]""", input_array.group(1)))

        if re.search(r"""types\s*:\s*['"]auto['"]""", config_source):
            parsed.types_setting = "auto"
        else:
            types_bool = re.search(r"""types\s*:\s*(true|false)\b""", config_source)
            if types_bool:
                parsed.types_setting = types_bool.group(1) == "true"

        str_key_map: dict[str, str] = {
            "asset_url": "asset_url",
            "bundle_dir": "bundle_dir",
            "resource_dir": "resource_dir",
            "static_dir": "static_dir",
            "hot_file": "hot_file",
            "types_output": "types_output",
            "types_openapi": "types_openapi_path",
            "types_routes": "types_routes_path",
        }
        bool_key_map: dict[str, str] = {
            "inertia_mode": "inertia_mode",
            "types_enabled": "types_enabled",
            "types_generate_zod": "types_generate_zod",
            "types_generate_sdk": "types_generate_sdk",
        }

        for key, pattern in _VITE_CONFIG_PATTERNS.items():
            found = pattern.search(config_source)
            if not found:
                continue
            val = found.group(1)

            attr_name = str_key_map.get(key)
            if attr_name is not None:
                setattr(parsed, attr_name, val)
                continue

            attr_name = bool_key_map.get(key)
            if attr_name is not None:
                setattr(parsed, attr_name, val == "true")

        return parsed

    def _apply_write_bridge_fix(self) -> bool:
        if self.bridge_path is None:
            return False
        expected = self._expected_bridge_payload()
        if self.bridge_path.exists():
            bridge_backup = self.bridge_path.with_suffix(self.bridge_path.suffix + ".bak")
            bridge_backup.write_bytes(self.bridge_path.read_bytes())
            console.print(f"[dim]Created backup at {bridge_backup}[/]")
        self.bridge_path.write_bytes(encode_json(expected))
        console.print("[green]✓ Wrote .litestar.json[/]")
        return True

    def _apply_vite_key_fix(self, content: str, *, key: str, expected: Any) -> tuple[str, bool]:
        expected_literal = _format_ts_literal(expected)
        expected_str = str(expected)
        expected_bool = "true" if expected is True else "false" if expected is False else None

        bool_pattern = rf"({key}\s*:\s*)(true|false)\b"
        if expected_bool is not None and re.search(bool_pattern, content):
            content = re.sub(bool_pattern, rf"\g<1>{expected_bool}", content, count=1)
            return content, True

        quoted_pattern = rf"({key}\s*:\s*['\"])([^'\"]+)(['\"])"
        if re.search(quoted_pattern, content):
            content = re.sub(quoted_pattern, rf"\g<1>{expected_str}\g<3>", content, count=1)
            return content, True

        insert_match = _LITESTAR_CONFIG_START.search(content)
        if insert_match:
            brace_index = content.find("{", insert_match.start())
            line_start = content.rfind("\n", 0, brace_index) + 1
            indent_match = re.match(r"\s*", content[line_start:brace_index])
            indent = indent_match.group(0) if indent_match else ""
            insertion = f"\n{indent}  {key}: {expected_literal},"
            content = content[: brace_index + 1] + insertion + content[brace_index + 1 :]
            return content, True

        return content, False

    def _resolve_to_root(self, path: Path) -> Path:
        root = self.config.root_dir or Path.cwd()
        return path if path.is_absolute() else (root / path)

    def _check_litestar_plugin_config(self) -> None:
        """Ensure the vite.config includes a litestar({ ... }) plugin config."""
        if not self.parsed_config:
            return
        if self.parsed_config.has_litestar_config:
            return

        self.issues.append(
            DoctorIssue(
                check="Missing litestar() Plugin Config",
                severity="error",
                message=f"{self.parsed_config.path.name} does not appear to contain a litestar({{...}}) call",
                fix_hint=(
                    "Add the plugin to vite.config, e.g. `import litestar from 'litestar-vite-plugin'` and "
                    "`plugins: [litestar({ input: ['src/main.ts'] })]`"
                ),
                auto_fixable=False,
            )
        )

    def _expected_bridge_payload(self) -> dict[str, Any]:
        """Build the expected .litestar.json payload from the active Python config.

        Returns:
            A dictionary representing the expected bridge configuration.
        """
        types = self.config.types if isinstance(self.config.types, TypeGenConfig) else None
        deploy = self.config.deploy_config
        return {
            "assetUrl": self.config.asset_url,
            "deployAssetUrl": deploy.asset_url if deploy is not None and deploy.asset_url else None,
            "bundleDir": str(self.config.bundle_dir),
            "hotFile": self.config.hot_file,
            "resourceDir": str(self.config.resource_dir),
            "staticDir": str(self.config.static_dir),
            "manifest": self.config.manifest_name,
            "mode": self.config.mode,
            "proxyMode": self.config.proxy_mode,
            "port": self.config.port,
            "host": self.config.host,
            "ssrOutDir": str(self.config.ssr_output_dir) if self.config.ssr_output_dir else None,
            "types": (
                {
                    "enabled": True,
                    "output": str(types.output),
                    "openapiPath": str(types.openapi_path),
                    "routesPath": str(types.routes_path),
                    "generateZod": types.generate_zod,
                    "generateSdk": types.generate_sdk,
                }
                if types
                else None
            ),
        }

    def _check_bridge_file(self) -> None:
        """Validate presence and consistency of .litestar.json when enabled."""
        if not self.config.set_environment:
            return
        if self.bridge_path is None:
            return

        if not self.bridge_path.exists():
            self.issues.append(
                DoctorIssue(
                    check="Missing .litestar.json",
                    severity="warning",
                    message=f"{self.bridge_path} not found (Vite plugin auto-config may fall back to defaults)",
                    fix_hint=(
                        "Start your app (`litestar run`) or `litestar assets serve` to generate it, or run "
                        "`litestar assets doctor --fix` to write it now"
                    ),
                    auto_fixable=True,
                    context={"action": "write_bridge"},
                )
            )
            return

        if self.bridge_config is None:
            return

        if "__error__" in self.bridge_config:
            self.issues.append(
                DoctorIssue(
                    check="Invalid .litestar.json",
                    severity="error",
                    message=str(self.bridge_config.get("__error__")),
                    fix_hint=(
                        "Run `litestar assets doctor --fix` to rewrite it (a .bak backup is created). If you prefer, "
                        "starting your app (`litestar run`) will overwrite it on startup when `runtime.set_environment=True`"
                    ),
                    auto_fixable=True,
                    context={"action": "write_bridge"},
                )
            )
            return

        expected = self._expected_bridge_payload()
        mismatched: list[str] = []
        root = self.config.root_dir or Path.cwd()
        for key, exp in expected.items():
            actual = self.bridge_config.get(key)
            if key in {"bundleDir", "resourceDir", "staticDir", "ssrOutDir"}:
                exp_path = (root / exp) if isinstance(exp, str) and exp and not Path(exp).is_absolute() else exp
                act_path = (
                    (root / actual) if isinstance(actual, str) and actual and not Path(actual).is_absolute() else actual
                )
                if str(exp_path).rstrip("/") != str(act_path).rstrip("/"):
                    mismatched.append(key)
            elif actual != exp:
                mismatched.append(key)

        if mismatched:
            self.issues.append(
                DoctorIssue(
                    check="Stale .litestar.json",
                    severity="warning",
                    message=f"Bridge config differs from Python config for: {', '.join(sorted(mismatched))}",
                    fix_hint=(
                        "Run `litestar assets doctor --fix` to rewrite it (a .bak backup is created). "
                        "Or just restart your app (`litestar run`) to overwrite it on startup when `runtime.set_environment=True`"
                    ),
                    auto_fixable=True,
                    context={"action": "write_bridge"},
                )
            )

    def _check_paths_exist(self) -> None:
        """Validate core Python paths exist."""
        root = self.config.root_dir or Path.cwd()
        resource_dir = self._resolve_to_root(self.config.resource_dir)
        static_dir = self._resolve_to_root(self.config.static_dir)

        if not resource_dir.exists():
            self.issues.append(
                DoctorIssue(
                    check="Missing resource_dir",
                    severity="error",
                    message=f"resource_dir does not exist: {_rel_to_root(resource_dir, root)}",
                    fix_hint="Create the directory or update ViteConfig.paths.resource_dir to the correct source folder",
                    auto_fixable=False,
                )
            )

        if not static_dir.exists():
            self.issues.append(
                DoctorIssue(
                    check="Missing static_dir",
                    severity="warning",
                    message=f"static_dir does not exist: {_rel_to_root(static_dir, root)}",
                    fix_hint=f"Create the directory or update ViteConfig.paths.static_dir (often `${resource_dir}/public`)",
                    auto_fixable=False,
                )
            )

    def _check_asset_url(self) -> None:
        """Check if Python asset_url matches JS assetUrl."""
        if not self.parsed_config:
            return

        py_url = self.config.asset_url
        js_url = self.parsed_config.asset_url

        py_norm = py_url.rstrip("/")
        js_norm = (js_url or "").rstrip("/")

        if js_url and py_norm != js_norm:
            self.issues.append(
                DoctorIssue(
                    check="Asset URL Mismatch",
                    severity="error",
                    message=f"Python asset_url '{py_url}' != JS assetUrl '{js_url}'",
                    fix_hint=f"Update vite.config to use assetUrl: '{py_url}'",
                    auto_fixable=True,
                    context={"key": "assetUrl", "expected": py_url},
                )
            )

    def _check_hot_file(self) -> None:
        """Check if Python hot_file matches JS hotFile.

        Litestar's Python config stores ``hot_file`` as a filename (default ``hot``), while the JS plugin commonly
        uses a full path defaulting to ``${bundleDir}/hot``. This check only warns when JS explicitly sets ``hotFile``
        to a value that diverges from the Python expectation.
        """
        if not self.parsed_config:
            return
        expected_hot = f"{self.config.bundle_dir}/{self.config.hot_file}".replace("//", "/")
        js_hot = self.parsed_config.hot_file

        if js_hot and js_hot != expected_hot:
            self.issues.append(
                DoctorIssue(
                    check="Hot File Mismatch",
                    severity="warning",
                    message=f"JS hotFile '{js_hot}' differs from Python default '{expected_hot}'",
                    fix_hint=f"Update vite.config to use hotFile: '{expected_hot}'",
                    auto_fixable=True,
                    context={"key": "hotFile", "expected": expected_hot},
                )
            )

    def _check_bundle_dir(self) -> None:
        """Check bundle directory match."""
        if not self.parsed_config:
            return

        py_dir = str(self.config.bundle_dir)
        js_dir = self.parsed_config.bundle_dir

        if js_dir and py_dir != js_dir:
            self.issues.append(
                DoctorIssue(
                    check="Bundle Directory Mismatch",
                    severity="error",
                    message=f"Python bundle_dir '{py_dir}' != JS bundleDir '{js_dir}'",
                    fix_hint=f"Update vite.config to use bundleDir: '{py_dir}'",
                    auto_fixable=True,
                    context={"key": "bundleDir", "expected": py_dir},
                )
            )

    def _check_resource_dir(self) -> None:
        """Check resource directory match when explicitly set in vite.config."""
        if not self.parsed_config:
            return

        py_dir = str(self.config.resource_dir)
        js_dir = self.parsed_config.resource_dir

        if js_dir and py_dir != js_dir:
            self.issues.append(
                DoctorIssue(
                    check="Resource Directory Mismatch",
                    severity="warning",
                    message=f"Python resource_dir '{py_dir}' != JS resourceDir '{js_dir}'",
                    fix_hint=f"Update vite.config to use resourceDir: '{py_dir}' (or remove it to auto-read from .litestar.json)",
                    auto_fixable=True,
                    context={"key": "resourceDir", "expected": py_dir},
                )
            )

    def _check_static_dir(self) -> None:
        """Check static directory match when explicitly set in vite.config."""
        if not self.parsed_config:
            return

        py_dir = str(self.config.static_dir)
        js_dir = self.parsed_config.static_dir

        if js_dir and py_dir != js_dir:
            self.issues.append(
                DoctorIssue(
                    check="Static Directory Mismatch",
                    severity="warning",
                    message=f"Python static_dir '{py_dir}' != JS staticDir '{js_dir}'",
                    fix_hint=f"Update vite.config to use staticDir: '{py_dir}' (or remove it to auto-read from .litestar.json)",
                    auto_fixable=True,
                    context={"key": "staticDir", "expected": py_dir},
                )
            )

    def _check_inertia_mode(self) -> None:
        """Warn when vite.config inertiaMode conflicts with Python mode."""
        if not self.parsed_config or self.parsed_config.inertia_mode is None:
            return

        py_inertia = self.config.mode == "inertia"
        js_inertia = self.parsed_config.inertia_mode

        if py_inertia != js_inertia:
            self.issues.append(
                DoctorIssue(
                    check="Inertia Mode Mismatch",
                    severity="warning",
                    message=(
                        f"Python mode={self.config.mode!r} implies inertiaMode={py_inertia}, "
                        f"but vite.config sets inertiaMode={js_inertia}"
                    ),
                    fix_hint="Remove inertiaMode from vite.config to auto-detect, or set it to match your Python mode",
                    auto_fixable=False,
                )
            )

    def _check_types_setting_alignment(self) -> None:
        """Warn when vite.config explicitly enables/disables types against Python config."""
        if not self.parsed_config:
            return

        py_types_enabled = isinstance(self.config.types, TypeGenConfig)
        js_setting = self.parsed_config.types_setting

        if py_types_enabled and js_setting is False:
            self.issues.append(
                DoctorIssue(
                    check="TypeGen Disabled in vite.config",
                    severity="warning",
                    message="Python types are enabled, but vite.config sets `types: false`",
                    fix_hint="Remove `types: false` or set `types: 'auto'` to read from .litestar.json",
                    auto_fixable=False,
                )
            )

        if not py_types_enabled and js_setting is True:
            self.issues.append(
                DoctorIssue(
                    check="TypeGen Enabled in vite.config",
                    severity="warning",
                    message="Python types are disabled, but vite.config sets `types: true`",
                    fix_hint="Disable types in vite.config, or enable TypeGenConfig in Python to keep both sides aligned",
                    auto_fixable=False,
                )
            )

    def _check_input_paths(self) -> None:
        """Check that configured entrypoints exist on disk (best-effort)."""
        if not self.parsed_config or not self.parsed_config.inputs:
            return

        root = self.config.root_dir or Path.cwd()
        missing: list[str] = []
        for input_path in self.parsed_config.inputs:
            p = Path(input_path)
            resolved = p if p.is_absolute() else (root / p)
            if not resolved.exists():
                missing.append(input_path)

        if missing:
            self.issues.append(
                DoctorIssue(
                    check="Missing Vite Inputs",
                    severity="error",
                    message=f"Entry point(s) not found: {', '.join(missing)}",
                    fix_hint="Update the `input` paths in vite.config or ensure the files exist under your frontend source folder",
                    auto_fixable=False,
                )
            )

    def _check_typegen_paths(self) -> None:
        """Check type generation paths when TypeGen is enabled on both sides.

        Only compares OpenAPI and routes output paths when the corresponding JS settings are explicitly present to
        avoid warning on JS defaults that may differ in representation (absolute vs relative).
        """
        if not self.parsed_config:
            return

        if not isinstance(self.config.types, TypeGenConfig):
            return

        if self.parsed_config.types_enabled:
            root = self.config.root_dir or Path.cwd()

            py_openapi_path = self.config.types.openapi_path
            if py_openapi_path is None:
                py_openapi_path = self.config.types.output / "openapi.json"
            js_openapi_path = (
                (root / self.parsed_config.types_openapi_path) if self.parsed_config.types_openapi_path else None
            )

            if self.parsed_config.types_openapi_path and _rel_to_root(py_openapi_path, root) != _rel_to_root(
                js_openapi_path, root
            ):
                self.issues.append(
                    DoctorIssue(
                        check="TypeGen OpenAPI Path Mismatch",
                        severity="warning",
                        message=f"Python '{py_openapi_path}' != JS '{js_openapi_path}'",
                        fix_hint=f"Update vite.config openapiPath to '{py_openapi_path}'",
                        auto_fixable=True,
                        context={"key": "openapiPath", "expected": str(py_openapi_path)},
                    )
                )

            py_routes_path = self.config.types.routes_path
            if py_routes_path is None:
                py_routes_path = self.config.types.output / "routes.json"
            js_routes_path = (
                (root / self.parsed_config.types_routes_path) if self.parsed_config.types_routes_path else None
            )

            if self.parsed_config.types_routes_path and _rel_to_root(py_routes_path, root) != _rel_to_root(
                js_routes_path, root
            ):
                self.issues.append(
                    DoctorIssue(
                        check="TypeGen Routes Path Mismatch",
                        severity="warning",
                        message=f"Python '{py_routes_path}' != JS '{js_routes_path}'",
                        fix_hint=f"Update vite.config routesPath to '{py_routes_path}'",
                        auto_fixable=True,
                        context={"key": "routesPath", "expected": str(py_routes_path)},
                    )
                )

    def _check_typegen_flags(self) -> None:
        """Check TypeGen flags when enabled on both sides.

        Only compares flags that are explicitly set in JS to avoid warning on JS defaults.
        """
        if not self.parsed_config:
            return

        if not isinstance(self.config.types, TypeGenConfig):
            return

        if self.parsed_config.types_enabled:
            py_zod = self.config.types.generate_zod
            js_zod = self.parsed_config.types_generate_zod

            if js_zod is not None and py_zod != js_zod:
                self.issues.append(
                    DoctorIssue(
                        check="TypeGen generateZod Mismatch",
                        severity="warning",
                        message=f"Python generate_zod={py_zod} != JS generateZod={js_zod}",
                        fix_hint=f"Update vite.config generateZod to {str(py_zod).lower()}",
                        auto_fixable=True,
                        context={"key": "generateZod", "expected": str(py_zod).lower()},
                    )
                )

            py_sdk = self.config.types.generate_sdk
            js_sdk = self.parsed_config.types_generate_sdk

            if js_sdk is not None and py_sdk != js_sdk:
                self.issues.append(
                    DoctorIssue(
                        check="TypeGen generateSdk Mismatch",
                        severity="warning",
                        message=f"Python generate_sdk={py_sdk} != JS generateSdk={js_sdk}",
                        fix_hint=f"Update vite.config generateSdk to {str(py_sdk).lower()}",
                        auto_fixable=True,
                        context={"key": "generateSdk", "expected": str(py_sdk).lower()},
                    )
                )

    def _check_plugin_spread(self) -> None:
        """No-op check kept for backwards compatibility.

        This check is intentionally disabled because Vite plugin arrays allow nested arrays; reliably detecting
        missing spread introduces false positives.
        """
        return

    def _check_dist_files(self) -> None:
        """Verify JS plugin dist files exist."""
        root = self.config.root_dir or Path.cwd()
        pkg_paths = [
            root / "node_modules" / "@litestar" / "vite-plugin" / "dist",
            root / "node_modules" / "litestar-vite-plugin" / "dist",
        ]

        dist_path = next((p for p in pkg_paths if p.exists()), None)

        if dist_path is None:
            self.issues.append(
                DoctorIssue(
                    check="Plugin Dist Missing",
                    severity="warning",
                    message="Could not find @litestar/vite-plugin dist files in node_modules",
                    fix_hint="Run `litestar assets install` to install frontend dependencies",
                    auto_fixable=False,
                )
            )
            return

        required_files = ["index.js", "install-hint.js", "litestar-meta.js"]
        missing = [f for f in required_files if not (dist_path / "js" / f).exists()]

        if missing:
            self.issues.append(
                DoctorIssue(
                    check="Corrupt Plugin Installation",
                    severity="error",
                    message=f"Missing required plugin files: {', '.join(missing)}",
                    fix_hint="Reinstall frontend dependencies with `litestar assets install` (or reinstall your package manager deps)",
                    auto_fixable=False,
                )
            )

    def _check_node_modules(self) -> None:
        """Check if node_modules directory exists."""
        root = self.config.root_dir or Path.cwd()
        node_modules = root / "node_modules"

        if not node_modules.exists():
            self.issues.append(
                DoctorIssue(
                    check="Node Modules Missing",
                    severity="error",
                    message="node_modules directory not found",
                    fix_hint="Run `litestar assets install` to install frontend dependencies",
                    auto_fixable=False,
                )
            )
        elif self.verbose:
            console.print("[dim]✓ node_modules directory exists[/]")

    def _check_vite_server_reachable(self) -> None:
        """Check if Vite dev server is reachable (only in dev mode)."""
        if not self.config.is_dev_mode:
            return

        host = self.config.host
        port = self.config.port

        if self.verbose:
            console.print(f"[dim]Checking Vite server at {host}:{port}...[/]")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()

            if result != 0:
                self.issues.append(
                    DoctorIssue(
                        check="Vite Server Not Running",
                        severity="warning",
                        message=f"Cannot connect to Vite server at {host}:{port}",
                        fix_hint="Start the server with `litestar assets serve` (and your backend with `litestar run` if needed)",
                        auto_fixable=False,
                    )
                )
            elif self.verbose:
                console.print(f"[dim]✓ Vite server reachable at {host}:{port}[/]")
        except OSError as e:
            self.issues.append(
                DoctorIssue(
                    check="Vite Server Check Failed",
                    severity="warning",
                    message=f"Could not check Vite server: {e}",
                    fix_hint="Ensure Vite server is running",
                    auto_fixable=False,
                )
            )

    def _check_hotfile_presence(self) -> None:
        """Warn if hotfile is missing when it's required for dynamic proxy targets."""
        if not self.config.is_dev_mode:
            return

        ext = self.config.runtime.external_dev_server
        needs_hotfile = self.config.proxy_mode == "proxy" or (
            isinstance(ext, ExternalDevServer) and ext.enabled and ext.target is None
        )
        if not needs_hotfile:
            return

        hot_path = self._resolve_to_root(self.config.bundle_dir) / self.config.hot_file
        if not hot_path.exists():
            self.issues.append(
                DoctorIssue(
                    check="Hotfile Missing",
                    severity="warning",
                    message=f"Hotfile not found at {hot_path}",
                    fix_hint=(
                        "If you're running in proxy mode (SSR/external server), start the server with "
                        "`litestar assets serve` so it can write the hotfile. Otherwise, ignore this check or run "
                        "`litestar assets doctor` without `--runtime-checks`."
                    ),
                    auto_fixable=False,
                )
            )

    def _check_manifest_presence(self) -> None:
        """Ensure manifest exists in non-dev mode."""
        if self.config.is_dev_mode:
            return

        candidates = self.config.candidate_manifest_paths()
        if not any(path.exists() for path in candidates):
            manifest_locations = " or ".join(str(path) for path in candidates)
            self.issues.append(
                DoctorIssue(
                    check="Manifest Missing",
                    severity="warning",
                    message=f"Manifest not found at {manifest_locations} (expected in production; ok during dev)",
                    fix_hint="Run `litestar assets build` before starting in production",
                    auto_fixable=False,
                )
            )

    def _check_typegen_artifacts(self) -> None:
        """Verify exported OpenAPI/routes when typegen is enabled."""
        if not isinstance(self.config.types, TypeGenConfig):
            return

        openapi_path = self.config.types.openapi_path
        if openapi_path is None:
            openapi_path = self.config.types.output / "openapi.json"
        routes_path = self.config.types.routes_path
        if routes_path is None:
            routes_path = self.config.types.output / "routes.json"

        if not openapi_path.exists():
            self.issues.append(
                DoctorIssue(
                    check="OpenAPI Export Missing",
                    severity="warning",
                    message=f"{openapi_path} not found",
                    fix_hint="Run litestar assets generate-types (or start the app with types enabled)",
                    auto_fixable=False,
                )
            )

        if not routes_path.exists():
            self.issues.append(
                DoctorIssue(
                    check="Routes Export Missing",
                    severity="warning",
                    message=f"{routes_path} not found",
                    fix_hint="Run litestar assets generate-types (or start the app with types enabled)",
                    auto_fixable=False,
                )
            )

    def _check_env_alignment(self) -> None:
        """Compare key env vars to active config to surface surprises."""
        env_mismatches: list[tuple[str, str, str]] = []
        comparisons = {
            "VITE_PORT": str(self.config.port),
            "VITE_HOST": self.config.host,
            "VITE_PROXY_MODE": self.config.proxy_mode,
            "VITE_PROTOCOL": self.config.protocol,
        }
        if self.config.base_url:
            comparisons["VITE_BASE_URL"] = self.config.base_url

        for key, expected in comparisons.items():
            actual = os.getenv(key)
            if actual is None:
                continue
            if str(actual).rstrip("/") != str(expected).rstrip("/"):
                env_mismatches.append((key, str(actual), str(expected)))

        if env_mismatches:
            mismatch_lines = ", ".join(f"{k}={a} (expected {e})" for k, a, e in env_mismatches)
            self.issues.append(
                DoctorIssue(
                    check="Env / Config Mismatch",
                    severity="warning",
                    message=mismatch_lines,
                    fix_hint="Unset conflicting env vars or align ViteConfig/runtime before running",
                    auto_fixable=False,
                )
            )

    def _print_config_snapshot(self, *, show_bridge: bool) -> None:
        """Print a detailed view of Python, .litestar.json, and vite.config settings."""
        if not self.parsed_config:
            return

        root = self.config.root_dir or Path.cwd()
        python_cfg = {
            "root": str(root),
            "mode": self.config.mode,
            "asset_url": self.config.asset_url,
            "bundle_dir": str(self.config.bundle_dir),
            "resource_dir": str(self.config.resource_dir),
            "static_dir": str(self.config.static_dir),
            "manifest": self.config.manifest_name,
            "hot_file": self.config.hot_file,
            "proxy_mode": self.config.proxy_mode,
            "dev_mode": self.config.is_dev_mode,
            "host": self.config.host,
            "port": self.config.port,
            "executor": self.config.runtime.executor,
            "set_environment": self.config.set_environment,
            "types_enabled": isinstance(self.config.types, TypeGenConfig),
        }

        js_cfg = {
            "has_litestar_config": self.parsed_config.has_litestar_config,
            "assetUrl": self.parsed_config.asset_url,
            "bundleDir": self.parsed_config.bundle_dir,
            "resourceDir": self.parsed_config.resource_dir,
            "staticDir": self.parsed_config.static_dir,
            "hotFile": self.parsed_config.hot_file,
            "inertiaMode": self.parsed_config.inertia_mode,
            "types": self.parsed_config.types_setting,
            "types.enabled": self.parsed_config.types_enabled,
            "types.output": self.parsed_config.types_output,
        }

        blocks: list[Any] = [
            "[bold]Python (effective)[/]",
            Syntax(encode_json(python_cfg).decode(), "json", theme="ansi_dark", word_wrap=True),
        ]

        if show_bridge and self.bridge_path is not None:
            bridge_obj: dict[str, Any] = {
                "path": str(self.bridge_path),
                "exists": self.bridge_path.exists(),
                "content": self.bridge_config or {},
            }
            blocks.extend([
                "[bold].litestar.json[/]",
                Syntax(encode_json(bridge_obj).decode(), "json", theme="ansi_dark", word_wrap=True),
            ])

        blocks.extend([
            "[bold]vite.config (litestar plugin)[/]",
            Syntax(encode_json(js_cfg).decode(), "json", theme="ansi_dark", word_wrap=True),
        ])

        if show_bridge and self.parsed_config.litestar_config_block:
            blocks.extend([
                "[bold]Extracted litestar({ ... }) block[/]",
                Syntax(self.parsed_config.litestar_config_block, "typescript", theme="ansi_dark", word_wrap=True),
            ])

        console.print(Panel(Group(*blocks), title="Config snapshot", border_style="dim"))

    def _print_report(self) -> None:
        """Print a table of detected issues."""
        if not self.issues:
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Severity", style="dim")
        table.add_column("Check")
        table.add_column("Message")
        table.add_column("Fix Hint")

        for issue in self.issues:
            severity_style = "red" if issue.severity == "error" else "yellow"
            table.add_row(f"[{severity_style}]{issue.severity.upper()}[/]", issue.check, issue.message, issue.fix_hint)

        console.print(table)

    def _apply_fixes(self, no_prompt: bool) -> bool:
        """Apply auto-fixes.

        Returns:
            True if fixes were applied, otherwise False.
        """
        if not self.parsed_config:
            return False

        fixable_issues = [i for i in self.issues if i.auto_fixable]
        if not fixable_issues:
            console.print("\n[yellow]No auto-fixable issues found.[/]")
            return False

        console.print(f"\n[bold]Found {len(fixable_issues)} auto-fixable issues.[/]")

        if not no_prompt and not Confirm.ask("Apply fixes?"):
            return False

        content = self.parsed_config.content

        will_edit_vite = self.vite_config_path is not None and any((i.context or {}).get("key") for i in fixable_issues)
        if will_edit_vite and self.vite_config_path is not None:
            backup_path = self.vite_config_path.with_suffix(self.vite_config_path.suffix + ".bak")
            backup_path.write_text(content)
            console.print(f"[dim]Created backup at {backup_path}[/]")

        for issue in fixable_issues:
            context = issue.context
            if not context:
                continue

            action = context.get("action")
            if action == "write_bridge":
                self._apply_write_bridge_fix()
                continue

            key = context.get("key")
            expected = context.get("expected")
            if not key or expected is None:
                continue

            content, updated = self._apply_vite_key_fix(content, key=key, expected=expected)
            if updated:
                console.print(f"[green]✓ Fixed {key}[/]")
            else:
                console.print(f"[red]✗ Failed to apply fix for {key} (pattern match failed)[/]")

        if will_edit_vite and self.vite_config_path is not None:
            self.vite_config_path.write_text(content)
        console.print("\n[bold green]Fixes applied. Please verify configuration.[/]")
        return True

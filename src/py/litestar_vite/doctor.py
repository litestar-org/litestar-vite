"""Vite Doctor - Diagnostic Tool."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]
from rich.prompt import Confirm
from rich.table import Table

if TYPE_CHECKING:
    from litestar_vite.config import ViteConfig


@dataclass
class DoctorIssue:
    """Represents a detected configuration issue."""

    check: str
    severity: str  # "error" or "warning"
    message: str
    fix_hint: str
    auto_fixable: bool = False
    context: dict[str, Any] | None = None


@dataclass
class ParsedViteConfig:
    """Parsed values from vite.config.* file."""

    path: Path
    content: str
    asset_url: str | None = None
    bundle_dir: str | None = None
    hot_file: str | None = None
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

    def run(self, fix: bool = False, no_prompt: bool = False) -> bool:
        """Run diagnostics and optionally fix issues.

        Returns:
            True if healthy (after fixes), False if issues remain.
        """
        console.rule("[yellow]Vite Doctor Diagnostics[/]", align="left")

        self._locate_vite_config()
        if not self.vite_config_path or not self.parsed_config:
            console.print("[red]✗ Could not locate or parse vite.config.* file[/]")
            return False

        self._check_asset_url()
        self._check_hot_file()
        self._check_bundle_dir()
        self._check_typegen_paths()
        self._check_typegen_flags()
        self._check_plugin_spread()
        self._check_dist_files()

        self._print_report()

        if not self.issues:
            console.print("\n[green]✓ No issues found. Configuration looks healthy.[/]")
            return True

        if fix:
            return self._apply_fixes(no_prompt)

        return False

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

    def _parse_vite_config(self, path: Path, content: str) -> ParsedViteConfig:
        """Regex-based parsing of vite.config content."""
        parsed = ParsedViteConfig(path=path, content=content)

        # Regex patterns
        # Using triple quotes to avoid escaping issues
        patterns = {
            "asset_url": r"""assetUrl\s*:\s*['"]([^'"']+)['"]""",
            "bundle_dir": r"""bundleDirectory\s*:\s*['"]([^'"']+)['"]""",
            "hot_file": r"""hotFile\s*:\s*['"]([^'"']+)['"]""",
            "types_enabled": r"""types\s*:\s*{\s*enabled\s*:\s*(true|false)""",
            "types_output": r"""output\s*:\s*['"]([^'"']+)['"]""",
            "types_openapi": r"""openapiPath\s*:\s*['"]([^'"']+)['"]""",
            "types_routes": r"""routesPath\s*:\s*['"]([^'"']+)['"]""",
            "types_generate_zod": r"""generateZod\s*:\s*(true|false)""",
            "types_generate_sdk": r"""generateSdk\s*:\s*(true|false)""",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                val = match.group(1)
                if key == "asset_url":
                    parsed.asset_url = val
                elif key == "bundle_dir":
                    parsed.bundle_dir = val
                elif key == "hot_file":
                    parsed.hot_file = val
                elif key == "types_enabled":
                    parsed.types_enabled = val == "true"
                elif key == "types_output":
                    parsed.types_output = val
                elif key == "types_openapi":
                    parsed.types_openapi_path = val
                elif key == "types_routes":
                    parsed.types_routes_path = val
                elif key == "types_generate_zod":
                    parsed.types_generate_zod = val == "true"
                elif key == "types_generate_sdk":
                    parsed.types_generate_sdk = val == "true"

        return parsed

    def _check_asset_url(self) -> None:
        """Check if Python asset_url matches JS assetUrl."""
        if not self.parsed_config:
            return

        py_url = self.config.asset_url
        js_url = self.parsed_config.asset_url

        # Normalize for comparison (strip trailing slashes)
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
        """Check if Python hot_file matches JS hotFile."""
        if not self.parsed_config:
            return

        # Python config stores just the filename usually, but plugin constructs full path
        # We need to check expectation. The JS plugin expects full path usually or relative to bundle.
        # Actually, Litestar config.hot_file is a filename (default "hot").
        # JS plugin config.hotFile defaults to `${bundleDirectory}/hot`.

        # If the user has a custom hotFile in JS, we should check if it aligns.
        # This check is tricky because of defaults.
        # Let's check if it's explicitly set in JS and differs from what we expect.

        # For now, simple check: if hotFile is set in JS, is it consistent with bundle_dir + hot_file?
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
                    message=f"Python bundle_dir '{py_dir}' != JS bundleDirectory '{js_dir}'",
                    fix_hint=f"Update vite.config to use bundleDirectory: '{py_dir}'",
                    auto_fixable=True,
                    context={"key": "bundleDirectory", "expected": py_dir},
                )
            )

    def _check_typegen_paths(self) -> None:
        """Check type generation paths."""
        if not self.parsed_config:
            return

        # Only check if types are enabled in Python config
        if isinstance(self.config.types, bool) or not self.config.types.enabled:
            return

        # If JS has types enabled, check paths
        if self.parsed_config.types_enabled:
            # Check openapi path
            py_openapi = str(self.config.types.openapi_path)
            js_openapi = self.parsed_config.types_openapi_path

            if js_openapi and py_openapi != js_openapi:
                self.issues.append(
                    DoctorIssue(
                        check="TypeGen OpenAPI Path Mismatch",
                        severity="warning",
                        message=f"Python '{py_openapi}' != JS '{js_openapi}'",
                        fix_hint=f"Update vite.config openapiPath to '{py_openapi}'",
                        auto_fixable=True,
                        context={"key": "openapiPath", "expected": py_openapi},
                    )
                )

            # Check routes path
            py_routes = str(self.config.types.routes_path)
            js_routes = self.parsed_config.types_routes_path

            if js_routes and py_routes != js_routes:
                self.issues.append(
                    DoctorIssue(
                        check="TypeGen Routes Path Mismatch",
                        severity="warning",
                        message=f"Python '{py_routes}' != JS '{js_routes}'",
                        fix_hint=f"Update vite.config routesPath to '{py_routes}'",
                        auto_fixable=True,
                        context={"key": "routesPath", "expected": py_routes},
                    )
                )

    def _check_typegen_flags(self) -> None:
        """Check type generation flags."""
        if not self.parsed_config:
            return

        if isinstance(self.config.types, bool) or not self.config.types.enabled:
            return

        if self.parsed_config.types_enabled:
            # Check generateZod
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

            # Check generateSdk
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
        """Check if the plugin is correctly spread in the config."""
        if not self.parsed_config:
            return

        # Check for litestar() usage without spread
        # Matches: plugins: [ ..., litestar({ ... }) ] (without ...)
        # We look for 'litestar(' that is NOT preceded by '...'

        # Simplified check: find "litestar(" and check preceding chars
        content = self.parsed_config.content

        # Find all occurrences of litestar(
        for match in re.finditer(r"(\.{3})?\s*litestar\s*\(", content):
            is_spread = match.group(1) == "..."
            if not is_spread:
                self.issues.append(
                    DoctorIssue(
                        check="Plugin Spread Missing",
                        severity="error",
                        message="The litestar plugin must be spread into the plugins array: ...litestar(...)",
                        fix_hint="Add the spread operator: ...litestar({...})",
                        auto_fixable=False,  # Hard to auto-fix reliably with regex
                    )
                )
                break

    def _check_dist_files(self) -> None:
        """Verify JS plugin dist files exist."""
        # This assumes standard node_modules structure
        root = self.config.root_dir or Path.cwd()
        dist_path = root / "node_modules" / "litestar-vite-plugin" / "dist"

        if not dist_path.exists():
            # Only a warning because they might be using a different package manager or structure
            self.issues.append(
                DoctorIssue(
                    check="Plugin Dist Missing",
                    severity="warning",
                    message="Could not find litestar-vite-plugin/dist in node_modules",
                    fix_hint="Run npm install / pnpm install",
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
                    fix_hint="Reinstall the plugin: npm install litestar-vite-plugin --force",
                    auto_fixable=False,
                )
            )

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
            table.add_row(
                f"[{severity_style}]{issue.severity.upper()}[/]",
                issue.check,
                issue.message,
                issue.fix_hint,
            )

        console.print(table)

    def _apply_fixes(self, no_prompt: bool) -> bool:
        """Apply auto-fixes."""
        if not self.vite_config_path or not self.parsed_config:
            return False

        fixable_issues = [i for i in self.issues if i.auto_fixable]
        if not fixable_issues:
            console.print("\n[yellow]No auto-fixable issues found.[/]")
            return False

        console.print(f"\n[bold]Found {len(fixable_issues)} auto-fixable issues.[/]")

        if not no_prompt and not Confirm.ask("Apply fixes?"):
            return False

        content = self.parsed_config.content

        # Create backup
        backup_path = self.vite_config_path.with_suffix(self.vite_config_path.suffix + ".bak")
        backup_path.write_text(content)
        console.print(f"[dim]Created backup at {backup_path}[/]")

        for issue in fixable_issues:
            if not issue.context:
                continue

            key = issue.context.get("key")
            expected = issue.context.get("expected")

            if key and expected:
                # Simple regex replacement for the key
                # This is simplistic and assumes standard formatting
                pattern = r"(" + key + r"""\s*:\s*['"])([^'"]+)(['"])"""

                if re.search(pattern, content):
                    content = re.sub(pattern, rf"\g<1>{expected}\g<3>", content)
                    console.print(f"[green]✓ Fixed {key}[/]")
                else:
                    console.print(f"[red]✗ Failed to apply fix for {key} (pattern match failed)[/]")

        self.vite_config_path.write_text(content)
        console.print("\n[bold green]Fixes applied. Please verify configuration.[/]")
        return True
#!/usr/bin/env python3
"""Project scanner for tool-agnostic PRD/implementation workflows."""

import argparse
import json
import re
from pathlib import Path
from typing import Any

LANGUAGE_MARKERS = {
    "python": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile", "uv.lock"],
    "typescript": ["tsconfig.json"],
    "javascript": ["package.json"],
    "rust": ["Cargo.toml"],
    "go": ["go.mod"],
    "ruby": ["Gemfile"],
    "dotnet": ["*.csproj", "*.sln"],
    "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "elixir": ["mix.exs"],
    "php": ["composer.json"],
}

FRAMEWORK_MARKERS = {
    "litestar": ["litestar"],
    "fastapi": ["fastapi"],
    "django": ["django"],
    "flask": ["flask"],
    "vite": ["vite"],
    "react": ["react"],
    "vue": ["vue"],
    "svelte": ["svelte"],
    "angular": ["@angular/core"],
    "nuxt": ["nuxt"],
    "sveltekit": ["@sveltejs/kit"],
    "astro": ["astro"],
}

PRD_ROOT_CANDIDATES = [
    ("specs/active", "specs"),
    ("specs", "specs"),
    ("docs/specs/active", "docs/specs"),
    ("docs/specs", "docs/specs"),
    ("docs/prd", "docs/prd"),
    ("docs/prds", "docs/prds"),
]


def _has_any(root: Path, names: list[str]) -> bool:
    for name in names:
        if "*" in name:
            if list(root.glob(name)):
                return True
        else:
            if (root / name).exists():
                return True
    return False


def _detect_languages(root: Path) -> list[str]:
    detected: list[str] = []
    for lang, markers in LANGUAGE_MARKERS.items():
        if _has_any(root, markers):
            detected.append(lang)
    return detected


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _parse_makefile_targets(makefile: Path) -> list[str]:
    targets: list[str] = []
    try:
        lines = makefile.read_text(encoding="utf-8").splitlines()
    except Exception:
        return targets
    for line in lines:
        if line.startswith("."):
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)\s*:", line)
        if match:
            targets.append(match.group(1))
    return sorted(set(targets))


def _detect_frameworks(package_json: dict[str, Any], pyproject: str) -> list[str]:
    deps = {}
    deps.update(package_json.get("dependencies", {}) or {})
    deps.update(package_json.get("devDependencies", {}) or {})
    frameworks: list[str] = []
    for name, markers in FRAMEWORK_MARKERS.items():
        if any(marker in deps for marker in markers):
            frameworks.append(name)
        elif _marker_in_text(pyproject, markers):
            frameworks.append(name)
    return sorted(set(frameworks))


def _marker_in_text(text: str, markers: list[str]) -> bool:
    return any(marker in text for marker in markers)


def _detect_package_manager(root: Path) -> str | None:
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    if (root / "bun.lockb").exists():
        return "bun"
    if (root / "package-lock.json").exists():
        return "npm"
    return None


def _detect_prd_root(root: Path) -> dict[str, str]:
    for candidate, base in PRD_ROOT_CANDIDATES:
        if (root / candidate).exists():
            return {"root": base, "active": f"{base}/active"}
    return {"root": "specs", "active": "specs/active"}


def _detect_commands(root: Path, package_json: dict[str, Any], make_targets: list[str]) -> dict[str, list[str]]:
    commands: dict[str, list[str]] = {"test": [], "lint": [], "build": [], "typecheck": []}

    scripts = package_json.get("scripts", {}) or {}

    if "test" in scripts:
        commands["test"].append(_pkg_cmd(root, "test"))
    if "lint" in scripts:
        commands["lint"].append(_pkg_cmd(root, "lint"))
    if "build" in scripts:
        commands["build"].append(_pkg_cmd(root, "build"))
    if "typecheck" in scripts:
        commands["typecheck"].append(_pkg_cmd(root, "typecheck"))

    if "test" in make_targets:
        commands["test"].insert(0, "make test")
    if "lint" in make_targets:
        commands["lint"].insert(0, "make lint")
    if "build" in make_targets:
        commands["build"].insert(0, "make build")
    if "type-check" in make_targets:
        commands["typecheck"].insert(0, "make type-check")

    return commands


def _pkg_cmd(root: Path, script: str) -> str:
    manager = _detect_package_manager(root) or "npm"
    if manager == "yarn":
        return f"yarn {script}"
    if manager == "pnpm":
        return f"pnpm {script}"
    if manager == "bun":
        return f"bun run {script}"
    return f"npm run {script}"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def scan_project(root: Path) -> dict[str, Any]:
    package_json_path = root / "package.json"
    pyproject_path = root / "pyproject.toml"
    makefile_path = root / "Makefile"

    package_json = _read_json(package_json_path) if package_json_path.exists() else {}
    pyproject_text = _read_text(pyproject_path) if pyproject_path.exists() else ""
    make_targets = _parse_makefile_targets(makefile_path) if makefile_path.exists() else []

    data = {
        "root": str(root),
        "languages": _detect_languages(root),
        "frameworks": _detect_frameworks(package_json, pyproject_text),
        "package_manager": _detect_package_manager(root),
        "make_targets": make_targets,
        "package_scripts": sorted(package_json.get("scripts", {}).keys()) if package_json else [],
        "commands": _detect_commands(root, package_json, make_targets),
        "prd": _detect_prd_root(root),
        "docs": {
            "readme": (root / "README.md").exists(),
            "claude": (root / "CLAUDE.md").exists(),
            "agents": (root / "AGENTS.md").exists(),
            "contributing": (root / "CONTRIBUTING.md").exists() or (root / "CONTRIBUTING.rst").exists(),
        },
    }

    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan a repo for PRD/implementation workflows.")
    parser.add_argument("root", nargs="?", default=".", help="Repo root (default: .)")
    parser.add_argument("--format", choices=["json", "pretty"], default="pretty")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    data = scan_project(root)

    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

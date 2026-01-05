"""Hatchling build hook to ensure JS assets are built for packaging."""

import os
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class NpmBuildHook(BuildHookInterface):
    """Run the JS build pipeline so packaged artifacts exist."""

    def initialize(self, version: str, build_data: dict[str, object]) -> None:
        if os.getenv("LITESTAR_VITE_SKIP_NPM_BUILD") or os.getenv("LITESTAR_VITE_SKIP_JS_BUILD"):
            return

        root = Path(self.root)
        env = os.environ.copy()
        env.setdefault("NODE_OPTIONS", "--no-deprecation --disable-warning=ExperimentalWarning")

        executor = os.getenv("LITESTAR_VITE_BUILD_EXECUTOR") or os.getenv("LITESTAR_VITE_RUNTIME") or "npm"
        executor = executor.lower()
        if executor == "node":
            executor = "npm"

        node_modules = root / "node_modules"
        if not node_modules.exists():
            install_cmd = _install_command(executor, root)
            subprocess.run(install_cmd, cwd=root, env=env, check=True)

        subprocess.run(_build_command(executor), cwd=root, env=env, check=True)


def _install_command(executor: str, root: Path) -> list[str]:
    if executor == "bun":
        return ["bun", "install"]
    if executor == "pnpm":
        return ["pnpm", "install", "--frozen-lockfile"]
    if executor == "yarn":
        return ["yarn", "install", "--frozen-lockfile"]

    # Default to npm semantics.
    if (root / "package-lock.json").exists():
        return ["npm", "ci", "--no-fund", "--quiet"]
    return ["npm", "install", "--no-fund", "--quiet"]


def _build_command(executor: str) -> list[str]:
    if executor == "pnpm":
        return ["pnpm", "run", "build"]
    if executor == "yarn":
        return ["yarn", "run", "build"]
    if executor == "bun":
        return ["bun", "run", "build"]
    return ["npm", "run", "build", "--quiet"]

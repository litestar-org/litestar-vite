"""File system paths configuration."""

import os
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ("PathConfig",)


@dataclass
class PathConfig:
    """File system and URL path configuration for Vite source, public, and bundle directories."""

    root: "str | Path" = field(default_factory=Path.cwd)
    """Root directory of the frontend project, defaulting to the current working directory."""
    bundle_dir: "str | Path" = field(default_factory=lambda: Path("public"))
    """Output directory for compiled production bundles and `manifest.json`."""
    resource_dir: "str | Path" = field(default_factory=lambda: Path("src"))
    """TypeScript/JavaScript source directory containing entrypoints and components."""
    static_dir: "str | Path" = field(default_factory=lambda: Path("public"))
    """Static public assets directory served as-is by Vite (`publicDir`)."""
    manifest_name: str = "manifest.json"
    """Filename of the Vite build manifest inside `bundle_dir`."""
    hot_file: str = "hot"
    """Filename inside `bundle_dir` storing the active Vite dev server URL."""
    asset_url: str = field(default_factory=lambda: os.getenv("ASSET_URL", "/static/"))
    """Base URL prefix prepended to static and built asset references."""
    ssr_output_dir: "str | Path | None" = None
    """Optional output directory for compiled server-side rendering (SSR) bundles."""

    def __post_init__(self) -> None:
        """Normalize path types to Path objects.

        This also adjusts defaults to prevent Vite's ``publicDir`` (input) from
        colliding with ``outDir`` (output). ``bundle_dir`` is treated as the build
        output directory. When ``static_dir`` equals ``bundle_dir``, Vite may warn
        and effectively disable public asset copying, so ``static_dir`` defaults to
        ``<resource_dir>/public`` in that case.
        """
        if isinstance(self.root, str):
            object.__setattr__(self, "root", Path(self.root))
        if isinstance(self.bundle_dir, str):
            object.__setattr__(self, "bundle_dir", Path(self.bundle_dir))
        if isinstance(self.resource_dir, str):
            object.__setattr__(self, "resource_dir", Path(self.resource_dir))
        if isinstance(self.static_dir, str):
            object.__setattr__(self, "static_dir", Path(self.static_dir))
        if isinstance(self.ssr_output_dir, str):
            object.__setattr__(self, "ssr_output_dir", Path(self.ssr_output_dir))

        if (
            isinstance(self.bundle_dir, Path)
            and isinstance(self.static_dir, Path)
            and self.static_dir == self.bundle_dir
        ):
            object.__setattr__(self, "static_dir", Path(self.resource_dir) / "public")

        asset_url = self.asset_url
        if asset_url and asset_url != "/" and not asset_url.endswith("/"):
            object.__setattr__(self, "asset_url", f"{asset_url}/")


def resolve_ssr_bundle_path(paths: PathConfig) -> Path:
    """Resolve Vite's default SSR entry bundle independently of the worker cwd."""
    output_dir = (
        Path(paths.ssr_output_dir)
        if paths.ssr_output_dir is not None
        else Path(paths.resource_dir) / "bootstrap" / "ssr"
    )
    return (Path(paths.root) / output_dir / "ssr.js").resolve()

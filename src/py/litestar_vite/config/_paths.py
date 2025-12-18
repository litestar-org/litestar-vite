"""File system paths configuration."""

import os
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ("PathConfig",)


@dataclass
class PathConfig:
    """File system paths configuration.

    Attributes:
        root: The root directory of the project. Defaults to current working directory.
        bundle_dir: Location of compiled assets and manifest.json.
        resource_dir: TypeScript/JavaScript source directory (equivalent to ./src in Vue/React).
        static_dir: Static public assets directory (served as-is by Vite).
        manifest_name: Name of the Vite manifest file.
        hot_file: Name of the hot file indicating dev server URL.
        asset_url: Base URL for static asset references (prepended to Vite output).
        ssr_output_dir: SSR output directory (optional).
    """

    root: "str | Path" = field(default_factory=Path.cwd)
    bundle_dir: "str | Path" = field(default_factory=lambda: Path("public"))
    resource_dir: "str | Path" = field(default_factory=lambda: Path("src"))
    static_dir: "str | Path" = field(default_factory=lambda: Path("public"))
    manifest_name: str = "manifest.json"
    hot_file: str = "hot"
    asset_url: str = field(default_factory=lambda: os.getenv("ASSET_URL", "/static/"))
    ssr_output_dir: "str | Path | None" = None

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

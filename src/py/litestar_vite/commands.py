"""Vite commands module.

This module provides utility functions for Vite project initialization.
The main scaffolding functionality has moved to litestar_vite.scaffolding.
"""

from typing import TYPE_CHECKING

from litestar_vite.config import JINJA_INSTALLED
from litestar_vite.exceptions import MissingDependencyError

if TYPE_CHECKING:
    from pathlib import Path


def init_vite(
    root_path: "Path",
    resource_path: "Path",
    asset_url: "str",
    static_path: "Path",
    bundle_path: "Path",
    enable_ssr: "bool",
    vite_port: int,
    litestar_port: int,
    framework: str = "react",
) -> None:
    """Initialize a new Vite project using the scaffolding system.

    Args:
        root_path: Root directory for the Vite project.
        resource_path: Directory containing source files.
        asset_url: Base URL for serving assets.
        static_path: Directory for static (unprocessed) frontend assets.
        bundle_path: Output directory for built files.
        enable_ssr: Enable server-side rendering.
        vite_port: Port for Vite dev server.
        litestar_port: Port for Litestar server.
        framework: Framework template to use (default: react).

    Raises:
        MissingDependencyError: If Jinja2 is not installed.
        ValueError: If the specified framework template is not found.
    """
    if not JINJA_INSTALLED:
        raise MissingDependencyError(package="jinja2", install_package="jinja")

    from litestar_vite.scaffolding import TemplateContext, generate_project
    from litestar_vite.scaffolding.templates import FrameworkType, get_template

    template = get_template(framework)
    if template is None:
        template = get_template(FrameworkType.REACT)
    if template is None:  # pragma: no cover
        msg = f"Could not find template for framework: {framework}"
        raise ValueError(msg)

    context = TemplateContext(
        project_name=root_path.name or "my-project",
        framework=template,
        use_typescript=template.uses_typescript,
        use_tailwind=False,
        vite_port=vite_port,
        litestar_port=litestar_port,
        asset_url=asset_url,
        resource_dir=str(resource_path),
        bundle_dir=str(bundle_path),
        static_dir=str(static_path),
        enable_ssr=enable_ssr,
        enable_inertia=template.inertia_compatible and "inertia" in framework,
        enable_types=True,
    )

    generate_project(root_path, context, overwrite=True)

from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any, MutableMapping

if TYPE_CHECKING:
    from jinja2 import Environment, Template
    from litestar import Litestar

VITE_INIT_TEMPLATES: set[str] = {"package.json.j2", "tsconfig.json.j2", "vite.config.ts.j2"}
DEFAULT_RESOURCES: set[str] = {"styles.css.j2", "main.ts.j2"}
DEFAULT_DEV_DEPENDENCIES: dict[str, str] = {
    "typescript": "^5.7.2",
    "vite": "^6.0.6",
    "litestar-vite-plugin": "^0.12.1",
    "@types/node": "^22.10.2",
}
DEFAULT_DEPENDENCIES: dict[str, str] = {"axios": "^1.7.9"}


def to_json(value: Any) -> str:
    """Serialize JSON field values.

    Args:
        value: Any json serializable value.

    Returns:
        JSON string.
    """
    from litestar.serialization import encode_json

    return encode_json(value).decode("utf-8")


def init_vite(
    app: Litestar,
    root_path: Path,
    resource_path: Path,
    asset_url: str,
    public_path: Path,
    bundle_path: Path,
    enable_ssr: bool,
    vite_port: int,
    hot_file: Path,
    litestar_port: int,
) -> None:
    """Initialize a new Vite project.

    Args:
        app: The Litestar application instance.
        root_path: Root directory for the Vite project.
        resource_path: Directory containing source files.
        asset_url: Base URL for serving assets.
        public_path: Directory for static files.
        bundle_path: Output directory for built files.
        enable_ssr: Enable server-side rendering.
        vite_port: Port for Vite dev server.
        hot_file: Path to hot reload manifest.
        litestar_port: Port for Litestar server.
    """
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from litestar.cli._utils import console
    from litestar.utils import module_loader

    template_path = module_loader.module_to_os_path("litestar_vite.templates")
    vite_template_env = Environment(
        loader=FileSystemLoader([template_path]),
        autoescape=select_autoescape(),
    )

    enabled_templates: set[str] = VITE_INIT_TEMPLATES
    enabled_resources: set[str] = DEFAULT_RESOURCES
    dependencies: dict[str, str] = DEFAULT_DEPENDENCIES
    dev_dependencies: dict[str, str] = DEFAULT_DEV_DEPENDENCIES
    templates: dict[str, Template] = {
        template_name: get_template(environment=vite_template_env, name=template_name)
        for template_name in enabled_templates
    }

    # Prepare root_path
    root_path.mkdir(parents=True, exist_ok=True)
    for template_name, template in templates.items():
        target_file_name = template_name[:-3] if template_name.endswith(".j2") else template_name
        target_file_path = root_path / target_file_name
        with target_file_path.open(mode="w") as file:
            console.print(f" * Writing {target_file_name} to {target_file_path!s}")

            file.write(
                template.render(
                    entry_point=[
                        f"{resource_path!s}/{resource_name[:-3] if resource_name.endswith('.j2') else resource_name}"
                        for resource_name in enabled_resources
                    ],
                    enable_ssr=enable_ssr,
                    asset_url=asset_url,
                    root_path=root_path,
                    resource_path=str(resource_path),
                    public_path=str(public_path),
                    bundle_path=str(bundle_path),
                    hot_file=str(hot_file),
                    vite_port=str(vite_port),
                    litestar_port=litestar_port,
                    dependencies=to_json(dependencies),
                    dev_dependencies=to_json(dev_dependencies),
                ),
            )

    (root_path / bundle_path).mkdir(parents=True, exist_ok=True)
    (root_path / public_path).mkdir(parents=True, exist_ok=True)
    (root_path / resource_path).mkdir(parents=True, exist_ok=True)
    for resource_name in enabled_resources:
        template = get_template(environment=vite_template_env, name=resource_name)
        target_file_name = f"{resource_name[:-3] if resource_name.endswith('.j2') else resource_name}"
        target_file_path = root_path / resource_path / target_file_name
        with target_file_path.open(mode="w") as file:
            console.print(
                f" * Writing {resource_name[:-3] if resource_name.endswith('.j2') else resource_name} to {target_file_path!s}",
            )
            file.write(template.render())
    console.print("[yellow]Vite initialization completed.[/]")


def get_template(
    environment: Environment,
    name: str | Template,
    parent: str | None = None,
    globals: MutableMapping[str, Any] | None = None,  # noqa: A002
) -> Template:
    return environment.get_template(name=name, parent=parent, globals=globals)


def execute_command(command_to_run: list[str], cwd: str | Path | None = None) -> subprocess.CompletedProcess[bytes]:
    """Run Vite in a subprocess."""
    kwargs = {}
    if cwd is not None:
        kwargs["cwd"] = Path(cwd)
    return subprocess.run(command_to_run, check=False, shell=platform.system() == "Windows", **kwargs)  # type: ignore[call-overload]

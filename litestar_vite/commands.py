from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any, MutableMapping

from jinja2 import select_autoescape
from litestar.serialization import encode_json

if TYPE_CHECKING:
    from jinja2 import Environment, Template
    from litestar import Litestar

VITE_INIT_TEMPLATES_PATH = f"{Path(__file__).parent}/templates"
VITE_INIT_TEMPLATES: set[str] = {"package.json.j2", "tsconfig.json.j2", "vite.config.ts.j2"}
DEFAULT_RESOURCES: set[str] = {"styles.css", "main.ts"}
DEFAULT_DEV_DEPENDENCIES: dict[str, str] = {
    "typescript": "^5.3.3",
    "vite": "^5.0.6",
    "litestar-vite-plugin": "^0.3.0",
    "@types/node": "^20.10.3",
}
DEFAULT_DEPENDENCIES: dict[str, str] = {"axios": "^1.6.2"}


def to_json(value: Any) -> str:
    """Serialize JSON field values.

    Args:
        value: Any json serializable value.

    Returns:
        JSON string.
    """
    return encode_json(value).decode("utf-8")


def init_vite(
    app: Litestar,
    root_path: Path,
    resource_path: Path,
    asset_url: str,
    bundle_path: Path,
    enable_ssr: bool,
    vite_port: int,
    hot_file: Path,
    litestar_port: int,
) -> None:
    """Initialize a new vite project."""
    from jinja2 import Environment, FileSystemLoader

    entry_point: list[str] = []
    vite_template_env = Environment(
        loader=FileSystemLoader([VITE_INIT_TEMPLATES_PATH]),
        autoescape=select_autoescape(),
    )

    logger = app.get_logger()
    enabled_templates: set[str] = VITE_INIT_TEMPLATES
    enabled_resources: set[str] = DEFAULT_RESOURCES
    dependencies: dict[str, str] = DEFAULT_DEPENDENCIES
    dev_dependencies: dict[str, str] = DEFAULT_DEV_DEPENDENCIES
    templates: dict[str, Template] = {
        template_name: get_template(environment=vite_template_env, name=template_name)
        for template_name in enabled_templates
    }
    entry_point = [
        str(Path(resource_path / resource_name).relative_to(Path.cwd().absolute()))
        for resource_name in enabled_resources
    ]
    for template_name, template in templates.items():
        target_file_name = template_name.removesuffix(".j2")
        with Path(target_file_name).open(mode="w") as file:
            logger.info("Writing %s", target_file_name)

            file.write(
                template.render(
                    entry_point=entry_point,
                    enable_ssr=enable_ssr,
                    asset_url=asset_url,
                    root_path=str(root_path.relative_to(Path.cwd().absolute())),
                    resource_path=str(resource_path.relative_to(root_path)),
                    bundle_path=str(bundle_path.relative_to(root_path)),
                    hot_file=str(hot_file.relative_to(Path.cwd().absolute())),
                    vite_port=str(vite_port),
                    litestar_port=litestar_port,
                    dependencies=to_json(dependencies),
                    dev_dependencies=to_json(dev_dependencies),
                ),
            )

    for resource_name in enabled_resources:
        with Path(resource_path / resource_name).open(mode="w") as file:
            logger.info("Writing %s", resource_name)


def get_template(
    environment: Environment,
    name: str | Template,
    parent: str | None = None,
    globals: MutableMapping[str, Any] | None = None,  # noqa: A002
) -> Template:
    return environment.get_template(name=name, parent=parent, globals=globals)


def execute_command(command_to_run: list[str]) -> subprocess.CompletedProcess[bytes]:
    """Run Vite in a subprocess."""
    return subprocess.run(command_to_run, check=False)  # noqa: S603

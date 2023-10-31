from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, MutableMapping

if TYPE_CHECKING:
    from jinja2 import Environment, Template
    from litestar import Litestar

VITE_INIT_TEMPLATES_PATH = f"{Path(__file__).parent}/templates/init"
VITE_INIT_TEMPLATES = ("package.json.j2", "tsconfig.json.j2", "vite.config.ts.j2")


def init_vite(
    app: Litestar,
    resource_path: Path,
    bundle_path: Path,
    include_vue: bool,
    include_react: bool,
    vite_port: int,
) -> None:
    """Initialize a new vite project."""
    from jinja2 import Environment, FileSystemLoader

    vite_template_env = Environment(loader=FileSystemLoader(VITE_INIT_TEMPLATES_PATH), autoescape=True)
    templates: dict[str, Template] = {
        template_name: get_template(environment=vite_template_env, name=template_name)
        for template_name in VITE_INIT_TEMPLATES
    }
    logger = app.get_logger()

    for template_name, template in templates.items():
        with Path(template_name.removesuffix(".j2")).open(mode="w") as file:
            logger.info("Writing %s", template_name)

            file.write(
                template.render(
                    {
                        "include_vue": include_vue,
                        "include_react": include_react,
                        "resource_path": resource_path,
                        "static_port": bundle_path,
                        "vite_port": vite_port,
                    },
                )
            )


def get_template(
    environment: Environment,
    name: str | Template,
    parent: str | None = None,
    globals: MutableMapping[str, Any] | None = None,  # noqa: A002
) -> Template:
    return environment.get_template(name=name, parent=parent, globals=globals)


def run_vite(app: Litestar, command: Literal["serve", "build"]) -> None:
    """Run Vite in a subprocess."""
    import anyio

    logger = app.get_logger()
    try:
        anyio.run(_run_vite, app, command)
    except KeyboardInterrupt:
        logger.info("Stopping typescript development services.")
    finally:
        logger.info("Vite Service stopped.")


async def _run_vite(app: Litestar, command: Literal["serve", "build"]) -> None:
    """Run Vite in a subprocess."""
    from anyio import open_process
    from anyio.streams.text import TextReceiveStream

    from litestar_vite.plugin import VitePlugin

    logger = app.get_logger()
    plugin = app.plugins.get(VitePlugin)
    command_to_run = plugin._config.build_command if command == "build" else plugin._config.run_command  # noqa: SLF001
    async with await open_process(command_to_run) as vite_process:
        async for text in TextReceiveStream(vite_process.stdout):  # type: ignore[arg-type]
            logger.info("Vite", message=text.replace("\n", ""))

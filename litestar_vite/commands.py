from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, MutableMapping

from jinja2 import select_autoescape
from litestar.serialization import encode_json

if TYPE_CHECKING:
    from jinja2 import Environment, Template
    from litestar import Litestar

VITE_INIT_TEMPLATES_PATH = f"{Path(__file__).parent}/templates/init"
VITE_INIT_TEMPLATES = ("package.json.j2", "tsconfig.json.j2", "vite.config.ts.j2")
REACT_INIT_TEMPLATES = ("react/App.tsx.j2", "react/main.tsx.j2")
VUE_INIT_TEMPLATES = ("vue/App.vue.j2", "vue/main.ts")
TAILWIND_INIT_TEMPLATES = ("vue/App.vue.j2", "vue/main.ts")
HTMX_INIT_TEMPLATES = ("main.css", "main.js")


DEFAULT_DEV_DEPENDENCIES: dict[str, str] = {"axios": "^1.1.2", "typescript": "^4.9.5", "vite": "^4.0.0"}
DEFAULT_DEPENDENCIES: dict[str, str] = {}
VUE_DEV_DEPENDENCIES: dict[str, str] = {"@vitejs/plugin-vue": "^4.4.0", "vue-tsc": "^1.8.22"}
VUE_DEPENDENCIES: dict[str, str] = {"vue": "^3.3.7"}
REACT_DEV_DEPENDENCIES: dict[str, str] = {"@vitejs/plugin-react": "^4.1.1"}
REACT_DEPENDENCIES: dict[str, str] = {"react": "^18.2.0"}
TAILWIND_DEV_DEPENDENCIES: dict[str, str] = {"autoprefixer": "^10.4.16", "postcss": "^8.4.31", "tailwindcss": "^3.3.5"}
TAILWIND_DEPENDENCIES: dict[str, str] = {}
HTMX_DEV_DEPENDENCIES: dict[str, str] = {}
HTMX_DEPENDENCIES: dict[str, str] = {"htmx.org": "^1.9.6"}


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
    resource_path: Path,
    asset_path: Path,
    asset_url: str,
    bundle_path: Path,
    include_tailwind: bool,
    include_vue: bool,
    include_react: bool,
    include_htmx: bool,
    enable_ssr: bool,
    vite_port: int,
    litestar_port: int,
) -> None:
    """Initialize a new vite project."""
    from jinja2 import Environment, FileSystemLoader

    entry_point = ["resources/styles.css"]
    vite_template_env = Environment(loader=FileSystemLoader(VITE_INIT_TEMPLATES_PATH), autoescape=select_autoescape())
    templates: dict[str, Template] = {
        template_name: get_template(environment=vite_template_env, name=template_name)
        for template_name in VITE_INIT_TEMPLATES
    }
    logger = app.get_logger()
    dependencies: dict[str, str] = DEFAULT_DEPENDENCIES
    dev_dependencies: dict[str, str] = DEFAULT_DEV_DEPENDENCIES
    if include_vue:
        dependencies.update(VUE_DEPENDENCIES)
        dev_dependencies.update(VUE_DEV_DEPENDENCIES)
    if include_react:
        dependencies.update(REACT_DEPENDENCIES)
        dev_dependencies.update(REACT_DEV_DEPENDENCIES)
    if include_tailwind:
        dependencies.update(TAILWIND_DEPENDENCIES)
        dev_dependencies.update(TAILWIND_DEV_DEPENDENCIES)
    if include_htmx:
        dependencies.update(HTMX_DEPENDENCIES)
        dev_dependencies.update(HTMX_DEV_DEPENDENCIES)
    for template_name, template in templates.items():
        target_file_name = template_name.removesuffix(".j2")
        with Path(target_file_name).open(mode="w") as file:
            logger.info("Writing %s", target_file_name)

            file.write(
                template.render(
                    entry_point=entry_point,
                    include_vue=include_vue,
                    include_react=include_react,
                    include_tailwind=include_tailwind,
                    include_htmx=include_htmx,
                    enable_ssr=enable_ssr,
                    asset_url=asset_url,
                    resource_path=str(resource_path.relative_to(Path.cwd())),
                    bundle_path=str(bundle_path.relative_to(Path.cwd())),
                    asset_path=str(asset_path.relative_to(Path.cwd())),
                    vite_port=str(vite_port),
                    litestar_port=litestar_port,
                    dependencies=to_json(dependencies),
                    dev_dependencies=to_json(dev_dependencies),
                ),
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
            logger.info("[Vite]: %s", text.replace("\n", ""))

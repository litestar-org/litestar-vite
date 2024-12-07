import textwrap
from pathlib import Path

from click.testing import CliRunner
from litestar.cli._utils import LitestarGroup

from tests.test_cli.conftest import CreateAppFileFixture


def test_basic_command(runner: CliRunner, create_app_file: CreateAppFileFixture, root_command: LitestarGroup) -> None:
    template_dir = Path(Path(__file__).parent.parent / "templates")
    app_file_content = textwrap.dedent(
        f"""
from __future__ import annotations

from pathlib import Path

from litestar import Controller, Litestar, get
from litestar.response import Template
from litestar.template.config import TemplateConfig
from litestar.contrib.jinja import JinjaTemplateEngine

from litestar_vite import ViteConfig, VitePlugin


class WebController(Controller):
    include_in_schema = False

    @get("/")
    async def index(self) -> Template:
        return Template(template_name="index.html.j2")

template_config = TemplateConfig(engine=JinjaTemplateEngine(directory='{template_dir!s}'))
vite = VitePlugin(config=ViteConfig())

app = Litestar(plugins=[vite], template_config=template_config)
    """,
    )
    app_file = create_app_file("command_test_app.py", content=app_file_content)
    result = runner.invoke(root_command, ["--app", f"{app_file.stem}:app", "assets"])

    assert not result.exception
    assert "Manage Vite Tasks." in result.output


def test_init_command_no_prompt(
    runner: CliRunner,
    create_app_file: CreateAppFileFixture,
    root_command: LitestarGroup,
    tmp_project_dir: Path,
) -> None:
    template_dir = Path(Path(__file__).parent.parent / "templates")
    app_file_content = textwrap.dedent(
        f"""
from __future__ import annotations

from pathlib import Path

from litestar import Controller, Litestar, get
from litestar.response import Template
from litestar.template.config import TemplateConfig
from litestar.contrib.jinja import JinjaTemplateEngine

from litestar_vite import ViteConfig, VitePlugin


class WebController(Controller):
    include_in_schema = False

    @get("/")
    async def index(self) -> Template:
        return Template(template_name="index.html.j2")

template_config = TemplateConfig(engine=JinjaTemplateEngine(directory='{template_dir!s}'))
vite = VitePlugin(config=ViteConfig())

app = Litestar(plugins=[vite], template_config=template_config)
    """,
    )
    app_file = create_app_file("command_test_app.py", content=app_file_content)
    result = runner.invoke(
        root_command,
        [
            "--app-dir",
            f"{app_file.parent!s}",
            "--app",
            f"{app_file.stem}:app",
            "assets",
            "init",
            "--no-prompt",
            "--root-path",
            "web",
        ],
    )

    assert "Initializing Vite" in result.output
    assert Path(Path(tmp_project_dir) / "web" / "vite.config.ts").exists()
    assert Path(Path(tmp_project_dir) / "web" / "package.json").exists()
    assert Path(Path(tmp_project_dir) / "web" / "tsconfig.json").exists()
    assert Path(Path(tmp_project_dir) / "web" / "resources" / "main.ts").exists()
    assert Path(Path(tmp_project_dir) / "web" / "resources" / "styles.css").exists()


def test_init_install_build(
    runner: CliRunner,
    create_app_file: CreateAppFileFixture,
    root_command: LitestarGroup,
    tmp_project_dir: Path,
) -> None:
    app_file_content = textwrap.dedent(
        """
from __future__ import annotations

from litestar import Litestar
from litestar.template.config import TemplateConfig
from litestar.contrib.jinja import JinjaTemplateEngine

from litestar_vite import VitePlugin, ViteConfig

template_config = TemplateConfig(engine=JinjaTemplateEngine(directory='{template_dir!s}'))
vite = VitePlugin(config=ViteConfig())

app = Litestar(plugins=[vite], template_config=template_config)
    """,
    )
    app_file = create_app_file("command_test_app.py", content=app_file_content)
    _ = runner.invoke(root_command, ["--app", f"{app_file.stem}:app", "assets", "init", "--no-prompt"])
    _ = runner.invoke(root_command, ["--app", f"{app_file.stem}:app", "assets", "install"])
    _ = runner.invoke(root_command, ["--app", f"{app_file.stem}:app", "assets", "build"])
    assert Path(app_file.parent / "vite.config.ts").exists()
    assert Path(app_file.parent / "package.json").exists()
    assert Path(app_file.parent / "tsconfig.json").exists()
    assert Path(app_file.parent / "resources" / "main.ts").exists()
    assert Path(app_file.parent / "resources" / "styles.css").exists()

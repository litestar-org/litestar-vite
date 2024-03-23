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

from litestar_vite import ViteConfig, VitePlugin


class WebController(Controller):
    include_in_schema = False

    @get("/")
    async def index(self) -> Template:
        return Template(template_name="index.html.j2")

vite = VitePlugin(config=ViteConfig(template_dir='{template_dir!s}'))

app = Litestar(plugins=[vite])
    """,
    )
    app_file = create_app_file("command_test_app.py", content=app_file_content)
    result = runner.invoke(root_command, ["--app", f"{app_file.stem}:app", "assets"])

    assert not result.exception
    assert "Using Litestar app from env:" in result.output


def test_init_command_noprompt(
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

from litestar_vite import ViteConfig, VitePlugin


class WebController(Controller):
    include_in_schema = False

    @get("/")
    async def index(self) -> Template:
        return Template(template_name="index.html.j2")

vite = VitePlugin(config=ViteConfig(template_dir='{template_dir!s}'))

app = Litestar(plugins=[vite])
    """,
    )
    app_file = create_app_file("command_test_app.py", content=app_file_content)
    result = runner.invoke(root_command, ["--app", f"{app_file.stem}:app", "assets", "init", "--no-prompt"])

    assert "Using Litestar app from env:" in result.output
    assert Path(tmp_project_dir / "vite.config.ts").exists()
    assert Path(tmp_project_dir / "package.json").exists()
    assert Path(tmp_project_dir / "tsconfig.json").exists()
    assert Path(tmp_project_dir / "resources" / "main.ts").exists()
    assert Path(tmp_project_dir / "resources" / "styles.css").exists()

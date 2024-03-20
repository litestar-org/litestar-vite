import textwrap
from pathlib import Path

from click.testing import CliRunner
from litestar.cli._utils import LitestarGroup

from tests.test_cli.conftest import CreateAppFileFixture

template_dir = Path(Path(__file__).parent.parent / "templates")


def test_basic_command(runner: CliRunner, create_app_file: CreateAppFileFixture, root_command: LitestarGroup) -> None:
    app_file_content = textwrap.dedent(
        f"""
from __future__ import annotations

from pathlib import Path

from litestar import Controller, Litestar, get
from litestar.response import Template

from litestar_vite import ViteConfig, VitePlugin


here = Path(__file__).parent

vite = VitePlugin(config=ViteConfig(template_dir='{template_dir!s}'))

app = Litestar(plugins=[vite])
    """,
    )
    app_file = create_app_file("command_test_app.py", content=app_file_content)
    result = runner.invoke(root_command, ["--app", f"{app_file.stem}:app", "assets"])

    assert not result.exception
    assert "Using Litestar app from env:" in result.output

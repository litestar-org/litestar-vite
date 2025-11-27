import textwrap

from click.testing import CliRunner
from litestar.cli._utils import LitestarGroup

from tests.integration.cli.conftest import CreateAppFileFixture


def test_status_command(runner: CliRunner, create_app_file: CreateAppFileFixture, root_command: LitestarGroup) -> None:
    app_file_content = textwrap.dedent(
        """
from __future__ import annotations
from litestar import Litestar
from litestar_vite import VitePlugin, ViteConfig

vite = VitePlugin(config=ViteConfig())
app = Litestar(plugins=[vite])
    """
    )
    app_file = create_app_file("command_test_app.py", content=app_file_content)
    result = runner.invoke(root_command, ["--app", f"{app_file.stem}:app", "assets", "status"])

    assert result.exit_code == 0
    assert "Vite Integration Status" in result.output
    assert "Dev Mode:" in result.output

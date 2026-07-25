"""CLI integration for the backend bind exported to Vite sidecars."""

import textwrap
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from litestar.cli._utils import LitestarGroup  # pyright: ignore[reportPrivateImportUsage]
from litestar.serialization import decode_json

from tests.integration.cli.conftest import CreateAppFileFixture


@pytest.mark.parametrize("server", ["uvicorn", "granian"])
def test_run_command_exports_effective_bind_for_vite(
    server: str,
    runner: CliRunner,
    create_app_file: CreateAppFileFixture,
    root_command: LitestarGroup,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both Litestar run providers expose the same effective bind to Vite."""
    for name in ("APP_URL", "LITESTAR_HOST", "LITESTAR_PORT", "PORT"):
        monkeypatch.delenv(name, raising=False)
    granian_import = "from litestar_granian import GranianPlugin" if server == "granian" else ""
    plugin_list = "[vite, GranianPlugin()]" if server == "granian" else "[vite]"
    app_file = create_app_file(
        f"{server}_run_app.py",
        content=textwrap.dedent(
            f"""
            from pathlib import Path

            from litestar import Litestar
            from litestar_vite import PathConfig, RuntimeConfig, ViteConfig, VitePlugin
            {granian_import}

            vite = VitePlugin(
                config=ViteConfig(
                    paths=PathConfig(root=Path(__file__).parent),
                    runtime=RuntimeConfig(dev_mode=False, start_dev_server=False),
                )
            )
            app = Litestar(plugins={plugin_list})
            """
        ),
    )
    captured: dict[str, Any] = {}

    def capture_bind(*_: object, **__: object) -> None:
        import os

        captured["host"] = os.environ["LITESTAR_HOST"]
        captured["port"] = os.environ["LITESTAR_PORT"]
        captured["app_url"] = os.environ["APP_URL"]
        bridge_path = Path(os.environ["LITESTAR_VITE_CONFIG_PATH"])
        captured["bridge"] = decode_json(bridge_path.read_bytes())

    patch_target = "litestar_granian.cli._GranianSupervisor.run" if server == "granian" else "uvicorn.run"
    with patch(patch_target, side_effect=capture_bind) as run_server:
        result = runner.invoke(
            root_command, ["--app", f"{app_file.stem}:app", "run", "--host", "0.0.0.0", "--port", "9123"]
        )

    assert result.exit_code == 0, result.output
    run_server.assert_called_once()
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == "9123"
    assert captured["app_url"] == "http://localhost:9123"
    assert captured["bridge"]["appUrl"] == "http://localhost:9123"
    assert captured["bridge"]["litestarPort"] == 9123

import sys
import types
from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock

import pytest
from litestar.cli._utils import LitestarEnv

from litestar_vite.config_updater import find_app_file, update_vite_config_in_file


def test_find_app_file_direct_py_file(tmp_path: Path) -> None:
    app_file = tmp_path / "app.py"
    app_file.write_text("from litestar import Litestar\napp = Litestar()\n")
    env = LitestarEnv(app_path="app.py:app", app=MagicMock(), cwd=tmp_path)
    assert find_app_file(env) == app_file


def test_find_app_file_module_path(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    app_file = src_dir / "main.py"
    app_file.write_text("from litestar import Litestar\napp = Litestar()\n")
    env = LitestarEnv(app_path="src.main:app", app=MagicMock(), cwd=tmp_path)
    assert find_app_file(env) == app_file


def test_find_app_file_package_init(tmp_path: Path) -> None:
    pkg_dir = tmp_path / "my_app"
    pkg_dir.mkdir()
    init_file = pkg_dir / "__init__.py"
    init_file.write_text("from litestar import Litestar\napp = Litestar()\n")
    env = LitestarEnv(app_path="my_app:app", app=MagicMock(), cwd=tmp_path)
    assert find_app_file(env) == init_file


def test_find_app_file_non_existent(tmp_path: Path) -> None:
    env = LitestarEnv(app_path="nonexistent.module:app", app=MagicMock(), cwd=tmp_path)
    assert find_app_file(env) is None


def test_update_vite_config_standalone_variable(tmp_path: Path) -> None:
    app_file = tmp_path / "app.py"
    app_file.write_text(
        dedent(
            """\
            from litestar import Litestar
            from litestar_vite import VitePlugin, ViteConfig

            vite_config = ViteConfig()
            app = Litestar(plugins=[VitePlugin(config=vite_config)])
            """
        )
    )

    success = update_vite_config_in_file(
        file_path=app_file, template_name="react", resource_dir="resources", bundle_dir="public", frontend_dir="."
    )
    assert success is True

    content = app_file.read_text()
    assert "from litestar_vite import PathConfig, ViteConfig" in content or "PathConfig" in content
    assert "from pathlib import Path" in content
    assert 'mode="template"' in content
    assert "dev_mode=True" in content
    assert "types=True" in content
    assert 'resource_dir="resources"' in content
    assert 'bundle_dir="public"' in content
    assert "app = Litestar(plugins=[VitePlugin(config=vite_config)])" in content


def test_update_vite_config_inline_plugin(tmp_path: Path) -> None:
    app_file = tmp_path / "app.py"
    app_file.write_text(
        dedent(
            """\
            from litestar import Litestar
            from litestar_vite import VitePlugin, ViteConfig

            app = Litestar(
                plugins=[
                    VitePlugin(
                        config=ViteConfig(
                            dev_mode=False,
                        )
                    )
                ]
            )
            """
        )
    )

    success = update_vite_config_in_file(
        file_path=app_file, template_name="react-router", resource_dir="src", bundle_dir="dist", frontend_dir="frontend"
    )
    assert success is True

    content = app_file.read_text()
    assert 'mode="spa"' in content
    assert 'root=Path(__file__).parent / "frontend"' in content
    assert 'resource_dir="src"' in content
    assert 'bundle_dir="dist"' in content


def test_update_vite_config_tanstack_extra_commands(tmp_path: Path) -> None:
    app_file = tmp_path / "app.py"
    app_file.write_text(
        dedent(
            """\
            from litestar import Litestar
            from litestar_vite import ViteConfig, VitePlugin

            config = ViteConfig()
            """
        )
    )

    success = update_vite_config_in_file(
        file_path=app_file, template_name="react-tanstack", resource_dir="src", bundle_dir="dist"
    )
    assert success is True

    content = app_file.read_text()
    assert "TypeGenConfig" in content
    assert 'extra_commands=[["tsr", "generate"]]' in content


def test_update_vite_config_not_found(tmp_path: Path) -> None:
    app_file = tmp_path / "app.py"
    app_file.write_text("from litestar import Litestar\napp = Litestar()\n")

    success = update_vite_config_in_file(
        file_path=app_file, template_name="react", resource_dir="resources", bundle_dir="public"
    )
    assert success is False


def test_update_vite_config_preserves_future_imports_and_docstring(tmp_path: Path) -> None:
    app_file = tmp_path / "app.py"
    app_file.write_text(
        dedent(
            '''\
            """My application."""

            from __future__ import annotations

            from litestar import Litestar
            from litestar_vite import ViteConfig, VitePlugin

            config = ViteConfig()
            app = Litestar(plugins=[VitePlugin(config=config)])
            '''
        )
    )

    success = update_vite_config_in_file(
        file_path=app_file, template_name="react", resource_dir="resources", bundle_dir="public"
    )
    assert success is True

    content = app_file.read_text()
    compile(content, str(app_file), "exec")
    lines = content.splitlines()
    assert lines[0] == '"""My application."""'
    future_idx = next(i for i, line in enumerate(lines) if line.startswith("from __future__"))
    pathlib_idx = next(i for i, line in enumerate(lines) if line.startswith("from pathlib"))
    assert future_idx < pathlib_idx


def test_update_vite_config_preserves_import_aliases(tmp_path: Path) -> None:
    app_file = tmp_path / "app.py"
    app_file.write_text(
        dedent(
            """\
            from litestar import Litestar
            from litestar_vite import ViteConfig, VitePlugin as Plugin

            config = ViteConfig()
            app = Litestar(plugins=[Plugin(config=config)])
            """
        )
    )

    success = update_vite_config_in_file(
        file_path=app_file, template_name="react", resource_dir="resources", bundle_dir="public"
    )
    assert success is True

    content = app_file.read_text()
    assert "VitePlugin as Plugin" in content
    assert "Plugin(config=config)" in content


def test_update_vite_config_adds_path_import_when_only_import_pathlib(tmp_path: Path) -> None:
    app_file = tmp_path / "app.py"
    app_file.write_text(
        dedent(
            """\
            import pathlib

            from litestar import Litestar
            from litestar_vite import ViteConfig, VitePlugin

            config = ViteConfig()
            app = Litestar(plugins=[VitePlugin(config=config)])
            """
        )
    )

    success = update_vite_config_in_file(
        file_path=app_file, template_name="react", resource_dir="resources", bundle_dir="public"
    )
    assert success is True

    content = app_file.read_text()
    assert "from pathlib import Path" in content


def test_update_vite_config_enable_types_false(tmp_path: Path) -> None:
    app_file = tmp_path / "app.py"
    app_file.write_text(
        dedent(
            """\
            from litestar import Litestar
            from litestar_vite import ViteConfig, VitePlugin

            config = ViteConfig()
            app = Litestar(plugins=[VitePlugin(config=config)])
            """
        )
    )

    success = update_vite_config_in_file(
        file_path=app_file, template_name="react", resource_dir="resources", bundle_dir="public", enable_types=False
    )
    assert success is True

    content = app_file.read_text()
    assert "types=False" in content
    assert "TypeGenConfig" not in content


def test_update_vite_config_tanstack_enable_types_false_omits_typegen(tmp_path: Path) -> None:
    app_file = tmp_path / "app.py"
    app_file.write_text(
        dedent(
            """\
            from litestar import Litestar
            from litestar_vite import ViteConfig, VitePlugin

            config = ViteConfig()
            app = Litestar(plugins=[VitePlugin(config=config)])
            """
        )
    )

    success = update_vite_config_in_file(
        file_path=app_file,
        template_name="react-tanstack",
        resource_dir="resources",
        bundle_dir="public",
        enable_types=False,
    )
    assert success is True

    content = app_file.read_text()
    assert "types=False" in content
    assert "TypeGenConfig" not in content


def test_find_app_file_ignores_module_outside_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = types.ModuleType("outside_app")
    fake_file = tmp_path / ".." / "outside" / "outside_app.py"
    fake_module.__file__ = str(fake_file.resolve())
    monkeypatch.setitem(sys.modules, "outside_app", fake_module)

    env = LitestarEnv(app_path="outside_app:app", app=MagicMock(), cwd=tmp_path)
    assert find_app_file(env) is None

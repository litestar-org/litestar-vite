import inspect
import subprocess
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock, patch

import pytest
from litestar import Litestar
from litestar.cli._utils import LitestarCLIException, LitestarEnv

from litestar_vite.cli import (
    _apply_cli_log_level,
    _build_deploy_config,
    _coerce_option_value,
    _format_command,
    _generate_schema_and_routes,
    _get_package_executor_cmd,
    _invoke_typegen_cli,
    _parse_storage_options,
    _print_recommended_config,
    _prompt_for_options,
    _run_vite_build,
    _select_framework_template,
    export_routes,
    generate_types,
    vite_build,
    vite_deploy,
    vite_doctor,
    vite_init,
    vite_install,
    vite_serve,
    vite_status,
    vite_update,
)
from litestar_vite.config import DeployConfig, ExternalDevServer, PathConfig, RuntimeConfig, TypeGenConfig, ViteConfig
from litestar_vite.exceptions import ViteExecutionError
from litestar_vite.executor import JSExecutor
from litestar_vite.plugin import VitePlugin
from litestar_vite.scaffolding.templates import FrameworkTemplate, FrameworkType


class FakeExecutor(JSExecutor):
    bin_name = "npm"

    def __init__(self, *, fail_update: bool = False, fail_execute: bool = False) -> None:
        super().__init__()
        self.installs: list[Path] = []
        self.updates: list[tuple[Path, bool]] = []
        self.executes: list[tuple[list[str], Path]] = []
        self.fail_update = fail_update
        self.fail_execute = fail_execute

    @property
    def build_command(self) -> list[str]:
        return ["npm", "run", "build"]

    def install(self, cwd: Path) -> None:
        self.installs.append(cwd)

    def update(self, cwd: Path, *, latest: bool = False) -> None:
        if self.fail_update:
            raise ViteExecutionError(["npm", "update"], 1, "boom")
        self.updates.append((cwd, latest))

    def run(self, args: list[str], cwd: Path) -> subprocess.Popen[Any]:
        self.executes.append((args, cwd))
        return cast("subprocess.Popen[Any]", Mock())

    def execute(self, args: list[str], cwd: Path) -> None:
        if self.fail_execute:
            raise ViteExecutionError(args, 1, "boom")
        self.executes.append((args, cwd))


class FakeDeployer:
    def __init__(self, bundle_dir: Path, manifest_name: str, deploy_config: DeployConfig) -> None:
        self.bundle_dir = bundle_dir
        self.manifest_name = manifest_name
        self.deploy_config = deploy_config
        self.remote_path = "s3://bucket/assets"

    def sync(self, *, dry_run: bool, on_progress: Mock | None = None) -> Mock:
        if on_progress:
            on_progress("upload", "app.js")
            on_progress("delete", "old.js")
        return Mock(uploaded=["app.js"], deleted=["old.js"], uploaded_bytes=123, deleted_bytes=45, dry_run=dry_run)


def _make_app(tmp_path: Path, *, dev_mode: bool = True, types: bool = True) -> Litestar:
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "public").mkdir(parents=True, exist_ok=True)

    types_config: TypeGenConfig | None = None
    if types:
        types_config = TypeGenConfig(output=Path("src/generated"))

    config = ViteConfig(
        mode="spa",
        dev_mode=dev_mode,
        paths=PathConfig(root=tmp_path, resource_dir="src", bundle_dir="public", static_dir="public"),
        runtime=RuntimeConfig(dev_mode=dev_mode, proxy_mode="vite", set_environment=True),
        types=types_config,
    )
    plugin = VitePlugin(config=config)
    return Litestar(route_handlers=[], plugins=[plugin])


def _unwrap_command(command: object) -> Callable[..., Any]:
    callback = getattr(command, "callback")
    return cast("Callable[..., Any]", inspect.unwrap(callback))


def test_cli_helpers_format_and_parse() -> None:
    assert _format_command(["npm", "run", "dev"]) == "npm run dev"
    assert _format_command(None) == ""

    assert _coerce_option_value("true") is True
    assert _coerce_option_value("false") is False
    assert _coerce_option_value("42") == 42
    assert _coerce_option_value("3.14") == 3.14
    assert _coerce_option_value("hello") == "hello"

    parsed = _parse_storage_options(("flag=true", "count=2", "ratio=1.5", "name=test"))
    assert parsed == {"flag": True, "count": 2, "ratio": 1.5, "name": "test"}


def test_cli_storage_option_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid storage option"):
        _parse_storage_options(("bad",))


def test_cli_apply_log_level_updates_executor() -> None:
    config = ViteConfig()
    config._executor_instance = FakeExecutor()

    _apply_cli_log_level(config, verbose=True)
    assert config.logging_config.level == "verbose"
    assert config._executor_instance is None

    config._executor_instance = FakeExecutor()
    _apply_cli_log_level(config, quiet=True)
    assert config.logging_config.level == "quiet"
    assert config._executor_instance is None


def test_cli_print_recommended_config(capsys: pytest.CaptureFixture[str]) -> None:
    _print_recommended_config("react", "src", "public")
    output = capsys.readouterr().out
    assert "Recommended ViteConfig" in output
    assert "resource_dir" in output


def test_cli_select_template_with_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    template = FrameworkTemplate(
        name="React", type=FrameworkType.REACT, description="React template", resource_dir="src"
    )
    monkeypatch.setattr("litestar_vite.cli.get_available_templates", lambda: [template])
    monkeypatch.setattr("litestar_vite.cli.Prompt.ask", lambda *args, **kwargs: "react")

    name, selected = _select_framework_template(None, no_prompt=False)
    assert name == "react"
    assert selected.type == FrameworkType.REACT


def test_cli_select_template_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("litestar_vite.cli.get_template", lambda *_: None)
    with pytest.raises(SystemExit):
        _select_framework_template("missing", no_prompt=True)


def test_cli_prompt_for_options_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    template = FrameworkTemplate(
        name="React", type=FrameworkType.REACT, description="React template", resource_dir="src", has_ssr=True
    )
    monkeypatch.setattr("litestar_vite.cli.Confirm.ask", Mock(side_effect=[True, True, True, False, True]))

    enable_ssr, tailwind, enable_types, generate_zod, generate_client = _prompt_for_options(
        template, None, False, False, False, False, False
    )

    assert enable_ssr is True
    assert tailwind is True
    assert enable_types is True
    assert generate_zod is False
    assert generate_client is True


def test_cli_build_deploy_config_errors() -> None:
    config = ViteConfig(deploy=False)
    with pytest.raises(SystemExit, match="Deployment is not configured"):
        _build_deploy_config(config, None, {}, False)

    config = ViteConfig(deploy=DeployConfig(enabled=True, storage_backend=None))
    with pytest.raises(SystemExit, match="Storage backend is required"):
        _build_deploy_config(config, None, {}, False)


def test_cli_build_deploy_config_merges_overrides() -> None:
    deploy = DeployConfig(enabled=True, storage_backend="gcs://bucket", storage_options={"region": "us"})
    config = ViteConfig(deploy=deploy)
    resolved = _build_deploy_config(config, "s3://bucket", {"region": "eu", "token": "abc"}, no_delete=True)

    assert resolved.storage_backend == "s3://bucket"
    assert resolved.storage_options["region"] == "eu"
    assert resolved.storage_options["token"] == "abc"
    assert resolved.delete_orphaned is False


def test_cli_run_vite_build_skips(tmp_path: Path) -> None:
    config = ViteConfig(paths=PathConfig(root=tmp_path))
    _run_vite_build(config, tmp_path, Mock(), no_build=True)


def test_cli_run_vite_build_executes(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    config = app.plugins.get(VitePlugin).config
    fake_executor = FakeExecutor()
    config._executor_instance = fake_executor

    with patch("litestar_vite.cli._generate_schema_and_routes") as generate, patch("litestar_vite.cli.set_environment"):
        _run_vite_build(config, tmp_path, Mock(), no_build=False, app=app)

    assert generate.called
    assert fake_executor.executes


def test_cli_run_vite_build_failure(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    config = app.plugins.get(VitePlugin).config
    fake_executor = FakeExecutor(fail_execute=True)
    config._executor_instance = fake_executor

    with patch("litestar_vite.cli.set_environment"):
        with pytest.raises(SystemExit, match="Build failed"):
            _run_vite_build(config, tmp_path, Mock(), no_build=False, app=app)


def test_cli_generate_schema_and_routes_success(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    config = app.plugins.get(VitePlugin).config
    result = Mock(exported_files=["routes.json"], unchanged_files=["openapi.json"])

    with patch("litestar_vite.codegen.export_integration_assets", return_value=result):
        _generate_schema_and_routes(app, config, Mock())


def test_cli_generate_schema_and_routes_no_types(tmp_path: Path) -> None:
    app = _make_app(tmp_path, types=False)
    config = app.plugins.get(VitePlugin).config
    _generate_schema_and_routes(app, config, Mock())


def test_cli_vite_doctor_check_exits(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    with patch("litestar_vite.cli.ViteDoctor") as doctor_cls:
        doctor_cls.return_value.run.return_value = False
        with pytest.raises(SystemExit):
            _unwrap_command(vite_doctor)(
                app, check=True, fix=False, no_prompt=True, verbose=False, show_config=False, runtime_checks=False
            )


def test_cli_vite_init_callable_ctx(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    env = LitestarEnv(app_path="app:app", app=app, cwd=tmp_path)
    ctx = SimpleNamespace(obj=lambda: env)

    with patch("litestar_vite.cli.generate_project", return_value=[tmp_path / "file.txt"]):
        _unwrap_command(vite_init)(
            ctx,
            template="react",
            vite_port=None,
            enable_ssr=None,
            asset_url=None,
            root_path=tmp_path,
            frontend_dir=".",
            bundle_path=None,
            resource_path=None,
            static_path=None,
            tailwind=False,
            enable_types=False,
            generate_zod=False,
            generate_client=False,
            overwrite=True,
            verbose=False,
            no_prompt=True,
            no_install=True,
        )


def test_cli_vite_init_verbose_sets_debug(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    env = LitestarEnv(app_path="app:app", app=app, cwd=tmp_path)
    ctx = SimpleNamespace(obj=env)

    with patch("litestar_vite.cli.generate_project", return_value=[tmp_path / "file.txt"]):
        _unwrap_command(vite_init)(
            ctx,
            template="react",
            vite_port=None,
            enable_ssr=None,
            asset_url=None,
            root_path=tmp_path,
            frontend_dir=".",
            bundle_path=None,
            resource_path=None,
            static_path=None,
            tailwind=False,
            enable_types=False,
            generate_zod=False,
            generate_client=False,
            overwrite=True,
            verbose=True,
            no_prompt=True,
            no_install=True,
        )

    assert env.app.debug is True


def test_cli_vite_init_existing_files_aborts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = _make_app(tmp_path)
    env = LitestarEnv(app_path="app:app", app=app, cwd=tmp_path)
    ctx = SimpleNamespace(obj=env)

    (tmp_path / "src").mkdir(exist_ok=True)
    monkeypatch.setattr("litestar_vite.cli.Confirm.ask", lambda *args, **kwargs: False)

    with patch("litestar_vite.cli.generate_project", return_value=[]):
        with pytest.raises(SystemExit) as exc:
            _unwrap_command(vite_init)(
                ctx,
                template="react",
                vite_port=None,
                enable_ssr=None,
                asset_url=None,
                root_path=tmp_path,
                frontend_dir=".",
                bundle_path=None,
                resource_path=None,
                static_path=None,
                tailwind=False,
                enable_types=False,
                generate_zod=False,
                generate_client=False,
                overwrite=False,
                verbose=False,
                no_prompt=False,
                no_install=True,
            )

    assert exc.value.code == 2


def test_cli_vite_init_runs_install(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    env = LitestarEnv(app_path="app:app", app=app, cwd=tmp_path)
    ctx = SimpleNamespace(obj=env)
    fake_executor = FakeExecutor()
    app.plugins.get(VitePlugin).config._executor_instance = fake_executor

    with patch("litestar_vite.cli.generate_project", return_value=[tmp_path / "file.txt"]):
        _unwrap_command(vite_init)(
            ctx,
            template="react",
            vite_port=None,
            enable_ssr=None,
            asset_url=None,
            root_path=tmp_path,
            frontend_dir=".",
            bundle_path=None,
            resource_path=None,
            static_path=None,
            tailwind=False,
            enable_types=False,
            generate_zod=False,
            generate_client=False,
            overwrite=True,
            verbose=False,
            no_prompt=True,
            no_install=False,
        )

    assert fake_executor.installs


def test_cli_vite_install_update_build(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    config = app.plugins.get(VitePlugin).config
    fake_executor = FakeExecutor()
    config._executor_instance = fake_executor

    _unwrap_command(vite_install)(app, verbose=False, quiet=False)
    assert fake_executor.installs

    _unwrap_command(vite_update)(app, latest=True, verbose=False, quiet=False)
    assert fake_executor.updates[-1][1] is True

    with patch("litestar_vite.cli._generate_schema_and_routes"), patch("litestar_vite.cli.set_environment"):
        _unwrap_command(vite_build)(app, verbose=False, quiet=False)
    assert fake_executor.executes


def test_cli_vite_update_failure(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    config = app.plugins.get(VitePlugin).config
    config._executor_instance = FakeExecutor(fail_update=True)

    with pytest.raises(SystemExit):
        _unwrap_command(vite_update)(app, latest=False, verbose=False, quiet=False)


def test_cli_vite_build_external_dev_server(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    config = app.plugins.get(VitePlugin).config
    config.runtime.external_dev_server = ExternalDevServer(enabled=True, build_command=["npm", "run", "build:ext"])
    fake_executor = FakeExecutor()
    config._executor_instance = fake_executor

    with patch("litestar_vite.cli._generate_schema_and_routes"), patch("litestar_vite.cli.set_environment"):
        _unwrap_command(vite_build)(app, verbose=False, quiet=False)
    assert any("build:ext" in cmd for cmd, _ in fake_executor.executes)


def test_cli_vite_serve_modes(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    config = app.plugins.get(VitePlugin).config
    fake_executor = FakeExecutor()
    config._executor_instance = fake_executor

    # Production branch with missing serve_command should return early
    _unwrap_command(vite_serve)(app, verbose=False, quiet=False, production=True)

    # Dev HMR branch
    _unwrap_command(vite_serve)(app, verbose=False, quiet=False, production=False)
    assert fake_executor.executes

    # Watch build branch (dev mode without HMR)
    config.runtime.proxy_mode = None
    _unwrap_command(vite_serve)(app, verbose=False, quiet=False, production=False)


def test_cli_vite_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    app = _make_app(tmp_path)
    config = app.plugins.get(VitePlugin).config
    manifest_path = config.candidate_manifest_paths()[0]
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{}")

    response = Mock(status_code=200)
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: response)

    _unwrap_command(vite_status)(app)


def test_cli_export_routes_json_and_ts(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    app.plugins.get(VitePlugin).config
    output_json = tmp_path / "routes.json"
    output_ts = tmp_path / "routes.ts"

    with (
        patch("litestar_vite.cli.generate_routes_json", return_value={"routes": {"home": "/"}}),
        patch("litestar_vite.cli.generate_routes_ts", return_value="export const route = () => ''"),
        patch("litestar_vite.cli.write_if_changed", return_value=True),
    ):
        _unwrap_command(export_routes)(
            app, output=output_json, only=None, exclude=None, include_components=True, typescript=False, verbose=False
        )
        _unwrap_command(export_routes)(
            app, output=output_ts, only="home", exclude=None, include_components=True, typescript=True, verbose=False
        )


def test_cli_get_package_executor_cmd_variants() -> None:
    assert _get_package_executor_cmd("bun", "tool") == ["bunx", "tool"]
    assert _get_package_executor_cmd("deno", "tool") == ["deno", "run", "-A", "npm:tool"]
    assert _get_package_executor_cmd("yarn", "tool") == ["yarn", "dlx", "tool"]
    assert _get_package_executor_cmd("pnpm", "tool") == ["pnpm", "dlx", "tool"]
    assert _get_package_executor_cmd(None, "tool") == ["npx", "tool"]


def test_cli_invoke_typegen_cli_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = ViteConfig(paths=PathConfig(root=tmp_path))
    monkeypatch.setattr("litestar_vite.cli.subprocess.run", Mock(return_value=Mock(returncode=1)))
    with pytest.raises(LitestarCLIException):
        _invoke_typegen_cli(config, verbose=False)


def test_cli_invoke_typegen_cli_missing_executor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = ViteConfig(paths=PathConfig(root=tmp_path))

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError

    monkeypatch.setattr("litestar_vite.cli.subprocess.run", _raise)
    with pytest.raises(LitestarCLIException):
        _invoke_typegen_cli(config, verbose=False)


def test_cli_generate_types_invokes_typegen(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    app.plugins.get(VitePlugin).config
    result = Mock(exported_files=["routes.json"], unchanged_files=[])

    with (
        patch("litestar_vite.cli._invoke_typegen_cli") as invoke,
        patch(
            "litestar_vite.plugin._utils.write_runtime_config_file",
            return_value=(str(tmp_path / ".litestar.json"), True),
        ),
        patch("litestar_vite.codegen.export_integration_assets", return_value=result),
    ):
        _unwrap_command(generate_types)(app, verbose=False)
        invoke.assert_called_once()


def test_cli_generate_types_disabled(tmp_path: Path) -> None:
    app = _make_app(tmp_path, types=False)
    _unwrap_command(generate_types)(app, verbose=False)


def test_cli_vite_deploy_dry_run(tmp_path: Path) -> None:
    deploy_config = DeployConfig(enabled=True, storage_backend="s3://bucket")
    app = _make_app(tmp_path)
    config = app.plugins.get(VitePlugin).config
    config.deploy = deploy_config
    fake_executor = FakeExecutor()
    config._executor_instance = fake_executor

    with (
        patch("litestar_vite.cli._run_vite_build"),
        patch("litestar_vite.cli.ViteDeployer", FakeDeployer),
        patch("litestar_vite.cli.format_bytes", lambda *_: "0B"),
    ):
        _unwrap_command(vite_deploy)(
            app, storage=None, storage_option=(), no_build=True, dry_run=True, no_delete=False, verbose=False
        )

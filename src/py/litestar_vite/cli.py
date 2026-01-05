import contextlib
import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any

from click import Choice, Context, group, option
from click import Path as ClickPath
from litestar.cli._utils import (  # pyright: ignore[reportPrivateImportUsage]
    LitestarCLIException,
    LitestarEnv,
    LitestarGroup,
    console,
)
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from litestar_vite.codegen import encode_deterministic_json, generate_routes_json, generate_routes_ts, write_if_changed
from litestar_vite.config import DeployConfig, ExternalDevServer, LoggingConfig, TypeGenConfig, ViteConfig
from litestar_vite.deploy import ViteDeployer, format_bytes
from litestar_vite.doctor import ViteDoctor
from litestar_vite.exceptions import ViteExecutionError
from litestar_vite.plugin import VitePlugin, set_environment
from litestar_vite.scaffolding import TemplateContext, generate_project, get_available_templates
from litestar_vite.scaffolding.templates import FrameworkType, get_template

if TYPE_CHECKING:
    from litestar import Litestar


FRAMEWORK_CHOICES = [
    "react",
    "react-router",
    "react-tanstack",
    "react-inertia",
    "vue",
    "vue-inertia",
    "svelte",
    "svelte-inertia",
    "sveltekit",
    "nuxt",
    "astro",
    "htmx",
    "angular",
    "angular-cli",
]


def _format_command(command: "list[str] | None") -> str:
    """Join a command list for display.

    Returns:
        Space-joined command string or empty string.
    """
    return " ".join(command or [])


def _apply_cli_log_level(config: ViteConfig, *, verbose: bool = False, quiet: bool = False) -> None:
    """Apply CLI log level overrides to the config.

    Precedence: --quiet > --verbose > config/env

    Args:
        config: The ViteConfig to modify.
        verbose: If True, set log level to "verbose".
        quiet: If True, set log level to "quiet" (takes precedence over verbose).
    """
    if quiet:
        config.logging = LoggingConfig(
            level="quiet",
            show_paths_absolute=config.logging_config.show_paths_absolute,
            suppress_npm_output=config.logging_config.suppress_npm_output,
            suppress_vite_banner=config.logging_config.suppress_vite_banner,
            timestamps=config.logging_config.timestamps,
        )
        config.reset_executor()
    elif verbose:
        config.logging = LoggingConfig(
            level="verbose",
            show_paths_absolute=config.logging_config.show_paths_absolute,
            suppress_npm_output=config.logging_config.suppress_npm_output,
            suppress_vite_banner=config.logging_config.suppress_vite_banner,
            timestamps=config.logging_config.timestamps,
        )
        config.reset_executor()


def _print_recommended_config(template_name: str, resource_dir: str, bundle_dir: str) -> None:
    """Print recommended ViteConfig for the scaffolded template.

    Args:
        template_name: The name of the template that was scaffolded.
        resource_dir: The resource directory used.
        bundle_dir: The bundle directory used.
    """
    spa_templates = {"react-router", "react-tanstack"}
    mode = "spa" if template_name in spa_templates else "template"

    config_snippet = dedent(
        f"""\
        from pathlib import Path
        from litestar_vite import ViteConfig, PathConfig

        vite_config = ViteConfig(
            mode="{mode}",
            dev_mode=True,
            types=True,
            paths=PathConfig(
                root=Path(__file__).parent,
                resource_dir="{resource_dir}",
                bundle_dir="{bundle_dir}",
            ),
        )
        """
    )

    console.print("\n[bold cyan]Recommended ViteConfig:[/]")
    console.print(Panel(config_snippet, title="app.py", border_style="dim"))
    console.print("[dim]Note: set dev_mode=False in production; set types=False to disable TypeScript generation.[/]")


def _coerce_option_value(value: str) -> object:
    """Convert CLI key/value strings into basic Python types.

    Returns:
        Converted value (bool, int, float, or original string).
    """
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if value.isdigit():
        return int(value)
    try:
        return float(value)
    except ValueError:
        return value


def _parse_storage_options(values: tuple[str, ...]) -> dict[str, object]:
    """Parse repeated --storage-option entries into a dictionary.

    Returns:
        Dictionary of parsed storage options.

    Raises:
        ValueError: If an option is not in key=value format.
    """
    options: dict[str, object] = {}
    for item in values:
        if "=" not in item:
            msg = f"Invalid storage option '{item}'. Expected key=value."
            raise ValueError(msg)
        key, raw = item.split("=", 1)
        options[key] = _coerce_option_value(raw)
    return options


def _build_deploy_config(
    base_config: ViteConfig, storage: str | None, storage_options: dict[str, object], no_delete: bool
) -> DeployConfig:
    """Resolve deploy configuration from CLI overrides.

    Returns:
        Resolved DeployConfig with CLI overrides applied.

    Raises:
        SystemExit: If deployment is not configured or storage backend is missing.
    """
    deploy_config = base_config.deploy_config
    if deploy_config is None:
        msg = "Deployment is not configured. Set ViteConfig.deploy to enable."
        raise SystemExit(msg)

    merged_options = {**deploy_config.storage_options, **storage_options}
    deploy_config = deploy_config.with_overrides(
        storage_backend=storage, storage_options=merged_options, delete_orphaned=False if no_delete else None
    )

    if not deploy_config.storage_backend:
        msg = "Storage backend is required (e.g., gcs://bucket/assets)."
        raise SystemExit(msg)

    return deploy_config


def _run_vite_build(
    config: ViteConfig, root_dir: Path, console: Any, no_build: bool, app: "Litestar | None" = None
) -> None:
    """Run Vite build unless skipped.

    If app is provided, exports schema/routes before building.

    Raises:
        SystemExit: If the build fails.
    """
    if no_build:
        console.print("[dim]Skipping Vite build (--no-build).[/]")
        return

    # Export schema/routes if app is provided
    if app is not None:
        _generate_schema_and_routes(app, config, console)

    console.rule("Starting [blue]Vite[/] build process", align="left")
    if config.set_environment:
        set_environment(config=config, asset_url_override=config.asset_url)
    os.environ.setdefault("VITE_BASE_URL", config.base_url or "/")
    try:
        config.executor.execute(config.build_command, cwd=root_dir)
        console.print("[bold green]✓ Build complete[/]")
    except ViteExecutionError as exc:
        msg = f"Build failed: {exc!s}"
        raise SystemExit(msg) from exc


def _generate_schema_and_routes(app: "Litestar", config: ViteConfig, console: Any) -> None:
    """Export OpenAPI schema, routes, and Inertia page props prior to running a build.

    Uses the shared `export_integration_assets` function to guarantee byte-identical
    output between CLI and Plugin.

    Skips generation when type generation is disabled.

    Raises:
        LitestarCLIException: If export fails.
    """
    from litestar_vite.codegen import export_integration_assets

    types_config = config.types
    if not isinstance(types_config, TypeGenConfig):
        return

    console.print("[dim]Preparing OpenAPI schema and routes...[/]")

    try:
        result = export_integration_assets(app, config)

        # Report results with detailed status
        for file in result.exported_files:
            console.print(f"[green]✓ Exported {file}[/] [dim](updated)[/]")
        for file in result.unchanged_files:
            console.print(f"[dim]✓ {file} (unchanged)[/]")

        if not result.exported_files and not result.unchanged_files:
            console.print("[yellow]! No files exported (OpenAPI may not be available)[/]")
    except (OSError, TypeError, ValueError) as exc:
        msg = f"Failed to export type metadata: {exc}"
        raise LitestarCLIException(msg) from exc


@group(cls=LitestarGroup, name="assets")
def vite_group() -> None:
    """Manage Vite Tasks."""


def _select_framework_template(template: "str | None", no_prompt: bool) -> "tuple[str, Any]":
    """Select and validate the framework template.

    Args:
        template: User-provided template name or None.
        no_prompt: Whether to skip interactive prompts.

    Returns:
        Tuple of (template_name, framework_template).

    Notes:
        When ``no_prompt=True`` and no template is provided, defaults to the ``react`` template.
    """
    if template is None and not no_prompt:
        available = get_available_templates()
        console.print("\n[bold]Available framework templates:[/]")
        for i, tmpl in enumerate(available, 1):
            console.print(f"  {i}. [cyan]{tmpl.type.value}[/] - {tmpl.description}")

        template = Prompt.ask(
            "\nSelect a framework template", choices=[t.type.value for t in available], default="react"
        )
    elif template is None:
        template = "react"

    framework = get_template(template)
    if framework is None:
        console.print(f"[red]Unknown template: {template}[/]")
        sys.exit(1)

    return template, framework


def _prompt_for_options(
    framework: "Any",
    enable_ssr: "bool | None",
    tailwind: bool,
    enable_types: bool,
    generate_zod: bool,
    generate_client: bool,
    no_prompt: bool,
) -> "tuple[bool, bool, bool, bool, bool]":
    """Prompt user for optional features if not specified.

    Args:
        framework: The framework template.
        enable_ssr: SSR flag or None.
        tailwind: TailwindCSS flag.
        enable_types: Type generation flag.
        generate_zod: Zod schema generation flag.
        generate_client: API client generation flag.
        no_prompt: Whether to skip prompts.

    Returns:
        Tuple of (enable_ssr, tailwind, enable_types, generate_zod, generate_client).
    """
    if enable_ssr is None:
        enable_ssr = (
            framework.has_ssr if no_prompt else Confirm.ask("Enable server-side rendering?", default=framework.has_ssr)
        )

    if not tailwind and not no_prompt:
        tailwind = Confirm.ask("Add TailwindCSS?", default=False)

    if not enable_types and not no_prompt:
        enable_types = Confirm.ask("Enable TypeScript type generation?", default=True)

    if enable_types:
        if not generate_zod and not no_prompt:
            generate_zod = Confirm.ask("Generate Zod schemas for validation?", default=False)

        if not generate_client and not no_prompt:
            generate_client = Confirm.ask("Generate API client?", default=True)
    else:
        generate_zod = False
        generate_client = False

    return enable_ssr or False, tailwind, enable_types, generate_zod, generate_client


@vite_group.command(name="doctor", help="Diagnose and fix Vite configuration issues.")
@option("--check", is_flag=True, help="Exit with non-zero status if errors are found (for CI).")
@option("--fix", is_flag=True, help="Auto-fix detected issues (with confirmation).")
@option("--no-prompt", is_flag=True, help="Apply fixes without confirmation.")
@option("--verbose", is_flag=True, help="Enable verbose output.")
@option("--show-config", is_flag=True, help="Print .litestar.json and extracted litestar({ ... }) config block.")
@option("--runtime-checks", is_flag=True, help="Run runtime-state checks (Vite reachable / hotfile presence).")
def vite_doctor(
    app: "Litestar", check: bool, fix: bool, no_prompt: bool, verbose: bool, show_config: bool, runtime_checks: bool
) -> None:
    """Diagnose and fix Vite configuration issues."""
    if verbose:
        app.debug = True

    plugin = app.plugins.get(VitePlugin)
    doctor = ViteDoctor(plugin.config, verbose=verbose)

    success = doctor.run(fix=fix, no_prompt=no_prompt, show_config=show_config, runtime_checks=runtime_checks)

    if check and not success:
        sys.exit(1)


@vite_group.command(name="init", help="Initialize vite for your project.")
@option(
    "--template",
    type=Choice(FRAMEWORK_CHOICES, case_sensitive=False),
    help="Frontend framework template to use. Inertia variants available: react-inertia, vue-inertia, svelte-inertia.",
    default=None,
    required=False,
)
@option(
    "--root-path",
    type=ClickPath(dir_okay=True, file_okay=False, path_type=Path),
    help="The path for the initial the Vite application.  This is the equivalent to the top-level folder in a normal Vue or React application..",
    default=None,
    required=False,
)
@option(
    "--frontend-dir",
    type=str,
    help="Optional subdirectory under root to place the generated frontend (e.g., 'web').",
    default=".",
    required=False,
)
@option(
    "--bundle-path",
    type=ClickPath(dir_okay=True, file_okay=False, path_type=Path),
    help="The path for the built Vite assets.  This is the where the output of `npm run build` will write files.",
    default=None,
    required=False,
)
@option(
    "--resource-path",
    type=ClickPath(dir_okay=True, file_okay=False, path_type=Path),
    help="The path to your Javascript/Typescript source and associated assets.  If this were a standalone Vue or React app, this would point to your `src/` folder.",
    default=None,
    required=False,
)
@option(
    "--static-path",
    type=ClickPath(dir_okay=True, file_okay=False, path_type=Path),
    help="The optional path to your static (unprocessed) frontend assets. If this were a standalone Vite app, this would point to your `public/` folder.",
    default=None,
    required=False,
)
@option("--asset-url", type=str, help="Base url to serve assets from.", default=None, required=False)
@option("--vite-port", type=int, help="The port to run the vite server against.", default=None, required=False)
@option(
    "--enable-ssr",
    "enable_ssr",
    flag_value=True,
    default=None,
    required=False,
    show_default=False,
    help="Enable SSR support.",
)
@option(
    "--disable-ssr",
    "enable_ssr",
    flag_value=False,
    default=None,
    required=False,
    show_default=False,
    help="Disable SSR support.",
)
@option(
    "--tailwind", type=bool, help="Add TailwindCSS to the project.", required=False, show_default=False, is_flag=True
)
@option(
    "--enable-types",
    type=bool,
    help="Enable TypeScript type generation from routes.",
    required=False,
    show_default=False,
    is_flag=True,
)
@option(
    "--generate-zod",
    type=bool,
    help="Generate Zod schemas for runtime validation.",
    required=False,
    show_default=False,
    is_flag=True,
)
@option(
    "--generate-client",
    type=bool,
    help="Generate API client from OpenAPI schema.",
    required=False,
    show_default=False,
    is_flag=True,
)
@option("--overwrite", type=bool, help="Overwrite any files in place.", default=False, is_flag=True)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
@option(
    "--no-prompt",
    help="Do not prompt for confirmation and use all defaults for initializing the project.",
    type=bool,
    default=False,
    required=False,
    show_default=True,
    is_flag=True,
)
@option(
    "--no-install",
    help="Do not execute the installation commands after generating templates.",
    type=bool,
    default=False,
    required=False,
    show_default=True,
    is_flag=True,
)
def vite_init(
    ctx: "Context",
    template: "str | None",
    vite_port: "int | None",
    enable_ssr: "bool | None",
    asset_url: "str | None",
    root_path: "Path | None",
    frontend_dir: str,
    bundle_path: "Path | None",
    resource_path: "Path | None",
    static_path: "Path | None",
    tailwind: "bool",
    enable_types: "bool",
    generate_zod: "bool",
    generate_client: "bool",
    overwrite: "bool",
    verbose: "bool",
    no_prompt: "bool",
    no_install: "bool",
) -> None:
    """Initialize a new Vite project with framework templates."""
    if callable(ctx.obj):
        ctx.obj = ctx.obj()
    elif verbose:
        ctx.obj.app.debug = True
    env: LitestarEnv = ctx.obj
    plugin = env.app.plugins.get(VitePlugin)
    config = plugin._config  # pyright: ignore[reportPrivateUsage]

    console.rule("Initializing [blue]Vite[/]", align="left")

    root_path = Path(root_path or config.root_dir or Path.cwd())
    frontend_dir = frontend_dir or "."
    asset_url = asset_url or config.asset_url
    vite_port = vite_port or config.port
    litestar_port = env.port or 8000
    template, framework = _select_framework_template(template, no_prompt)
    console.print(f"\n[green]Using {framework.name} template[/]")
    resource_path_str = str(resource_path or framework.resource_dir or config.resource_dir)
    bundle_path_str = str(bundle_path or config.bundle_dir)
    static_path_str = str(static_path or config.static_dir)

    if (
        any((root_path / p).exists() for p in [resource_path_str, bundle_path_str, static_path_str])
        and not any([overwrite, no_prompt])
        and not Confirm.ask("Files were found in the paths specified. Are you sure you wish to overwrite the contents?")
    ):
        console.print("Skipping Vite initialization")
        sys.exit(2)

    enable_ssr, tailwind, enable_types, generate_zod, generate_client = _prompt_for_options(
        framework, enable_ssr, tailwind, enable_types, generate_zod, generate_client, no_prompt
    )

    project_name = root_path.name or "my-project"
    is_inertia = framework.type in {
        FrameworkType.REACT_INERTIA,
        FrameworkType.VUE_INERTIA,
        FrameworkType.SVELTE_INERTIA,
    }
    context = TemplateContext(
        project_name=project_name,
        framework=framework,
        use_typescript=framework.uses_typescript,
        use_tailwind=tailwind,
        vite_port=vite_port,
        litestar_port=litestar_port,
        asset_url=asset_url,
        resource_dir=resource_path_str,
        bundle_dir=bundle_path_str,
        static_dir=static_path_str,
        base_dir=frontend_dir,
        enable_ssr=enable_ssr,
        enable_inertia=is_inertia,
        enable_types=enable_types,
        generate_zod=generate_zod,
        generate_client=generate_client,
    )

    console.print("\n[yellow]Generating project files...[/]")
    generated = generate_project(root_path, context, overwrite=overwrite)
    console.print(f"\n[green]Generated {len(generated)} files[/]")

    if not no_install:
        console.rule("Starting [blue]Vite[/] package installation", align="left")
        config.executor.install(root_path)

    console.print("\n[bold green]Vite initialization complete![/]")

    _print_recommended_config(template, context.resource_dir, context.bundle_dir)

    next_steps_cmd = _format_command(config.run_command)
    console.print(f"\n[dim]Next steps:\n  cd {root_path}\n  {next_steps_cmd}[/]")


@vite_group.command(name="install", help="Install frontend packages.")
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
@option("--quiet", type=bool, help="Suppress non-essential output.", default=False, is_flag=True)
def vite_install(app: "Litestar", verbose: "bool", quiet: "bool") -> None:
    """Install frontend packages."""
    if verbose:
        app.debug = True

    plugin = app.plugins.get(VitePlugin)

    _apply_cli_log_level(plugin.config, verbose=verbose, quiet=quiet)

    if not quiet:
        console.rule("Starting [blue]Vite[/] package installation", align="left")

    if plugin.config.executor:
        root_dir = Path(plugin.config.root_dir or Path.cwd())
        plugin.config.executor.install(root_dir)
    else:
        console.print("[red]Executor not configured.[/]")


@vite_group.command(name="update", help="Update frontend packages.")
@option(
    "--latest", type=bool, help="Update to latest versions (ignoring semver constraints).", default=False, is_flag=True
)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
@option("--quiet", type=bool, help="Suppress non-essential output.", default=False, is_flag=True)
def vite_update(app: "Litestar", latest: "bool", verbose: "bool", quiet: "bool") -> None:
    """Update frontend packages.

    By default, updates packages within their semver constraints defined in package.json.
    Use --latest to update to the newest versions available.

    Raises:
        SystemExit: If the update fails.
    """
    if verbose:
        app.debug = True

    plugin = app.plugins.get(VitePlugin)

    _apply_cli_log_level(plugin.config, verbose=verbose, quiet=quiet)

    if not quiet:
        if latest:
            console.rule("Updating [blue]Vite[/] packages to latest versions", align="left")
        else:
            console.rule("Updating [blue]Vite[/] packages", align="left")

    if plugin.config.executor:
        root_dir = Path(plugin.config.root_dir or Path.cwd())
        try:
            plugin.config.executor.update(root_dir, latest=latest)
            console.print("[bold green]✓ Packages updated[/]")
        except ViteExecutionError as e:
            console.print(f"[red]Package update failed: {e!s}[/]")
            raise SystemExit(1) from None
    else:
        console.print("[red]Executor not configured.[/]")


@vite_group.command(name="build", help="Building frontend assets with Vite.")
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
@option("--quiet", type=bool, help="Suppress non-essential output.", default=False, is_flag=True)
def vite_build(app: "Litestar", verbose: "bool", quiet: "bool") -> None:
    """Run vite build.

    Raises:
        SystemExit: If the build fails.
    """
    if verbose:
        app.debug = True

    plugin = app.plugins.get(VitePlugin)

    _apply_cli_log_level(plugin.config, verbose=verbose, quiet=quiet)

    if not quiet:
        console.rule("Starting [blue]Vite[/] build process", align="left")
    _generate_schema_and_routes(app, plugin.config, console)
    if plugin.config.set_environment:
        set_environment(config=plugin.config)

    executor = plugin.config.executor
    try:
        root_dir = plugin.config.root_dir or Path.cwd()
        if not (Path(root_dir) / "node_modules").exists():
            console.print("[dim]Installing frontend dependencies (node_modules missing)...[/]")
            executor.install(Path(root_dir))
        ext = plugin.config.runtime.external_dev_server
        if isinstance(ext, ExternalDevServer) and ext.enabled:
            build_cmd = ext.build_command or executor.build_command
            console.print(f"[dim]Running external build: {' '.join(build_cmd)}[/]")
            executor.execute(build_cmd, cwd=root_dir)
        else:
            executor.execute(plugin.config.build_command, cwd=root_dir)
        console.print("[bold green]✓ Assets built[/]")
    except ViteExecutionError as e:
        console.print(f"[red]Vite build failed: {e!s}[/]")
        raise SystemExit(1) from None


@vite_group.command(name="deploy", help="Build and deploy Vite assets to remote storage via fsspec.")
@option("--storage", type=str, help="Override storage backend URL (e.g., gcs://bucket/assets).")
@option(
    "--storage-option",
    type=str,
    multiple=True,
    help="Storage option key=value forwarded to fsspec (repeat for multiple).",
)
@option("--no-build", is_flag=True, help="Deploy existing build without running Vite build.")
@option("--dry-run", is_flag=True, help="Preview upload/delete plan without making changes.")
@option("--no-delete", is_flag=True, help="Do not delete orphaned remote files.")
@option(
    "--verbose",
    is_flag=True,
    help="Enable verbose output. Install providers separately: gcsfs for gcs://, s3fs for s3://, adlfs for abfs://.",
)
def vite_deploy(
    app: "Litestar",
    storage: "str | None",
    storage_option: "tuple[str, ...]",
    no_build: bool,
    dry_run: bool,
    no_delete: bool,
    verbose: bool,
) -> None:
    """Build and deploy assets to CDN-backed storage."""
    if verbose:
        app.debug = True

    plugin = app.plugins.get(VitePlugin)
    config = plugin.config

    try:
        storage_options = _parse_storage_options(storage_option)
        deploy_config = _build_deploy_config(config, storage, storage_options, no_delete)
    except ValueError as exc:  # pragma: no cover - CLI validation path
        console.print(f"[red]{exc}[/]")
        sys.exit(1)
    except SystemExit as exc:
        console.print(f"[red]{exc}[/]")
        sys.exit(1)

    root_dir = Path(config.root_dir or Path.cwd())
    bundle_dir = config.bundle_dir

    try:
        _run_vite_build(config, root_dir, console, no_build, app=app)
    except SystemExit as exc:
        console.print(f"[red]{exc}[/]")
        sys.exit(1)

    console.rule("Deploying [blue]Vite[/] assets", align="left")
    console.print(f"Storage: {deploy_config.storage_backend}")
    console.print(f"Delete orphaned: {deploy_config.delete_orphaned}")
    if dry_run:
        console.print("[dim]Dry-run enabled. No changes will be made.[/]")

    try:
        deployer = ViteDeployer(bundle_dir=bundle_dir, manifest_name=config.manifest_name, deploy_config=deploy_config)
    except ImportError as exc:  # pragma: no cover - backend import errors
        console.print(f"[red]Missing backend dependency: {exc}[/]")
        console.print("Install provider package, e.g., `pip install gcsfs` for gcs:// URLs.")
        sys.exit(1)
    except ValueError as exc:
        console.print(f"[red]{exc}[/]")
        sys.exit(1)

    def _on_progress(action: str, path: str) -> None:
        symbol = "+" if action == "upload" else "-"
        console.print(f"  {symbol} {path}")

    result = deployer.sync(dry_run=dry_run, on_progress=_on_progress)

    console.rule("[yellow]Deploy summary[/]", align="left")
    console.print(f"Uploaded: {len(result.uploaded)} files ({format_bytes(result.uploaded_bytes)})")
    console.print(f"Deleted:  {len(result.deleted)} files ({format_bytes(result.deleted_bytes)})")
    console.print(f"Remote:   {deployer.remote_path}")
    if result.dry_run:
        console.print("[dim]No changes applied (dry-run).[/]")
    else:
        console.print("[bold green]✓ Deploy complete[/]")


@vite_group.command(
    name="serve",
    help="Serve frontend assets. For meta-frameworks (mode='framework'; aliases: 'ssr'/'ssg'), runs production Node server. Otherwise runs Vite dev server.",
)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
@option("--quiet", type=bool, help="Suppress non-essential output.", default=False, is_flag=True)
@option("--production", type=bool, help="Force production mode (run serve_command).", default=False, is_flag=True)  # pyright: ignore
def vite_serve(app: "Litestar", verbose: "bool", quiet: "bool", production: "bool") -> None:
    """Run frontend server.

    In dev mode (default): Runs the dev server (npm run dev) for all frameworks.
    In production mode (--production or dev_mode=False): Runs the production
    server (npm run serve) for SSR frameworks.

    Use --production to force running the production server (serve_command).
    """
    if verbose:
        app.debug = True

    plugin = app.plugins.get(VitePlugin)

    _apply_cli_log_level(plugin.config, verbose=verbose, quiet=quiet)
    if plugin.config.set_environment:
        set_environment(config=plugin.config)

    use_production_server = production or not plugin.config.dev_mode

    if use_production_server:
        console.rule("Starting [blue]Vite[/] server", align="left")
        command_to_run = plugin.config.serve_command
        if command_to_run is None:
            console.print("[red]serve_command not configured. Add 'serve' script to package.json.[/]")
            return
    elif plugin.config.hot_reload:
        console.rule("Starting [blue]Vite[/] server with HMR", align="left")
        command_to_run = plugin.config.run_command
    else:
        console.rule("Starting [blue]Vite[/] watch and build process", align="left")
        command_to_run = plugin.config.build_watch_command

    if plugin.config.executor:
        try:
            root_dir = plugin.config.root_dir or Path.cwd()
            plugin.config.executor.execute(command_to_run, cwd=root_dir)
            console.print("[yellow]Vite process stopped.[/]")
        except ViteExecutionError as e:
            console.print(f"[red]Vite process failed: {e!s}[/]")
    else:
        console.print("[red]Executor not configured.[/]")


@vite_group.command(name="export-routes", help="Export route metadata for type-safe routing.")
@option(
    "--output",
    help="Output file path",
    type=ClickPath(dir_okay=False, path_type=Path),
    default=None,
    show_default=False,
)
@option("--only", help="Only include routes matching these patterns (comma-separated)", type=str, default=None)
@option("--except", "exclude", help="Exclude routes matching these patterns (comma-separated)", type=str, default=None)
@option("--include-components", help="Include Inertia component names", type=bool, default=True, is_flag=True)
@option(
    "--typescript",
    "--ts",
    "typescript",
    help="Generate typed routes.ts file (Ziggy-style) instead of JSON",
    type=bool,
    default=False,
    is_flag=True,
)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def export_routes(
    app: "Litestar",
    output: "Path | None",
    only: "str | None",
    exclude: "str | None",
    include_components: "bool",
    typescript: "bool",
    verbose: "bool",
) -> None:
    """Export route metadata for type-safe routing.

    Args:
        app: The Litestar application instance.
        output: The path to the output file. Uses TypeGenConfig if not provided.
        only: Comma-separated list of route patterns to include.
        exclude: Comma-separated list of route patterns to exclude.
        include_components: Include Inertia component names in output.
        typescript: Generate typed routes.ts file instead of JSON.
        verbose: Whether to enable verbose output.

    Raises:
        LitestarCLIException: If the output file cannot be written.
    """
    if verbose:
        app.debug = True

    plugin = app.plugins.get(VitePlugin)
    config = plugin.config

    only_list = [p.strip() for p in only.split(",")] if only else None
    exclude_list = [p.strip() for p in exclude.split(",")] if exclude else None

    if typescript:
        if output is None:
            if isinstance(config.types, TypeGenConfig) and config.types.routes_ts_path:
                output = config.types.routes_ts_path
            else:
                output = Path("routes.ts")

        console.rule(f"[yellow]Exporting typed routes to {output}[/]", align="left")

        global_route = bool(isinstance(config.types, TypeGenConfig) and config.types.global_route)
        routes_ts_content = generate_routes_ts(app, only=only_list, exclude=exclude_list, global_route=global_route)

        try:
            changed = write_if_changed(output, routes_ts_content)
            status = "updated" if changed else "unchanged"
            console.print(f"[green]✓ Typed routes exported to {output}[/] [dim]({status})[/]")
        except OSError as e:  # pragma: no cover
            msg = f"Failed to write routes to path {output}"
            raise LitestarCLIException(msg) from e
    else:
        if output is None:
            if isinstance(config.types, TypeGenConfig) and config.types.routes_path is not None:
                output = config.types.routes_path
            elif isinstance(config.types, TypeGenConfig):
                output = config.types.output / "routes.json"
            else:
                output = Path("routes.json")

        console.rule(f"[yellow]Exporting routes to {output}[/]", align="left")

        routes_data = generate_routes_json(
            app, only=only_list, exclude=exclude_list, include_components=include_components
        )

        try:
            content = encode_deterministic_json(routes_data)
            changed = write_if_changed(output, content)
            status = "updated" if changed else "unchanged"
            console.print(f"[green]✓ Routes exported to {output}[/] [dim]({status})[/]")
            console.print(f"[dim]  {len(routes_data.get('routes', {}))} routes exported[/]")
        except OSError as e:  # pragma: no cover
            msg = f"Failed to write routes to path {output}"
            raise LitestarCLIException(msg) from e


def _get_package_executor_cmd(executor: "str | None", package: str) -> "list[str]":
    """Build package executor command list.

    Maps executor to its "npx equivalent" and returns a command list
    suitable for subprocess.run.

    Args:
        executor: The JS runtime executor (node, bun, deno, yarn, pnpm).
        package: The package to run.

    Returns:
        Command list for subprocess.run.
    """
    match executor:
        case "bun":
            return ["bunx", package]
        case "deno":
            return ["deno", "run", "-A", f"npm:{package}"]
        case "yarn":
            return ["yarn", "dlx", package]
        case "pnpm":
            return ["pnpm", "dlx", package]
        case _:
            return ["npx", package]


def _invoke_typegen_cli(config: Any, verbose: bool) -> None:
    """Invoke the unified TypeScript type generation CLI.

    This is the single entry point for TypeScript type generation, used by
    `litestar assets generate-types`. It calls `litestar-vite-typegen` which
    handles both @hey-api/openapi-ts and page-props.ts generation.

    Args:
        config: The ViteConfig instance (with .types resolved).
        verbose: Whether to show verbose output.

    Raises:
        LitestarCLIException: If type generation fails.
    """
    root_dir = config.root_dir or Path.cwd()
    executor = config.runtime.executor

    # Build the command to run the unified TypeScript CLI
    pkg_cmd = _get_package_executor_cmd(executor, "litestar-vite-typegen")
    cmd = [*pkg_cmd]

    if verbose:
        cmd.append("--verbose")

    try:
        # Run the CLI, letting stdout/stderr pass through to the terminal
        result = subprocess.run(cmd, cwd=root_dir, check=False)
        if result.returncode != 0:
            msg = "TypeScript type generation failed"
            raise LitestarCLIException(msg)
    except FileNotFoundError:
        runtime_name = executor or "Node.js"
        console.print(
            f"[yellow]! litestar-vite-typegen not found - ensure {runtime_name} and litestar-vite-plugin are installed[/]"
        )
        msg = f"Package executor not found - ensure {runtime_name} is installed"
        raise LitestarCLIException(msg) from None


@vite_group.command(name="generate-types", help="Generate TypeScript types from OpenAPI schema and routes.")
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def generate_types(app: "Litestar", verbose: "bool") -> None:
    """Generate TypeScript types from OpenAPI schema and routes.

    Uses the unified TypeScript CLI (litestar-vite-typegen) to ensure
    identical output between CLI, dev server, and build commands.

    This command:
    1. Exports OpenAPI schema, routes, and page props metadata
    2. Invokes the unified TypeScript CLI which handles:
       - @hey-api/openapi-ts for API types
       - page-props.ts for Inertia page props (if enabled)

    Args:
        app: The Litestar application instance.
        verbose: Whether to enable verbose output.
    """
    from litestar_vite.codegen import export_integration_assets
    from litestar_vite.plugin._utils import write_runtime_config_file

    if verbose:
        app.debug = True

    plugin = app.plugins.get(VitePlugin)
    config = plugin.config

    if not isinstance(config.types, TypeGenConfig):
        console.print("[yellow]Type generation is not enabled in ViteConfig[/]")
        console.print("[dim]Set types=True or types=TypeGenConfig() in ViteConfig[/]")
        return

    console.rule("Generating [blue]TypeScript[/] types", align="left")

    config_path, config_changed = write_runtime_config_file(config, return_status=True)
    config_display = Path(config_path)
    with contextlib.suppress(ValueError):
        config_display = config_display.relative_to(Path.cwd())
    if config_changed:
        console.print(f"[green]✓ Exported {config_display}[/] [dim](updated)[/]")
    else:
        console.print(f"[dim]✓ {config_display} (unchanged)[/]")

    # Export all integration assets using the shared function
    try:
        result = export_integration_assets(app, config)

        # Report results with detailed status
        for file in result.exported_files:
            console.print(f"[green]✓ Exported {file}[/] [dim](updated)[/]")
        for file in result.unchanged_files:
            console.print(f"[dim]✓ {file} (unchanged)[/]")

        if not result.exported_files and not result.unchanged_files:
            console.print("[yellow]! No files exported (OpenAPI may not be available)[/]")
            return
    except (OSError, TypeError, ValueError) as exc:
        console.print(f"[red]✗ Failed to export type metadata: {exc}[/]")
        return

    # Invoke the unified TypeScript type generation CLI
    # This handles both @hey-api/openapi-ts and page-props.ts generation
    _invoke_typegen_cli(config, verbose)


@vite_group.command(name="status", help="Check the status of the Vite integration.")
def vite_status(app: "Litestar") -> None:
    """Check the status of the Vite integration."""
    import httpx

    plugin = app.plugins.get(VitePlugin)
    config = plugin.config

    console.rule("[blue]Vite[/] Integration Status", align="left")
    console.print(f"Dev Mode: {config.dev_mode}")
    console.print(f"Hot Reload: {config.hot_reload}")
    console.print(f"Assets URL: {config.asset_url}")
    console.print(f"Base URL: {config.base_url}")

    manifest_candidates = config.candidate_manifest_paths()
    found_manifest = next((path for path in manifest_candidates if path.exists()), None)
    if found_manifest is not None:
        console.print(f"[green]✓ Manifest found at {found_manifest}[/]")
    else:
        manifest_locations = " or ".join(str(path) for path in manifest_candidates)
        console.print(f"[red]✗ Manifest not found at {manifest_locations}[/]")

    if config.dev_mode:
        url = f"{config.protocol}://{config.host}:{config.port}"
        try:
            response = httpx.get(url, timeout=0.5)
            if response.status_code == 200:
                console.print(f"[green]✓ Vite server running at {url}[/]")
            else:
                console.print(f"[yellow]! Vite server reachable at {url} but returned {response.status_code}[/]")
        except httpx.HTTPError as e:
            console.print(f"[red]✗ Vite server not reachable at {url}: {e!s}[/]")

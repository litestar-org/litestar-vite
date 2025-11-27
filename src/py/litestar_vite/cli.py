from pathlib import Path
from typing import TYPE_CHECKING, Optional

from click import Context, group, option
from click import Path as ClickPath
from litestar.cli._utils import LitestarEnv, LitestarGroup  # pyright: ignore[reportPrivateImportUsage]

if TYPE_CHECKING:
    from litestar import Litestar


@group(cls=LitestarGroup, name="assets")
def vite_group() -> None:
    """Manage Vite Tasks."""


@vite_group.command(
    name="init",
    help="Initialize vite for your project.",
)
@option(
    "--root-path",
    type=ClickPath(dir_okay=True, file_okay=False, path_type=Path),
    help="The path for the initial the Vite application.  This is the equivalent to the top-level folder in a normal Vue or React application..",
    default=None,
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
    "--public-path",
    type=ClickPath(dir_okay=True, file_okay=False, path_type=Path),
    help="The optional path to your public/static JS assets.  If this were a standalone Vue or React app, this would point to your `public/` folder.",
    default=None,
    required=False,
)
@option("--asset-url", type=str, help="Base url to serve assets from.", default=None, required=False)
@option(
    "--vite-port",
    type=int,
    help="The port to run the vite server against.",
    default=None,
    is_flag=True,
    required=False,
)
@option(
    "--enable-ssr",
    type=bool,
    help="Enable SSR Support.",
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
    vite_port: "Optional[int]",
    enable_ssr: "Optional[bool]",
    asset_url: "Optional[str]",
    root_path: "Optional[Path]",
    bundle_path: "Optional[Path]",
    resource_path: "Optional[Path]",
    public_path: "Optional[Path]",
    overwrite: "bool",
    verbose: "bool",
    no_prompt: "bool",
    no_install: "bool",
) -> None:  # sourcery skip: low-code-quality
    """Run vite build."""
    import sys
    from pathlib import Path

    from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]
    from rich.prompt import Confirm

    from litestar_vite import VitePlugin
    from litestar_vite.commands import init_vite

    if callable(ctx.obj):
        ctx.obj = ctx.obj()
    elif verbose:
        ctx.obj.app.debug = True
    env: LitestarEnv = ctx.obj
    plugin = env.app.plugins.get(VitePlugin)
    config = plugin._config  # pyright: ignore[reportPrivateUsage]

    console.rule("[yellow]Initializing Vite[/]", align="left")
    root_path = Path(root_path or config.root_dir or Path.cwd())
    resource_path = Path(resource_path or config.resource_dir)
    public_path = Path(public_path or config.public_dir)
    bundle_path = Path(bundle_path or config.bundle_dir)
    enable_ssr = enable_ssr or config.ssr_enabled
    asset_url = asset_url or config.asset_url
    vite_port = vite_port or config.port
    hot_file = Path(bundle_path / config.hot_file)

    if any(output_path.exists() for output_path in (bundle_path, resource_path)) and not any(
        [overwrite, no_prompt],
    ):
        confirm_overwrite = Confirm.ask(
            "Files were found in the paths specified.  Are you sure you wish to overwrite the contents?",
        )
        if not confirm_overwrite:
            console.print("Skipping Vite initialization")
            sys.exit(2)

    enable_ssr = (
        True
        if enable_ssr
        else False
        if no_prompt
        else Confirm.ask(
            "Do you intend to use Litestar with any SSR framework?",
        )
    )
    init_vite(
        app=env.app,
        root_path=root_path,
        enable_ssr=enable_ssr,
        vite_port=vite_port,
        asset_url=asset_url,
        resource_path=resource_path,
        public_path=public_path,
        bundle_path=bundle_path,
        hot_file=hot_file,
        litestar_port=env.port or 8000,
    )
    if not no_install:
        if config.executor is None:
            console.print("[red]Executor not configured.[/]")
            return

        console.rule("[yellow]Starting package installation process[/]", align="left")
        config.executor.install(root_path)


@vite_group.command(
    name="install",
    help="Install frontend packages.",
)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def vite_install(app: "Litestar", verbose: "bool") -> None:
    """Run vite build."""
    from pathlib import Path

    from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]

    from litestar_vite.plugin import VitePlugin

    if verbose:
        app.debug = True
    plugin = app.plugins.get(VitePlugin)

    console.rule("[yellow]Starting package installation process[/]", align="left")

    if plugin.config.executor:
        root_dir = Path(plugin.config.root_dir or Path.cwd())
        plugin.config.executor.install(root_dir)
    else:
        console.print("[red]Executor not configured.[/]")


@vite_group.command(
    name="build",
    help="Building frontend assets with Vite.",
)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def vite_build(app: "Litestar", verbose: "bool") -> None:
    """Run vite build."""
    from pathlib import Path

    from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]

    from litestar_vite.exceptions import ViteExecutionError
    from litestar_vite.plugin import VitePlugin, set_environment

    if verbose:
        app.debug = True
    console.rule("[yellow]Starting Vite build process[/]", align="left")
    plugin = app.plugins.get(VitePlugin)
    if plugin.config.set_environment:
        set_environment(config=plugin.config)

    if plugin.config.executor:
        try:
            root_dir = Path(plugin.config.root_dir or Path.cwd())
            plugin.config.executor.execute(plugin.config.build_command, cwd=root_dir)
            console.print("[bold green] Assets built.[/]")
        except ViteExecutionError as e:
            console.print(f"[bold red] There was an error building the assets: {e!s}[/]")
    else:
        console.print("[red]Executor not configured.[/]")


@vite_group.command(
    name="serve",
    help="Serving frontend assets with Vite.",
)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def vite_serve(app: "Litestar", verbose: "bool") -> None:
    """Run vite serve."""
    from pathlib import Path

    from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]

    from litestar_vite.exceptions import ViteExecutionError
    from litestar_vite.plugin import VitePlugin, set_environment

    if verbose:
        app.debug = True

    plugin = app.plugins.get(VitePlugin)
    if plugin.config.set_environment:
        set_environment(config=plugin.config)
    if plugin.config.hot_reload:
        console.rule("[yellow]Starting Vite process with HMR Enabled[/]", align="left")
    else:
        console.rule("[yellow]Starting Vite watch and build process[/]", align="left")
    command_to_run = plugin.config.run_command if plugin.config.hot_reload else plugin.config.build_watch_command

    if plugin.config.executor:
        try:
            root_dir = Path(plugin.config.root_dir or Path.cwd())
            plugin.config.executor.execute(command_to_run, cwd=root_dir)
            console.print("[yellow]Vite process stopped.[/]")
        except ViteExecutionError as e:
            console.print(f"[bold red] Vite process failed: {e!s}[/]")
    else:
        console.print("[red]Executor not configured.[/]")


@vite_group.command(
    name="export-routes",
    help="Export route metadata for type-safe routing.",
)
@option(
    "--output",
    help="Output file path",
    type=ClickPath(dir_okay=False, path_type=Path),
    default=None,
    show_default=False,
)
@option(
    "--only",
    help="Only include routes matching these patterns (comma-separated)",
    type=str,
    default=None,
)
@option(
    "--except",
    "exclude",
    help="Exclude routes matching these patterns (comma-separated)",
    type=str,
    default=None,
)
@option(
    "--include-components",
    help="Include Inertia component names",
    type=bool,
    default=True,
    is_flag=True,
)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def export_routes(
    app: "Litestar",
    output: "Optional[Path]",
    only: "Optional[str]",
    exclude: "Optional[str]",
    include_components: "bool",
    verbose: "bool",
) -> None:
    """Export route metadata for type-safe routing.

    Args:
        app: The Litestar application instance.
        output: The path to the output file. Uses TypeGenConfig if not provided.
        only: Comma-separated list of route patterns to include.
        exclude: Comma-separated list of route patterns to exclude.
        include_components: Include Inertia component names in output.
        verbose: Whether to enable verbose output.

    Raises:
        LitestarCLIException: If the output file cannot be written.
    """
    import msgspec
    from litestar.cli._utils import LitestarCLIException, console  # pyright: ignore[reportPrivateImportUsage]

    from litestar_vite.codegen import generate_routes_json
    from litestar_vite.config import TypeGenConfig
    from litestar_vite.plugin import VitePlugin

    if verbose:
        app.debug = True

    plugin = app.plugins.get(VitePlugin)
    config = plugin.config

    # Determine output path
    if output is None:
        if isinstance(config.types, TypeGenConfig) and config.types.enabled:
            output = config.types.routes_path
        else:
            output = Path("routes.json")

    console.rule(f"[yellow]Exporting routes to {output}[/]", align="left")

    # Parse filter lists
    only_list = [p.strip() for p in only.split(",")] if only else None
    exclude_list = [p.strip() for p in exclude.split(",")] if exclude else None

    # Generate routes JSON
    routes_data = generate_routes_json(
        app,
        only=only_list,
        exclude=exclude_list,
        include_components=include_components,
    )

    try:
        content = msgspec.json.format(
            msgspec.json.encode(routes_data),
            indent=2,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(content)
        console.print(f"[green]✓ Routes exported to {output}[/]")
        console.print(f"[dim]  {len(routes_data.get('routes', {}))} routes exported[/]")
    except OSError as e:  # pragma: no cover
        msg = f"Failed to write routes to path {output}"
        raise LitestarCLIException(msg) from e


@vite_group.command(
    name="generate-types",
    help="Generate TypeScript types from OpenAPI schema and routes.",
)
@option("--verbose", type=bool, help="Enable verbose output.", default=False, is_flag=True)
def generate_types(app: "Litestar", verbose: "bool") -> None:
    """Generate TypeScript types from OpenAPI schema and routes.

    This command:
    1. Exports the OpenAPI schema (uses litestar's built-in schema generation)
    2. Exports route metadata
    3. Runs @hey-api/openapi-ts to generate TypeScript types
    4. Generates route helper functions

    Args:
        app: The Litestar application instance.
        verbose: Whether to enable verbose output.

    Raises:
        LitestarCLIException: If type generation fails.
    """
    import subprocess

    import msgspec
    from litestar.cli._utils import LitestarCLIException, console  # pyright: ignore[reportPrivateImportUsage]
    from litestar.serialization import encode_json, get_serializer

    from litestar_vite.codegen import generate_routes_json
    from litestar_vite.config import TypeGenConfig
    from litestar_vite.plugin import VitePlugin

    if verbose:
        app.debug = True

    plugin = app.plugins.get(VitePlugin)
    config = plugin.config

    # Check if types are enabled
    if not isinstance(config.types, TypeGenConfig) or not config.types.enabled:
        console.print("[yellow]Type generation is not enabled in ViteConfig[/]")
        console.print("[dim]Set types=True or types=TypeGenConfig(enabled=True) in ViteConfig[/]")
        return

    console.rule("[yellow]Generating TypeScript types[/]", align="left")

    # Step 1: Export OpenAPI schema directly
    console.print("[dim]1. Exporting OpenAPI schema...[/]")
    try:
        serializer = get_serializer(app.type_encoders)
        schema_dict = app.openapi_schema.to_schema()
        schema_content = msgspec.json.format(
            encode_json(schema_dict, serializer=serializer),
            indent=2,
        )
        config.types.openapi_path.parent.mkdir(parents=True, exist_ok=True)
        config.types.openapi_path.write_bytes(schema_content)
        console.print(f"[green]✓ Schema exported to {config.types.openapi_path}[/]")
    except OSError as e:
        msg = f"Failed to export OpenAPI schema: {e}"
        raise LitestarCLIException(msg) from e

    # Step 2: Export routes
    console.print("[dim]2. Exporting route metadata...[/]")
    try:
        routes_data = generate_routes_json(app, include_components=True)
        routes_content = msgspec.json.format(
            msgspec.json.encode(routes_data),
            indent=2,
        )
        config.types.routes_path.parent.mkdir(parents=True, exist_ok=True)
        config.types.routes_path.write_bytes(routes_content)
        console.print(f"[green]✓ Routes exported to {config.types.routes_path}[/]")
    except OSError as e:
        msg = f"Failed to export routes: {e}"
        raise LitestarCLIException(msg) from e

    # Step 3: Run @hey-api/openapi-ts
    console.print("[dim]3. Running @hey-api/openapi-ts...[/]")

    try:
        # Check if @hey-api/openapi-ts is installed
        check_cmd = ["npx", "@hey-api/openapi-ts", "--version"]
        subprocess.run(check_cmd, check=True, capture_output=True, cwd=config.root_dir)

        # Run the type generation
        openapi_cmd = [
            "npx",
            "@hey-api/openapi-ts",
            "-i",
            str(config.types.openapi_path),
            "-o",
            str(config.types.output),
        ]
        if config.types.generate_zod:
            openapi_cmd.extend(["--plugins", "@hey-api/schemas", "@hey-api/types"])

        subprocess.run(openapi_cmd, check=True, cwd=config.root_dir)
        console.print(f"[green]✓ Types generated in {config.types.output}[/]")
    except subprocess.CalledProcessError as e:
        console.print("[yellow]! @hey-api/openapi-ts failed - install it with:[/]")
        console.print("[dim]  npm install -D @hey-api/openapi-ts[/]")
        if verbose:
            console.print(f"[dim]Error: {e!s}[/]")
    except FileNotFoundError:
        console.print("[yellow]! npx not found - ensure Node.js is installed[/]")


@vite_group.command(
    name="status",
    help="Check the status of the Vite integration.",
)
def vite_status(app: "Litestar") -> None:
    """Check the status of the Vite integration."""
    import httpx
    from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]

    from litestar_vite.plugin import VitePlugin

    plugin = app.plugins.get(VitePlugin)
    config = plugin.config

    console.rule("[yellow]Vite Integration Status[/]", align="left")
    console.print(f"Dev Mode: {config.dev_mode}")
    console.print(f"Hot Reload: {config.hot_reload}")
    console.print(f"Assets URL: {config.asset_url}")
    console.print(f"Base URL: {config.base_url}")

    manifest_path = Path(f"{config.bundle_dir}/{config.manifest_name}")
    if manifest_path.exists():
        console.print(f"[green]✓ Manifest found at {manifest_path}[/]")
    else:
        console.print(f"[red]✗ Manifest not found at {manifest_path}[/]")

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

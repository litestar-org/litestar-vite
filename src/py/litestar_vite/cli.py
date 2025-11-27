from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from click import Choice, Context, group, option
from click import Path as ClickPath
from litestar.cli._utils import LitestarEnv, LitestarGroup  # pyright: ignore[reportPrivateImportUsage]

if TYPE_CHECKING:
    from litestar import Litestar


# Available framework templates for --template option
FRAMEWORK_CHOICES = [
    "react",
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


@group(cls=LitestarGroup, name="assets")
def vite_group() -> None:
    """Manage Vite Tasks."""


def _select_framework_template(
    template: "Optional[str]",
    no_prompt: bool,
) -> "tuple[str, Any]":
    """Select and validate the framework template.

    Args:
        template: User-provided template name or None.
        no_prompt: Whether to skip interactive prompts.

    Returns:
        Tuple of (template_name, framework_template).

    Raises:
        SystemExit: If template is invalid.
    """
    import sys

    from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]
    from rich.prompt import Prompt

    from litestar_vite.scaffolding import get_available_templates
    from litestar_vite.scaffolding.templates import get_template

    if template is None and not no_prompt:
        available = get_available_templates()
        console.print("\n[bold]Available framework templates:[/]")
        for i, tmpl in enumerate(available, 1):
            console.print(f"  {i}. [cyan]{tmpl.type.value}[/] - {tmpl.description}")

        template = Prompt.ask(
            "\nSelect a framework template",
            choices=[t.type.value for t in available],
            default="react",
        )
    elif template is None:
        template = "react"  # Default when --no-prompt

    framework = get_template(template)
    if framework is None:
        console.print(f"[red]Unknown template: {template}[/]")
        sys.exit(1)

    return template, framework


def _prompt_for_options(
    framework: "Any",
    enable_ssr: "Optional[bool]",
    tailwind: bool,
    enable_types: bool,
    no_prompt: bool,
) -> "tuple[bool, bool, bool]":
    """Prompt user for optional features if not specified.

    Args:
        framework: The framework template.
        enable_ssr: SSR flag or None.
        tailwind: TailwindCSS flag.
        enable_types: Type generation flag.
        no_prompt: Whether to skip prompts.

    Returns:
        Tuple of (enable_ssr, tailwind, enable_types).
    """
    from rich.prompt import Confirm

    if enable_ssr is None:
        enable_ssr = (
            framework.has_ssr if no_prompt else Confirm.ask("Enable server-side rendering?", default=framework.has_ssr)
        )

    if not tailwind and not no_prompt:
        tailwind = Confirm.ask("Add TailwindCSS?", default=False)

    if not enable_types and not no_prompt:
        enable_types = Confirm.ask("Enable TypeScript type generation?", default=True)

    return enable_ssr or False, tailwind, enable_types


@vite_group.command(
    name="init",
    help="Initialize vite for your project.",
)
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
@option(
    "--tailwind",
    type=bool,
    help="Add TailwindCSS to the project.",
    required=False,
    show_default=False,
    is_flag=True,
)
@option(
    "--enable-types",
    type=bool,
    help="Enable TypeScript type generation from routes.",
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
    template: "Optional[str]",
    vite_port: "Optional[int]",
    enable_ssr: "Optional[bool]",
    asset_url: "Optional[str]",
    root_path: "Optional[Path]",
    frontend_dir: str,
    bundle_path: "Optional[Path]",
    resource_path: "Optional[Path]",
    public_path: "Optional[Path]",
    tailwind: "bool",
    enable_types: "bool",
    overwrite: "bool",
    verbose: "bool",
    no_prompt: "bool",
    no_install: "bool",
) -> None:
    """Initialize a new Vite project with framework templates."""
    import sys
    from pathlib import Path

    from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]
    from rich.prompt import Confirm

    from litestar_vite import VitePlugin
    from litestar_vite.scaffolding import TemplateContext, generate_project
    from litestar_vite.scaffolding.templates import FrameworkType

    if callable(ctx.obj):
        ctx.obj = ctx.obj()
    elif verbose:
        ctx.obj.app.debug = True
    env: LitestarEnv = ctx.obj
    plugin = env.app.plugins.get(VitePlugin)
    config = plugin._config  # pyright: ignore[reportPrivateUsage]

    console.rule("[yellow]Initializing Vite[/]", align="left")

    # Resolve root and base values
    root_path = Path(root_path or config.root_dir or Path.cwd())
    frontend_dir = frontend_dir or "."
    asset_url = asset_url or config.asset_url
    vite_port = vite_port or config.port
    litestar_port = env.port or 8000

    # Select framework template
    template, framework = _select_framework_template(template, no_prompt)
    console.print(f"\n[green]Using {framework.name} template[/]")

    # Resolve paths now that framework defaults are known
    resource_path_str = str(resource_path or framework.resource_dir or config.resource_dir)
    bundle_path_str = str(bundle_path or config.bundle_dir)

    # Check for existing files
    if (
        any((root_path / p).exists() for p in [resource_path_str, bundle_path_str])
        and not any(
            [overwrite, no_prompt],
        )
        and not Confirm.ask("Files were found in the paths specified. Are you sure you wish to overwrite the contents?")
    ):
        console.print("Skipping Vite initialization")
        sys.exit(2)

    # Prompt for optional features
    enable_ssr, tailwind, enable_types = _prompt_for_options(framework, enable_ssr, tailwind, enable_types, no_prompt)

    # Create template context
    project_name = root_path.name or "my-project"
    is_inertia = framework.type in (
        FrameworkType.REACT_INERTIA,
        FrameworkType.VUE_INERTIA,
        FrameworkType.SVELTE_INERTIA,
    )
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
        base_dir=frontend_dir,
        enable_ssr=enable_ssr,
        enable_inertia=is_inertia,
        enable_types=enable_types,
    )

    # Generate project files
    console.print("\n[yellow]Generating project files...[/]")
    generated = generate_project(root_path, context, overwrite=overwrite)
    console.print(f"\n[green]Generated {len(generated)} files[/]")

    # Install dependencies
    if not no_install:
        console.rule("[yellow]Starting package installation process[/]", align="left")
        config.executor.install(root_path)

    console.print("\n[bold green]Vite initialization complete![/]")
    console.print(f"\n[dim]Next steps:\n  cd {root_path}\n  npm run dev[/]")


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


def _export_openapi_schema(app: "Litestar", types_config: Any) -> None:
    """Export OpenAPI schema to file.

    Args:
        app: The Litestar application instance.
        types_config: The TypeGenConfig instance.

    Raises:
        LitestarCLIException: If export fails.
    """
    import msgspec
    from litestar.cli._utils import LitestarCLIException, console  # pyright: ignore[reportPrivateImportUsage]
    from litestar.serialization import encode_json, get_serializer

    console.print("[dim]1. Exporting OpenAPI schema...[/]")
    try:
        serializer = get_serializer(app.type_encoders)
        schema_dict = app.openapi_schema.to_schema()
        schema_content = msgspec.json.format(
            encode_json(schema_dict, serializer=serializer),
            indent=2,
        )
        types_config.openapi_path.parent.mkdir(parents=True, exist_ok=True)
        types_config.openapi_path.write_bytes(schema_content)
        console.print(f"[green]✓ Schema exported to {types_config.openapi_path}[/]")
    except OSError as e:
        msg = f"Failed to export OpenAPI schema: {e}"
        raise LitestarCLIException(msg) from e


def _export_routes_metadata(app: "Litestar", types_config: Any) -> None:
    """Export routes metadata to file.

    Args:
        app: The Litestar application instance.
        types_config: The TypeGenConfig instance.

    Raises:
        LitestarCLIException: If export fails.
    """
    import msgspec
    from litestar.cli._utils import LitestarCLIException, console  # pyright: ignore[reportPrivateImportUsage]

    from litestar_vite.codegen import generate_routes_json

    console.print("[dim]2. Exporting route metadata...[/]")
    try:
        routes_data = generate_routes_json(app, include_components=True)
        routes_content = msgspec.json.format(
            msgspec.json.encode(routes_data),
            indent=2,
        )
        types_config.routes_path.parent.mkdir(parents=True, exist_ok=True)
        types_config.routes_path.write_bytes(routes_content)
        console.print(f"[green]✓ Routes exported to {types_config.routes_path}[/]")
    except OSError as e:
        msg = f"Failed to export routes: {e}"
        raise LitestarCLIException(msg) from e


def _run_openapi_ts(types_config: Any, root_dir: Any, verbose: bool) -> None:
    """Run @hey-api/openapi-ts to generate TypeScript types.

    Args:
        types_config: The TypeGenConfig instance.
        root_dir: The root directory for the project.
        verbose: Whether to show verbose output.
    """
    import subprocess

    from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]

    console.print("[dim]3. Running @hey-api/openapi-ts...[/]")

    try:
        # Check if @hey-api/openapi-ts is installed
        check_cmd = ["npx", "@hey-api/openapi-ts", "--version"]
        subprocess.run(check_cmd, check=True, capture_output=True, cwd=root_dir)

        # Run the type generation
        openapi_cmd = [
            "npx",
            "@hey-api/openapi-ts",
            "-i",
            str(types_config.openapi_path),
            "-o",
            str(types_config.output),
        ]
        if types_config.generate_zod:
            openapi_cmd.extend(["--plugins", "@hey-api/schemas", "@hey-api/types"])

        subprocess.run(openapi_cmd, check=True, cwd=root_dir)
        console.print(f"[green]✓ Types generated in {types_config.output}[/]")
    except subprocess.CalledProcessError as e:
        console.print("[yellow]! @hey-api/openapi-ts failed - install it with:[/]")
        console.print("[dim]  npm install -D @hey-api/openapi-ts[/]")
        if verbose:
            console.print(f"[dim]Error: {e!s}[/]")
    except FileNotFoundError:
        console.print("[yellow]! npx not found - ensure Node.js is installed[/]")


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

    Args:
        app: The Litestar application instance.
        verbose: Whether to enable verbose output.

    Raises:
        LitestarCLIException: If type generation fails.
    """
    from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]

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

    _export_openapi_schema(app, config.types)
    _export_routes_metadata(app, config.types)
    _run_openapi_ts(config.types, config.root_dir, verbose)


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

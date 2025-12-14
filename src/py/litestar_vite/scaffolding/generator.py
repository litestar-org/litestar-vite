"""Project scaffolding generator.

This module handles the generation of project files from templates.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from litestar_vite.scaffolding.templates import FrameworkTemplate


def _dict_factory() -> dict[str, Any]:
    return {}


_DictStrAnyFactory: Callable[[], dict[str, Any]] = _dict_factory


@dataclass
class TemplateContext:
    """Context variables for template rendering.

    Attributes:
        project_name: Name of the project
        framework: The selected framework template
        use_typescript: Whether to use TypeScript
        use_tailwind: Whether to add TailwindCSS
        vite_port: Vite dev server port
        litestar_port: Litestar server port
        asset_url: Base URL for assets
        resource_dir: Source directory for frontend files
        bundle_dir: Output directory for built files
        enable_ssr: Whether SSR is enabled
        enable_inertia: Whether Inertia.js is used
        enable_types: Whether type generation is enabled
        generate_zod: Whether to generate Zod schemas
        generate_client: Whether to generate API client
    """

    project_name: str
    framework: "FrameworkTemplate"
    use_typescript: bool = True
    use_tailwind: bool = False
    vite_port: int = 5173
    litestar_port: int = 8000
    asset_url: str = "/static/"
    resource_dir: str = "resources"
    bundle_dir: str = "public"
    static_dir: str = "public"
    base_dir: str = "."
    enable_ssr: bool = False
    enable_inertia: bool = False
    enable_types: bool = True
    generate_zod: bool = False
    generate_client: bool = False
    extra: dict[str, Any] = field(default_factory=_DictStrAnyFactory)

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for Jinja2 rendering.

        Returns:
            Dictionary of template variables.
        """
        return {
            "project_name": self.project_name,
            "framework": self.framework.type.value,
            "framework_name": self.framework.name,
            "use_typescript": self.use_typescript,
            "use_tailwind": self.use_tailwind,
            "vite_port": self.vite_port,
            "litestar_port": self.litestar_port,
            "asset_url": self.asset_url,
            "resource_dir": self.resource_dir,
            "bundle_dir": self.bundle_dir,
            "static_dir": self.static_dir,
            "base_dir": self.base_dir,
            "enable_ssr": self.enable_ssr,
            "enable_inertia": self.enable_inertia,
            "enable_types": self.enable_types,
            "generate_zod": self.generate_zod,
            "generate_client": self.generate_client,
            "dependencies": self.framework.dependencies,
            "dev_dependencies": self.framework.dev_dependencies,
            "vite_plugin": self.framework.vite_plugin,
            "uses_vite": self.framework.uses_vite,
            **self.extra,
        }


def get_template_dir() -> Path:
    """Get the directory containing framework templates.

    Returns:
        Path to the templates directory.
    """
    return Path(__file__).parent.parent / "templates"


def render_template(template_path: Path, context: dict[str, Any]) -> str:
    """Render a Jinja2 template with the given context.

    Templates are rendered with autoescaping disabled because the output is code
    and configuration files, not HTML.

    Args:
        template_path: Path to the template file.
        context: Dictionary of template variables.

    Returns:
        Rendered template content.
    """
    from jinja2 import Environment, FileSystemLoader

    template_dir = template_path.parent
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
        autoescape=False,  # noqa: S701
    )
    template = env.get_template(template_path.name)
    return template.render(**context)


def _process_templates(
    template_dir: Path,
    output_dir: Path,
    context_dict: dict[str, Any],
    resource_dir: str,
    *,
    overwrite: bool,
    skip_paths: "set[Path] | None" = None,
) -> list[Path]:
    """Process templates from a directory and generate output files.

    This function rewrites template paths so frameworks can customize the output
    directory layout:

    - ``resources/`` templates are rewritten to the configured ``resource_dir``.
    - ``public/`` templates can be relocated via ``static_dir`` in the context.

    SSR entrypoints under ``resources/`` are only generated when SSR is enabled.

    Args:
        template_dir: Directory containing template files.
        output_dir: Directory to write generated files.
        context_dict: Template context dictionary.
        resource_dir: Resource directory name for path rewriting.
        overwrite: Whether to overwrite existing files.
        skip_paths: Set of relative paths to skip.

    Returns:
        List of generated file paths.
    """
    from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]

    generated_files: list[Path] = []
    skip_paths = skip_paths or set()
    enable_ssr = bool(context_dict.get("enable_ssr"))

    for template_file in template_dir.glob("**/*.j2"):
        relative_path = template_file.relative_to(template_dir)

        if relative_path in skip_paths:
            continue

        if (
            not enable_ssr
            and relative_path.parts
            and relative_path.parts[0] == "resources"
            and relative_path.name.startswith("ssr.")
        ):
            continue

        if relative_path.parts and relative_path.parts[0] == "resources":
            relative_path = Path(resource_dir, *relative_path.parts[1:])

        if relative_path.parts and relative_path.parts[0] == "public":
            relative_path = Path(context_dict.get("static_dir", "public"), *relative_path.parts[1:])

        output_path = output_dir / str(relative_path).replace(".j2", "")

        if output_path.exists() and not overwrite:
            console.print(f"[yellow]Skipping {output_path} (exists)[/]")
            continue

        _render_and_write(template_file, output_path, context_dict)
        generated_files.append(output_path)

    return generated_files


def generate_project(output_dir: Path, context: TemplateContext, *, overwrite: bool = False) -> list[Path]:
    """Generate project files from templates.

    Args:
        output_dir: Directory to generate files in.
        context: Template context with configuration.
        overwrite: Whether to overwrite existing files.

    Returns:
        List of generated file paths.
    """
    from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]

    template_dir = get_template_dir()
    framework_dir = template_dir / context.framework.type.value
    base_dir = template_dir / "base"
    context_dict = context.to_dict()
    generated_files: list[Path] = []

    framework_overrides: set[Path] = set()
    if framework_dir.exists():
        framework_overrides = {
            template_file.relative_to(framework_dir) for template_file in framework_dir.glob("**/*.j2")
        }

    actual_output_dir = output_dir / context.base_dir if context.base_dir not in {"", "."} else output_dir
    actual_output_dir.mkdir(parents=True, exist_ok=True)

    if context.framework.uses_vite and base_dir.exists():
        generated_files.extend(
            _process_templates(
                base_dir,
                actual_output_dir,
                context_dict,
                context.resource_dir,
                overwrite=overwrite,
                skip_paths=framework_overrides,
            )
        )

    if framework_dir.exists():
        generated_files.extend(
            _process_templates(
                framework_dir, actual_output_dir, context_dict, context.resource_dir, overwrite=overwrite
            )
        )
    else:
        console.print(f"[dim]No framework templates for {context.framework.type.value}, using base templates[/]")

    if context.use_tailwind:
        tailwind_dir = template_dir / "addons" / "tailwindcss"
        if tailwind_dir.exists():
            generated_files.extend(
                _process_templates(
                    tailwind_dir, actual_output_dir, context_dict, context.resource_dir, overwrite=overwrite
                )
            )

    return generated_files


def _render_and_write(template_path: Path, output_path: Path, context: dict[str, Any]) -> None:
    """Render a template and write to output file.

    Args:
        template_path: Path to the template file.
        output_path: Path to write the rendered content.
        context: Template context dictionary.
    """
    from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    content = render_template(template_path, context)
    output_path.write_text(content, encoding="utf-8")
    console.print(f"[green]Created {output_path}[/]")

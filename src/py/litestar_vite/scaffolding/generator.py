"""Project scaffolding generator.

This module handles the generation of project files from templates.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from litestar_vite.scaffolding.templates import FrameworkTemplate


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
    enable_ssr: bool = False
    enable_inertia: bool = False
    enable_types: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

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
            "enable_ssr": self.enable_ssr,
            "enable_inertia": self.enable_inertia,
            "enable_types": self.enable_types,
            "dependencies": self.framework.dependencies,
            "dev_dependencies": self.framework.dev_dependencies,
            "vite_plugin": self.framework.vite_plugin,
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
        autoescape=False,
    )
    template = env.get_template(template_path.name)
    return template.render(**context)


def generate_project(
    output_dir: Path,
    context: TemplateContext,
    *,
    overwrite: bool = False,
) -> list[Path]:
    """Generate project files from templates.

    Args:
        output_dir: Directory to generate files in.
        context: Template context with configuration.
        overwrite: Whether to overwrite existing files.

    Returns:
        List of generated file paths.

    Raises:
        FileExistsError: If a file exists and overwrite is False.
    """
    from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]

    template_dir = get_template_dir()
    framework_dir = template_dir / context.framework.type.value
    base_dir = template_dir / "base"
    context_dict = context.to_dict()
    generated_files: list[Path] = []

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process base templates first (shared across frameworks)
    if base_dir.exists():
        for template_file in base_dir.glob("**/*.j2"):
            relative_path = template_file.relative_to(base_dir)
            output_path = output_dir / str(relative_path).replace(".j2", "")

            if output_path.exists() and not overwrite:
                console.print(f"[yellow]Skipping {output_path} (exists)[/]")
                continue

            _render_and_write(template_file, output_path, context_dict)
            generated_files.append(output_path)

    # Process framework-specific templates
    if framework_dir.exists():
        for template_file in framework_dir.glob("**/*.j2"):
            relative_path = template_file.relative_to(framework_dir)
            output_path = output_dir / str(relative_path).replace(".j2", "")

            if output_path.exists() and not overwrite:
                console.print(f"[yellow]Skipping {output_path} (exists)[/]")
                continue

            _render_and_write(template_file, output_path, context_dict)
            generated_files.append(output_path)
    else:
        # Fallback to generic templates if framework-specific don't exist
        console.print(f"[dim]No framework templates for {context.framework.type.value}, using base templates[/]")

    # Add TailwindCSS addon if requested
    if context.use_tailwind:
        tailwind_dir = template_dir / "addons" / "tailwindcss"
        if tailwind_dir.exists():
            for template_file in tailwind_dir.glob("**/*.j2"):
                relative_path = template_file.relative_to(tailwind_dir)
                output_path = output_dir / str(relative_path).replace(".j2", "")

                if output_path.exists() and not overwrite:
                    console.print(f"[yellow]Skipping {output_path} (exists)[/]")
                    continue

                _render_and_write(template_file, output_path, context_dict)
                generated_files.append(output_path)

    return generated_files


def _render_and_write(
    template_path: Path,
    output_path: Path,
    context: dict[str, Any],
) -> None:
    """Render a template and write to output file.

    Args:
        template_path: Path to the template file.
        output_path: Path to write the rendered content.
        context: Template context dictionary.
    """
    from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Render and write
    content = render_template(template_path, context)
    output_path.write_text(content)
    console.print(f"[green]Created {output_path}[/]")

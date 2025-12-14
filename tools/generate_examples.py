import sys
from pathlib import Path
from typing import TypedDict

# Add src/py to path so we can import litestar_vite
src_path = Path(__file__).parent.parent / "src" / "py"
sys.path.append(str(src_path))

from litestar_vite.scaffolding.generator import TemplateContext, generate_project  # noqa: E402
from litestar_vite.scaffolding.templates import get_template  # noqa: E402

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


class ExampleConfig(TypedDict, total=False):
    enable_types: bool
    use_tailwind: bool
    use_typescript: bool
    enable_ssr: bool


class Example(TypedDict):
    name: str
    framework: str
    config: ExampleConfig


def main() -> None:
    examples: list[Example] = [
        {"name": "react", "framework": "react", "config": {"enable_types": True, "use_tailwind": True}},
        {"name": "vue-inertia", "framework": "vue-inertia", "config": {"enable_types": True, "use_tailwind": True}},
        {"name": "svelte", "framework": "svelte", "config": {"enable_types": True, "use_tailwind": True}},
        {"name": "sveltekit", "framework": "sveltekit", "config": {"enable_types": True, "use_tailwind": True}},
        {
            "name": "template-htmx",
            "framework": "htmx",
            "config": {
                "enable_types": False,  # HTMX template doesn't use TS
                "use_tailwind": True,
                "use_typescript": False,
            },
        },
        {"name": "astro", "framework": "astro", "config": {"enable_types": True, "use_tailwind": True}},
        {
            "name": "fullstack-typed",
            "framework": "react-inertia",
            "config": {"enable_types": True, "use_tailwind": True, "enable_ssr": True},
        },
    ]

    for example in examples:
        name = example["name"]
        framework_str = example["framework"]
        config = example.get("config", {})

        framework = get_template(framework_str)
        if not framework:
            continue

        output_dir = EXAMPLES_DIR / name

        # Determine defaults based on framework if not specified
        use_typescript = config.get("use_typescript", framework.uses_typescript)
        enable_ssr = config.get("enable_ssr", framework.has_ssr)
        is_inertia = framework.inertia_compatible and ("inertia" in framework.type.value)

        context = TemplateContext(
            project_name=name,
            framework=framework,
            use_typescript=use_typescript,
            use_tailwind=config.get("use_tailwind", False),
            enable_ssr=enable_ssr,
            enable_inertia=is_inertia,
            enable_types=config.get("enable_types", True),
            resource_dir="resources",  # Default
            bundle_dir="public",  # Default
        )

        generate_project(output_dir, context, overwrite=True)


if __name__ == "__main__":
    main()

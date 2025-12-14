"""Framework template definitions for scaffolding.

This module defines the available framework templates and their configurations.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum


def _str_list_factory() -> list[str]:
    return []


class FrameworkType(str, Enum):
    """Supported frontend framework types."""

    REACT = "react"
    REACT_ROUTER = "react-router"
    REACT_TANSTACK = "react-tanstack"
    REACT_INERTIA = "react-inertia"
    VUE = "vue"
    VUE_INERTIA = "vue-inertia"
    SVELTE = "svelte"
    SVELTE_INERTIA = "svelte-inertia"
    SVELTEKIT = "sveltekit"
    NUXT = "nuxt"
    ASTRO = "astro"
    HTMX = "htmx"
    ANGULAR = "angular"
    ANGULAR_CLI = "angular-cli"


_ListStrFactory: Callable[[], list[str]] = _str_list_factory


@dataclass
class FrameworkTemplate:
    """Configuration for a frontend framework template.

    Attributes:
        name: Display name for the template
        type: Framework type enum
        description: Brief description shown in selection UI
        vite_plugin: Name of the Vite plugin import (if any)
        dependencies: NPM dependencies to install
        dev_dependencies: NPM dev dependencies to install
        files: List of template files to generate
        uses_typescript: Whether TypeScript is used by default
        has_ssr: Whether SSR is supported
        inertia_compatible: Whether it works with Inertia.js
        uses_vite: Whether the template is Vite-based (skip base files when False)
        resource_dir: Preferred source directory name for the framework
    """

    name: str
    type: FrameworkType
    description: str
    vite_plugin: "str | None" = None
    dependencies: list[str] = field(default_factory=_ListStrFactory)
    dev_dependencies: list[str] = field(default_factory=_ListStrFactory)
    files: list[str] = field(default_factory=_ListStrFactory)
    uses_typescript: bool = True
    has_ssr: bool = False
    inertia_compatible: bool = False
    uses_vite: bool = True
    resource_dir: str = "resources"


FRAMEWORK_TEMPLATES: dict[FrameworkType, FrameworkTemplate] = {
    FrameworkType.REACT: FrameworkTemplate(
        name="React",
        type=FrameworkType.REACT,
        description="React 18+ with TypeScript and Vite",
        vite_plugin="@vitejs/plugin-react",
        dependencies=["react", "react-dom"],
        dev_dependencies=["@vitejs/plugin-react", "@types/react", "@types/react-dom", "typescript"],
        files=[
            "vite.config.ts",
            "tsconfig.json",
            "package.json",
            "index.html",
            "src/main.tsx",
            "src/App.tsx",
            "src/App.css",
        ],
        uses_typescript=True,
        has_ssr=False,
        inertia_compatible=True,
        resource_dir="src",
    ),
    FrameworkType.REACT_ROUTER: FrameworkTemplate(
        name="React + React Router",
        type=FrameworkType.REACT_ROUTER,
        description="React 18+ with React Router for SPA routing",
        vite_plugin="@vitejs/plugin-react",
        dependencies=["react", "react-dom", "react-router-dom"],
        dev_dependencies=["@vitejs/plugin-react", "@types/react", "@types/react-dom", "typescript"],
        files=[
            "vite.config.ts",
            "tsconfig.json",
            "package.json",
            "index.html",
            "src/main.tsx",
            "src/App.tsx",
            "src/App.css",
        ],
        uses_typescript=True,
        has_ssr=False,
        inertia_compatible=False,
        resource_dir="src",
    ),
    FrameworkType.REACT_TANSTACK: FrameworkTemplate(
        name="React + TanStack Router",
        type=FrameworkType.REACT_TANSTACK,
        description="React 18+ with TanStack Router (file-based), Zod, and API client",
        vite_plugin="@vitejs/plugin-react",
        dependencies=["react", "react-dom", "@tanstack/react-router", "zod"],
        dev_dependencies=[
            "@vitejs/plugin-react",
            "@tanstack/router-plugin",
            "@hey-api/openapi-ts",
            "@types/react",
            "@types/react-dom",
            "typescript",
        ],
        files=[
            "vite.config.ts",
            "tsconfig.json",
            "package.json",
            "index.html",
            "src/main.tsx",
            "src/routes/__root.tsx",
            "src/routes/index.tsx",
            "src/routes/books.tsx",
            "src/routeTree.gen.ts",
            "src/App.css",
            "openapi-ts.config.ts",
        ],
        uses_typescript=True,
        has_ssr=False,
        inertia_compatible=False,
        resource_dir="src",
    ),
    FrameworkType.REACT_INERTIA: FrameworkTemplate(
        name="React + Inertia.js",
        type=FrameworkType.REACT_INERTIA,
        description="React 18+ with Inertia.js for server-side routing",
        vite_plugin="@vitejs/plugin-react",
        dependencies=["react", "react-dom", "@inertiajs/react"],
        dev_dependencies=["@vitejs/plugin-react", "@types/react", "@types/react-dom", "typescript", "vite"],
        files=[
            "vite.config.ts",
            "tsconfig.json",
            "package.json",
            "index.html",
            "resources/main.tsx",
            "resources/ssr.tsx",
            "resources/pages/Home.tsx",
            "resources/App.css",
        ],
        uses_typescript=True,
        has_ssr=True,
        inertia_compatible=True,
        resource_dir="resources",
    ),
    FrameworkType.VUE: FrameworkTemplate(
        name="Vue 3",
        type=FrameworkType.VUE,
        description="Vue 3 with Composition API and TypeScript",
        vite_plugin="@vitejs/plugin-vue",
        dependencies=["vue"],
        dev_dependencies=["@vitejs/plugin-vue", "vue-tsc", "typescript"],
        files=[
            "vite.config.ts",
            "tsconfig.json",
            "package.json",
            "index.html",
            "env.d.ts",
            "src/main.ts",
            "src/App.vue",
            "src/style.css",
        ],
        uses_typescript=True,
        has_ssr=False,
        inertia_compatible=True,
        resource_dir="src",
    ),
    FrameworkType.VUE_INERTIA: FrameworkTemplate(
        name="Vue + Inertia.js",
        type=FrameworkType.VUE_INERTIA,
        description="Vue 3 with Inertia.js for server-side routing",
        vite_plugin="@vitejs/plugin-vue",
        dependencies=["vue", "@inertiajs/vue3"],
        dev_dependencies=["@vitejs/plugin-vue", "vue-tsc", "typescript"],
        files=[
            "vite.config.ts",
            "tsconfig.json",
            "package.json",
            "index.html",
            "env.d.ts",
            "resources/main.ts",
            "resources/ssr.ts",
            "resources/pages/Home.vue",
            "resources/style.css",
        ],
        uses_typescript=True,
        has_ssr=True,
        inertia_compatible=True,
        resource_dir="resources",
    ),
    FrameworkType.SVELTE: FrameworkTemplate(
        name="Svelte 5",
        type=FrameworkType.SVELTE,
        description="Svelte 5 with runes and TypeScript",
        vite_plugin="@sveltejs/vite-plugin-svelte",
        dependencies=["svelte"],
        dev_dependencies=["@sveltejs/vite-plugin-svelte", "svelte-check", "typescript", "tslib"],
        files=[
            "vite.config.ts",
            "svelte.config.js",
            "tsconfig.json",
            "package.json",
            "index.html",
            "src/main.ts",
            "src/App.svelte",
            "src/app.css",
        ],
        uses_typescript=True,
        has_ssr=False,
        inertia_compatible=True,
        resource_dir="src",
    ),
    FrameworkType.SVELTE_INERTIA: FrameworkTemplate(
        name="Svelte + Inertia.js",
        type=FrameworkType.SVELTE_INERTIA,
        description="Svelte 5 with Inertia.js for server-side routing",
        vite_plugin="@sveltejs/vite-plugin-svelte",
        dependencies=["svelte", "@inertiajs/svelte"],
        dev_dependencies=["@sveltejs/vite-plugin-svelte", "svelte-check", "typescript", "tslib"],
        files=[
            "vite.config.ts",
            "svelte.config.js",
            "tsconfig.json",
            "package.json",
            "index.html",
            "resources/main.ts",
            "resources/pages/Home.svelte",
            "resources/app.css",
        ],
        uses_typescript=True,
        has_ssr=False,
        inertia_compatible=True,
        resource_dir="resources",
    ),
    FrameworkType.SVELTEKIT: FrameworkTemplate(
        name="SvelteKit",
        type=FrameworkType.SVELTEKIT,
        description="SvelteKit with Litestar API backend",
        vite_plugin="litestar-vite-plugin/sveltekit",
        dependencies=["svelte", "@sveltejs/kit"],
        dev_dependencies=[
            "@sveltejs/vite-plugin-svelte",
            "@sveltejs/adapter-auto",
            "svelte-check",
            "typescript",
            "tslib",
            "litestar-vite-plugin",
        ],
        files=[
            "vite.config.ts",
            "svelte.config.js",
            "tsconfig.json",
            "src/app.html",
            "src/app.css",
            "src/hooks.server.ts",
            "src/routes/+page.svelte",
            "src/routes/+layout.svelte",
        ],
        uses_typescript=True,
        has_ssr=True,
        inertia_compatible=False,
    ),
    FrameworkType.NUXT: FrameworkTemplate(
        name="Nuxt 3",
        type=FrameworkType.NUXT,
        description="Nuxt 3 with Litestar API backend",
        vite_plugin=None,
        dependencies=["nuxt", "vue"],
        dev_dependencies=["typescript", "vue-tsc", "litestar-vite-plugin"],
        files=["nuxt.config.ts", "app.vue", "pages/index.vue", "composables/useApi.ts"],
        uses_typescript=True,
        has_ssr=True,
        inertia_compatible=False,
    ),
    FrameworkType.ASTRO: FrameworkTemplate(
        name="Astro",
        type=FrameworkType.ASTRO,
        description="Astro with Litestar API backend",
        vite_plugin="litestar-vite-plugin/astro",
        dependencies=["astro"],
        dev_dependencies=["typescript", "litestar-vite-plugin"],
        files=["astro.config.mjs", "src/pages/index.astro", "src/layouts/Layout.astro", "src/styles/global.css"],
        uses_typescript=True,
        has_ssr=True,
        inertia_compatible=False,
    ),
    FrameworkType.HTMX: FrameworkTemplate(
        name="HTMX",
        type=FrameworkType.HTMX,
        description="Server-rendered HTML with HTMX",
        vite_plugin=None,
        dependencies=["htmx.org"],
        dev_dependencies=["typescript"],
        files=["vite.config.ts", "resources/main.js", "templates/base.html.j2", "templates/index.html.j2"],
        uses_typescript=False,
        has_ssr=False,
        inertia_compatible=False,
        resource_dir="resources",
    ),
    FrameworkType.ANGULAR: FrameworkTemplate(
        name="Angular (Vite)",
        type=FrameworkType.ANGULAR,
        description="Angular 21+ with Vite (zoneless signals)",
        vite_plugin="@analogjs/vite-plugin-angular",
        dependencies=[
            "@angular/animations",
            "@angular/common",
            "@angular/compiler",
            "@angular/core",
            "@angular/forms",
            "@angular/platform-browser",
            "rxjs",
        ],
        dev_dependencies=[
            "@analogjs/vite-plugin-angular",
            "@angular/build",
            "@angular/compiler-cli",
            "@angular/platform-browser-dynamic",
            "typescript",
            "@types/node",
        ],
        files=[
            "vite.config.ts",
            "tsconfig.json",
            "tsconfig.app.json",
            "package.json",
            "index.html",
            "src/main.ts",
            "src/styles.css",
            "src/app/app.component.ts",
            "src/app/app.component.html",
            "src/app/app.component.css",
            "src/app/app.config.ts",
        ],
        uses_typescript=True,
        has_ssr=False,
        inertia_compatible=False,
        uses_vite=True,
        resource_dir="src",
    ),
    FrameworkType.ANGULAR_CLI: FrameworkTemplate(
        name="Angular CLI",
        type=FrameworkType.ANGULAR_CLI,
        description="Angular 21+ with zoneless signals and TailwindCSS (Angular CLI)",
        vite_plugin=None,
        dependencies=[
            "@angular/animations",
            "@angular/common",
            "@angular/compiler",
            "@angular/core",
            "@angular/forms",
            "@angular/platform-browser",
            "@angular/platform-browser-dynamic",
            "rxjs",
            "@tailwindcss/postcss",
            "tailwindcss",
        ],
        dev_dependencies=[
            "@angular-devkit/build-angular",
            "@angular/cli",
            "@angular/compiler-cli",
            "@types/node",
            "typescript",
            "postcss",
            "autoprefixer",
        ],
        files=[
            "angular.json",
            "tsconfig.json",
            "tsconfig.app.json",
            "tsconfig.spec.json",
            "package.json",
            "proxy.conf.json",
            ".postcssrc.json",
            "tailwind.config.js",
            "src/index.html",
            "src/main.ts",
            "src/styles.css",
            "src/app/app.component.ts",
            "src/app/app.component.html",
            "src/app/app.component.css",
            "src/app/app.config.ts",
        ],
        uses_typescript=True,
        has_ssr=False,
        inertia_compatible=False,
        uses_vite=False,
        resource_dir="src",
    ),
}


def get_available_templates() -> list[FrameworkTemplate]:
    """Get all available framework templates.

    Returns:
        List of available FrameworkTemplate instances.
    """
    return list(FRAMEWORK_TEMPLATES.values())


def get_template(framework_type: "FrameworkType | str") -> "FrameworkTemplate | None":
    """Get a specific framework template.

    Args:
        framework_type: The framework type (enum or string).

    Returns:
        The FrameworkTemplate if found, None otherwise.
    """
    if isinstance(framework_type, FrameworkType):
        return FRAMEWORK_TEMPLATES.get(framework_type)
    try:
        return FRAMEWORK_TEMPLATES.get(FrameworkType(framework_type))
    except ValueError:
        return None

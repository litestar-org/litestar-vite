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


CURRENT_NPM_VERSION_RANGES: dict[str, str] = {
    "@analogjs/vite-plugin-angular": "2.3.1",
    "@angular-devkit/build-angular": "21.2.1",
    "@angular/animations": "21.2.1",
    "@angular/build": "21.2.1",
    "@angular/cli": "21.2.1",
    "@angular/common": "21.2.1",
    "@angular/compiler": "21.2.1",
    "@angular/compiler-cli": "21.2.1",
    "@angular/core": "21.2.1",
    "@angular/forms": "21.2.1",
    "@angular/platform-browser": "21.2.1",
    "@angular/platform-browser-dynamic": "21.2.1",
    "@angular/router": "21.2.1",
    "@hey-api/openapi-ts": "0.94.0",
    "@inertiajs/react": "2.3.17",
    "@inertiajs/svelte": "2.3.17",
    "@inertiajs/vue3": "2.3.17",
    "@sveltejs/adapter-auto": "7.0.1",
    "@sveltejs/adapter-node": "5.5.4",
    "@sveltejs/kit": "2.55.0",
    "@sveltejs/vite-plugin-svelte": "7.0.0",
    "@tailwindcss/postcss": "4.2.2",
    "@tailwindcss/vite": "4.2.2",
    "@tanstack/react-router": "1.166.2",
    "@tanstack/router-plugin": "1.166.2",
    "@types/jasmine": "6.0.0",
    "@types/node": "25.3.5",
    "@types/react": "19.2.14",
    "@types/react-dom": "19.2.3",
    "@vitejs/plugin-react": "6.0.1",
    "@vitejs/plugin-vue": "6.0.4",
    "@vue/tsconfig": "0.9.0",
    "@vue/server-renderer": "3.5.29",
    "astro": "5.18.0",
    "autoprefixer": "10.4.27",
    "axios": "1.13.6",
    "htmx.org": "2.0.8",
    "nitropack": "2.13.1",
    "nuxt": "4.3.1",
    "postcss": "8.5.8",
    "react": "19.2.4",
    "react-dom": "19.2.4",
    "react-router-dom": "7.13.1",
    "rxjs": "7.8.2",
    "svelte": "5.53.7",
    "svelte-check": "4.4.4",
    "tailwindcss": "4.2.2",
    "tslib": "2.8.1",
    "typescript": "5.9.3",
    "vite": "8.0.1",
    "vue": "3.5.29",
    "vue-tsc": "3.2.5",
    "zod": "4.3.6",
}


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
        description="React with TypeScript and Vite",
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
        description="React with React Router for SPA routing",
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
        description="React with TanStack Router (file-based), Zod, and API client",
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
        description="React with Inertia.js for server-side routing",
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
        name="Vue",
        type=FrameworkType.VUE,
        description="Vue with Composition API and TypeScript",
        vite_plugin="@vitejs/plugin-vue",
        dependencies=["vue"],
        dev_dependencies=["@vitejs/plugin-vue", "vue-tsc", "typescript"],
        files=[
            "vite.config.ts",
            "tsconfig.json",
            "tsconfig.app.json",
            "tsconfig.node.json",
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
        description="Vue with Inertia.js for server-side routing",
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
        name="Svelte",
        type=FrameworkType.SVELTE,
        description="Svelte with runes and TypeScript",
        vite_plugin="@sveltejs/vite-plugin-svelte",
        dependencies=["svelte"],
        dev_dependencies=["@sveltejs/vite-plugin-svelte", "svelte-check", "typescript", "tslib"],
        files=[
            "vite.config.ts",
            "svelte.config.js",
            "tsconfig.json",
            "package.json",
            "openapi-ts.config.ts",
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
        description="Svelte with Inertia.js for server-side routing",
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
            "@sveltejs/adapter-node",
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
        name="Nuxt",
        type=FrameworkType.NUXT,
        description="Nuxt with Litestar API backend",
        vite_plugin=None,
        dependencies=["nuxt", "vue"],
        dev_dependencies=["typescript", "vue-tsc", "litestar-vite-plugin"],
        files=[
            "package.json",
            "tsconfig.json",
            "nuxt.config.ts",
            "app/app.vue",
            "app/assets/css/app.css",
            "app/composables/useApi.ts",
            "app/pages/index.vue",
        ],
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
        files=[
            "package.json",
            "tsconfig.json",
            "astro.config.mjs",
            "src/pages/index.astro",
            "src/layouts/Layout.astro",
            "src/styles/global.css",
        ],
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
        files=[
            "package.json",
            "vite.config.ts",
            "resources/main.js",
            "templates/base.html.j2",
            "templates/index.html.j2",
        ],
        uses_typescript=False,
        has_ssr=False,
        inertia_compatible=False,
        resource_dir="resources",
    ),
    FrameworkType.ANGULAR: FrameworkTemplate(
        name="Angular (Vite)",
        type=FrameworkType.ANGULAR,
        description="Angular with standalone APIs, signals, and Vite",
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
            "src/app/app.routes.ts",
            "src/app/home.component.ts",
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
        description="Angular with the application builder, standalone APIs, and Angular CLI",
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
        ],
        dev_dependencies=[
            "@angular/build",
            "@angular/cli",
            "@angular/compiler-cli",
            "@tailwindcss/postcss",
            "@types/node",
            "postcss",
            "tailwindcss",
            "typescript",
        ],
        files=[
            "angular.json",
            "tsconfig.json",
            "tsconfig.app.json",
            "package.json",
            "proxy.conf.json",
            ".postcssrc.json",
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

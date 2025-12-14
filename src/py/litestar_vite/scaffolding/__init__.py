"""Project scaffolding module for litestar-vite.

This module provides the `litestar assets init` command with framework-specific
template generation. It supports multiple frontend frameworks and build tools.

Supported frameworks:
- React (with TypeScript)
- Vue 3 (with TypeScript)
- Vue + Inertia.js
- Svelte 5 (with runes)
- SvelteKit
- Nuxt 3
- Astro
- HTMX + Alpine.js
"""

from litestar_vite.scaffolding.generator import TemplateContext, generate_project
from litestar_vite.scaffolding.templates import FrameworkTemplate, get_available_templates

__all__ = ["FrameworkTemplate", "TemplateContext", "generate_project", "get_available_templates"]

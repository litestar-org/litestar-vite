---
description: Explore and understand the codebase structure
allowed-tools: Glob, Grep, Read, Bash
---

# Codebase Exploration

Exploring: **$ARGUMENTS**

## Quick Overview

### Python Structure

```
src/py/litestar_vite/
├── config.py          # ViteConfig
├── plugin.py          # VitePlugin (main entry)
├── loader.py          # ViteAssetLoader
├── cli.py             # CLI commands
├── commands.py        # CLI implementation
├── executor.py        # Process execution
├── exceptions.py      # Custom exceptions
├── html_transform.py  # HTML manipulation
├── inertia/           # Inertia.js integration
│   ├── config.py      # InertiaConfig
│   ├── plugin.py      # InertiaPlugin
│   ├── middleware.py  # InertiaMiddleware
│   ├── request.py     # InertiaRequest
│   └── response.py    # InertiaResponse
└── templates/         # Framework scaffolding templates
```

### TypeScript Structure

```
src/js/src/
├── index.ts           # Main Vite plugin
└── inertia-helpers/   # Inertia helper utilities
```

### Examples

```
examples/
├── react/         # React SPA
├── vue/           # Vue 3 SPA
├── svelte/        # Svelte 5 SPA
├── vue-inertia/   # Vue + Inertia
├── inertia/           # React + Inertia
├── angular/           # Angular + Vite
├── angular-cli/       # Angular CLI
├── nuxt/          # Nuxt 3
├── sveltekit/     # SvelteKit
├── astro/         # Astro
├── template-htmx/     # HTMX
├── basic/             # Basic Vite
├── flash/             # Flash messages
├── jinja/             # Jinja templates
└── fullstack-typed/   # Typed fullstack
```

## Search Commands

Find the specific area mentioned in "$ARGUMENTS":

```
# Find classes
Grep(pattern="class.*$ARGUMENTS", path="src/py/litestar_vite")

# Find functions
Grep(pattern="def.*$ARGUMENTS", path="src/py/litestar_vite")

# Find files
Glob(pattern="**/*$ARGUMENTS*")

# Find imports
Grep(pattern="from.*$ARGUMENTS|import.*$ARGUMENTS", path="src/py")
```

Explore the relevant files and explain the architecture.

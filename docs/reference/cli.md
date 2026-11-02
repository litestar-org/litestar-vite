# CLI Reference (`litestar assets`)

This page is deterministically generated from [`litestar_vite.cli.vite_group`](https://github.com/litestar-org/litestar-vite/blob/main/src/py/litestar_vite/cli.py) via `uv run python tools/docs/generate_cli_docs.py`.

All commands run under the Litestar CLI `assets` group:

```bash
litestar --app app:app assets <command> [OPTIONS]
```

| Command | Category | Summary |
| --- | --- | --- |
| [`litestar assets init`](#litestar-assets-init) | Scaffolding & Dependencies | Initialize vite for your project. |
| [`litestar assets install`](#litestar-assets-install) | Scaffolding & Dependencies | Install frontend packages. |
| [`litestar assets update`](#litestar-assets-update) | Scaffolding & Dependencies | Update frontend packages. |
| [`litestar assets serve`](#litestar-assets-serve) | Development, Build & Deploy | Serve frontend assets. For meta-frameworks (mode='framework'; aliases: 'ssr'/'ssg'), runs production Node server. Otherwise runs Vite dev server. |
| [`litestar assets build`](#litestar-assets-build) | Development, Build & Deploy | Building frontend assets with Vite. |
| [`litestar assets deploy`](#litestar-assets-deploy) | Development, Build & Deploy | Build and deploy Vite assets to remote storage via fsspec. |
| [`litestar assets generate-types`](#litestar-assets-generate-types) | Type Generation & Diagnostics | Generate TypeScript types from OpenAPI schema and routes. |
| [`litestar assets export-routes`](#litestar-assets-export-routes) | Type Generation & Diagnostics | Export route metadata for type-safe routing. |
| [`litestar assets doctor`](#litestar-assets-doctor) | Type Generation & Diagnostics | Diagnose and fix Vite configuration issues. |
| [`litestar assets status`](#litestar-assets-status) | Type Generation & Diagnostics | Check the status of the Vite integration. |

## Scaffolding & Dependencies

Commands for initializing new frontend templates and managing Node, Bun, Deno, Pnpm, or Yarn packages.

#### `litestar assets init`

Initialize vite for your project.

```bash
litestar assets init [OPTIONS]
```

**Options**

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `--template` | `Choice` | `None` | Frontend framework template to use. Inertia variants available: react-inertia, vue-inertia, svelte-inertia. (Choices: `react`, `react-router`, `react-tanstack`, `react-inertia`, `react-inertia-jinja`, `vue`, `vue-inertia`, `vue-inertia-ssr`, `vue-inertia-jinja`, `vue-inertia-jinja-ssr`, `svelte`, `svelte-inertia`, `svelte-inertia-jinja`, `sveltekit`, `nuxt`, `astro`, `htmx`, `jinja-htmx`, `htmx-no-jinja`, `angular`, `angular-cli`) |
| `--root-path` | `Path` | `None` | The path for the initial the Vite application.  This is the equivalent to the top-level folder in a normal Vue or React application.. |
| `--frontend-dir` | `text` | `"."` | Optional subdirectory under root to place the generated frontend (e.g., 'web'). |
| `--bundle-path` | `Path` | `None` | The path for the built Vite assets.  This is the where the output of `npm run build` will write files. |
| `--resource-path` | `Path` | `None` | The path to your Javascript/Typescript source and associated assets.  If this were a standalone Vue or React app, this would point to your `src/` folder. |
| `--static-path` | `Path` | `None` | The optional path to your static (unprocessed) frontend assets. If this were a standalone Vite app, this would point to your `public/` folder. |
| `--asset-url` | `text` | `None` | Base url to serve assets from. |
| `--vite-port` | `integer` | `None` | The port to run the vite server against. |
| `--enable-ssr` | `bool` | `False` | Enable SSR support. |
| `--disable-ssr` | `bool` | `False` | Disable SSR support. |
| `--tailwind` | `bool` | `False` | Add TailwindCSS to the project. |
| `--enable-types` | `bool` | `False` | Enable TypeScript type generation from routes. |
| `--no-enable-types` | `bool` | `False` | Disable TypeScript type generation from routes. |
| `--generate-zod` | `bool` | `False` | Generate Zod schemas for runtime validation. |
| `--generate-client` | `bool` | `False` | Generate API client from OpenAPI schema. |
| `--no-generate-client` | `bool` | `False` | Disable API client generation from OpenAPI schema. |
| `--overwrite` | `bool` | `False` | Overwrite any files in place. |
| `--verbose` | `bool` | `False` | Enable verbose output. |
| `--no-prompt` | `bool` | `False` | Do not prompt for confirmation and use all defaults for initializing the project. |
| `--no-install` | `bool` | `False` | Do not execute the installation commands after generating templates. |

#### `litestar assets install`

Install frontend packages.

```bash
litestar assets install [OPTIONS]
```

**Options**

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `--verbose` | `bool` | `False` | Enable verbose output. |
| `--quiet` | `bool` | `False` | Suppress non-essential output. |

#### `litestar assets update`

Update frontend packages.

```bash
litestar assets update [OPTIONS]
```

**Options**

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `--latest` | `bool` | `False` | Update to latest versions (ignoring semver constraints). |
| `--verbose` | `bool` | `False` | Enable verbose output. |
| `--quiet` | `bool` | `False` | Suppress non-essential output. |

## Development, Build & Deploy

Commands for running the Vite development server or production SSR server, building hashed asset bundles, and syncing bundles to CDN object storage.

#### `litestar assets serve`

Serve frontend assets. For meta-frameworks (mode='framework'; aliases: 'ssr'/'ssg'), runs production Node server. Otherwise runs Vite dev server.

```bash
litestar assets serve [OPTIONS]
```

**Options**

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `--verbose` | `bool` | `False` | Enable verbose output. |
| `--quiet` | `bool` | `False` | Suppress non-essential output. |
| `--production` | `bool` | `False` | Force production mode (run serve_command). |

#### `litestar assets build`

Building frontend assets with Vite.

```bash
litestar assets build [OPTIONS]
```

**Options**

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `--verbose` | `bool` | `False` | Enable verbose output. |
| `--quiet` | `bool` | `False` | Suppress non-essential output. |

#### `litestar assets deploy`

Build and deploy Vite assets to remote storage via fsspec.

```bash
litestar assets deploy [OPTIONS]
```

**Options**

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `--storage` | `text` | `None` | Override storage backend URL (e.g., gcs://bucket/assets). |
| `--storage-option` | `text` | `None` | Storage option key=value forwarded to fsspec (repeat for multiple). |
| `--no-build` | `bool` | `False` | Deploy existing build without running Vite build. |
| `--dry-run` | `bool` | `False` | Preview upload/delete plan without making changes. |
| `--no-delete` | `bool` | `False` | Do not delete orphaned remote files. |
| `--verbose` | `bool` | `False` | Enable verbose output. Install providers separately: gcsfs for gcs://, s3fs for s3://, adlfs for abfs://. |

## Type Generation & Diagnostics

Commands for exporting deterministic OpenAPI/AsyncAPI/route schemas, running the Python + TypeScript configuration doctor, and inspecting runtime status.

#### `litestar assets generate-types`

Generate TypeScript types from OpenAPI schema and routes.

```bash
litestar assets generate-types [OPTIONS]
```

**Options**

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `--verbose` | `bool` | `False` | Enable verbose output. |

#### `litestar assets export-routes`

Export route metadata for type-safe routing.

```bash
litestar assets export-routes [OPTIONS]
```

**Options**

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `--output` | `Path` | `None` | Output file path |
| `--only` | `text` | `None` | Only include routes matching these patterns (comma-separated) |
| `--except` | `text` | `None` | Exclude routes matching these patterns (comma-separated) |
| `--include-components` | `bool` | `True` | Include Inertia component names |
| `--typescript`, `--ts` | `bool` | `False` | Generate typed routes.ts file (Ziggy-style) instead of JSON |
| `--verbose` | `bool` | `False` | Enable verbose output. |

#### `litestar assets doctor`

Diagnose and fix Vite configuration issues.

```bash
litestar assets doctor [OPTIONS]
```

**Options**

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `--check` | `bool` | `False` | Exit with non-zero status if errors are found (for CI). |
| `--fix` | `bool` | `False` | Auto-fix detected issues (with confirmation). |
| `--no-prompt` | `bool` | `False` | Apply fixes without confirmation. |
| `--verbose` | `bool` | `False` | Enable verbose output. |
| `--show-config` | `bool` | `False` | Print .litestar.json and extracted litestar({ ... }) config block. |
| `--runtime-checks` | `bool` | `False` | Run runtime-state checks (Vite reachable / hotfile presence). |

#### `litestar assets status`

Check the status of the Vite integration.

```bash
litestar assets status
```

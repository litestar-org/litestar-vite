# Contributing & Development Setup

This guide covers local polyglot workspace setup, verification commands, and architectural conventions for contributors working on `litestar-vite` (Python) and `litestar-vite-plugin` (TypeScript).

---

## Prerequisites

- **Python**: `3.10` or newer managed with [`uv`](https://docs.astral.sh/uv/)
- **Node.js**: `20+` (or `22+` LTS) with `npm`
- **Vite**: `7.0.0+` (enforced across all runtime and test suites)

---

## Workspace Installation

Clone the repository and install both the Python virtual environment (all dependency groups) and TypeScript workspace packages:

```bash
git clone https://github.com/litestar-org/litestar-vite.git
cd litestar-vite
make install
```

Build the TypeScript plugin artifacts (`dist/`) and Python wheel/sdist before running integration tests:

```bash
make build
```

---

## Verification & Quality Gates

| Gate | Command | What It Checks |
| --- | --- | --- |
| **Python Unit & Integration Tests** | `NO_PROXY=localhost,127.0.0.1,::1 uv run pytest` | Full Python test suite (`src/py/tests/`) |
| **TypeScript Contract & Unit Tests** | `npm test` | Vitest suite (`npx vitest run --config ./src/js/vitest.config.ts`) |
| **Format & Auto-Fix** | `make fix` | `uv run ruff format` + Biome formatting across Python and TypeScript |
| **Static Type & Lint Gate** | `make check` | `ruff`, `mypy`, `pyright`, `slotscheck`, `biome`, and `tsc --noEmit` |
| **Docstring & Field Hygiene** | `uv run python tools/docs/scan_public_docstrings.py` | Enforces 1-sentence PEP 257 inline field docstrings, zero duplicate `Attributes:` blocks, and zero rST syntax |
| **CLI & TypeScript Auto-Docs** | `uv run python tools/docs/generate_cli_docs.py --check && uv run python tools/docs/generate_ts_docs.py --check` | Verifies `docs/reference/cli.md` and `docs/reference/typescript/*.md` match live source |
| **Documentation Snippet Gate** | `DOCS_EXAMPLES_STRICT=1 uv run python tools/check_docs_examples.py` | Validates fenced code blocks in `docs/**/*.md` and executes `docs/examples/**/*.py` |
| **Full Documentation Build Gate** | `uv run python tools/docs/verify_docs_artifacts.py --strict-warnings` | Runs Zensical build, `postbuild.py`, HTML size/TOC budgets, and redirect checks |

---

## Running Example Applications Locally

The `examples/` directory contains full runnable applications for every supported framework and operating mode (`react`, `react-inertia`, `vue`, `vue-inertia`, `svelte`, `sveltekit`, `nuxt`, `astro`, `angular`, `htmx`, `jinja-htmx`):

```bash
uv run litestar --app-dir examples/vue-inertia assets install
uv run litestar --app-dir examples/vue-inertia run --reload
```

---

## Architectural Guardrails

1. **Google-Style Docstrings & Inline Field Docstrings**: All public Python classes, functions, and `@dataclass`/`TypedDict` attributes use concise Markdown Google-style docstrings and PEP 257 inline `"""..."""` field docstrings (`0` inline `#` comments in Python source files).
2. **Single-Port AnyIO Streaming Proxy**: `ViteProxyMiddleware` (`src/py/litestar_vite/handler/_proxy.py`) uses `anyio.connect_tcp` and `wsproto` for WebSocket HMR and `httpx2` for pooled HTTP proxying.
3. **Granian `StaticPlacement.NATIVE` Compatibility**: Static metadata blocking (`BLOCKED_STATIC_METADATA_FILES`) and immutable caching use picklable slotted router-level hooks (`_StaticBeforeRequestHook`, `_StaticAfterRequestHook`) so `StaticFilesConfig.has_asgi_overrides()` stays `False`.
4. **Private OpenAPI Seam**: All access to Litestar's internal OpenAPI schema builders is confined to `src/py/litestar_vite/codegen/_openapi.py`.

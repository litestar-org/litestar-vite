# Development Workflow for litestar-vite

**Version**: 0.16.0 | **Updated**: 2026-01-04

This guide describes the standard development workflow for contributing to the `litestar-vite` project. It covers initial setup, daily development tasks, and the quality assurance process.

## 1. Initial Setup

All project tasks are managed through a `Makefile` and the `uv` Python package manager.

1. **Prerequisites**:
    - Python 3.10+
    - Node.js 20.19.0+ or 22.12.0+
    - `curl`

2. **Install `uv`**:
    If you don't have `uv` installed, you can install it with:

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

3. **Install Project Dependencies**:
    Run the `install` target from the `Makefile`. This is the only command you need to get started.

    ```bash
    make install
    ```

    This command will:
    - Create a Python virtual environment (`.venv/`).
    - Install all required Python dependencies using `uv`.
    - Install all required Node.js dependencies using `npm`.
    - Set up the `pre-commit` hooks.

## 2. Daily Development

### Frontend directory conventions

- Inertia variants follow Laravel conventions and use `resources/` (e.g., `resources/main.tsx`, `resources/pages/*`).
- All other templates (React, Vue, Svelte, HTMX, Angular Vite, etc.) use `src/` for source files and keep `index.html` at the frontend root.
- You can relocate the entire frontend under a subfolder (e.g., `web/`) via `litestar assets init --frontend-dir web`; generated files (package.json, vite.config.ts, src/…) will be placed there.
- When configuring `VitePlugin` manually for non-Inertia templates, set `paths.resource_dir="src"` (default for scaffolds). For Inertia templates, keep `resources/`.

### Running the Development Server

To work on an example application (like the `vue` one), run Litestar and let it manage Vite for you (single port by default):

- **Run Litestar App (starts/proxies Vite)**:

    ```bash
    uv run litestar --app examples.vue.app:app run --reload
    ```

- **Two-port option (start Vite yourself)**:

    ```bash
    uv run litestar --app examples.vue.app:app assets serve
    uv run litestar --app examples.vue.app:app run --reload
    ```

- **Production Server (SSR)**:

    ```bash
    uv run litestar --app examples.sveltekit.app:app assets serve --production
    ```

### Running Tests

As you make changes, you should run tests to ensure you haven't introduced any regressions.

```bash
# Run the full test suite (Python and JS)
make test

# Run only Python tests
pytest src/py/tests/

# Run only JS tests
npm run test
```

### Code Quality

Before committing, ensure your code meets the project's quality standards. The pre-commit hooks will run these checks automatically, but you can also run them manually.

```bash
# Run all linters and type checkers
make lint

# Auto-format your code
make fix
```

## 3. Committing and Pre-Commit Hooks

This project uses `pre-commit` to enforce code quality at the time of commit. When you run `git commit`, a series of automated checks (linting, formatting, type-checking) will execute.

If any of the checks fail, the commit will be aborted. You must fix the reported issues and re-add the files to your commit. For formatting issues, the hooks may fix them for you automatically; in this case, you just need to `git add` the modified files and commit again.

## 4. AI Agent Workflow

For significant features, this project uses an AI agent system with specialized agents for different phases.

See `AGENTS.md` and `CLAUDE.md` for detailed documentation on:

- `/prd [feature]` - Create Product Requirements Documents
- `/implement [slug]` - Implement features from PRDs
- `/test [slug]` - Create comprehensive test suites
- `/review [slug]` - Quality gates and documentation
- Specialized subagents: `prd`, `expert`, `testing`, `docs-vision`, `sync-guides`

The agent system guides features through planning, implementation, testing, and review, ensuring all quality gates are met.

## 5. Release Workflow

### Standard Release

For regular releases (patch, minor, major):

```bash
# Ensure clean working tree
git status

# Bump version (choose one)
make release bump=patch   # 0.16.0 → 0.16.1
make release bump=minor   # 0.16.0 → 0.17.0
make release bump=major   # 0.16.0 → 1.0.0

# Push to main
git push origin main

# Create GitHub release
gh release create v0.16.0 --title "v0.16.0" --generate-notes
```

### Pre-releases (Alpha/Beta/RC)

For testing breaking changes with a limited audience before stable release:

```bash
# Start alpha
make pre-release version=0.16.0-alpha.1

# Iterate on alpha
make pre-release version=0.16.0-alpha.2

# Progress to beta
make pre-release version=0.16.0-beta.1

# Release candidate
make pre-release version=0.16.0-rc.1

# Push and create pre-release
git push origin HEAD
gh release create v0.16.0-alpha.1 --prerelease --title "v0.16.0-alpha.1"
```

**Distribution:**

- PyPI: Pre-release versions are automatically marked (users need `pip install --pre` or explicit version)
- npm: Published with `next` tag (users install via `npm install litestar-vite-plugin@next`)

**Finalizing:** When ready for stable, run `make release bump=minor` (or `patch` from RC).

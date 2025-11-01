# Development Workflow for litestar-vite

This guide describes the standard development workflow for contributing to the `litestar-vite` project. It covers initial setup, daily development tasks, and the quality assurance process.

## 1. Initial Setup

All project tasks are managed through a `Makefile` and the `uv` Python package manager.

1.  **Prerequisites**:
    -   Python 3.8+
    -   Node.js and npm
    -   `curl`

2.  **Install `uv`**:
    If you don't have `uv` installed, you can install it with:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

3.  **Install Project Dependencies**:
    Run the `install` target from the `Makefile`. This is the only command you need to get started.
    ```bash
    make install
    ```
    This command will:
    -   Create a Python virtual environment (`.venv/`).
    -   Install all required Python dependencies using `uv`.
    -   Install all required Node.js dependencies using `npm`.
    -   Set up the `pre-commit` hooks.

## 2. Daily Development

### Running the Development Server

To work on an example application (like the `basic` one), you would typically run the Litestar backend and the Vite frontend dev server.

-   **Run Litestar App**:
    ```bash
    uv run uvicorn examples.basic.app:app --reload
    ```

-   **Run Vite Dev Server**:
    ```bash
    npm run dev --workspace=examples/basic
    ```

### Running Tests

As you make changes, you should run tests to ensure you haven't introduced any regressions.

```bash
# Run the full test suite (Python and JS)
make test

# Run only Python tests
pytest src/py/tests/

# Run only JS tests
npm run test --workspace=src/js
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

## 4. Gemini Agent Workflow

For significant features, this project uses the Gemini Agent System.

-   **Start a feature**: `gemini /prd "My new feature"`
-   **Implement a feature**: `gemini /implement <feature-slug>`

The agent system will guide the feature through a rigorous process of planning, implementation, testing, and review, ensuring all quality gates are met. Refer to `.gemini/GEMINI.md` for more details.

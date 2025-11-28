===================
Project Scaffolding
===================

Litestar Vite includes a powerful CLI for scaffolding new projects with your preferred
frontend framework. This tutorial covers the ``litestar assets init`` command and all available options.

Overview
--------

The scaffolding command creates a complete project structure with:

- Vite configuration optimized for your chosen framework
- Package.json with all required dependencies
- TypeScript configuration
- Sample components to get you started
- Integration with the litestar-vite plugin

Quick Start
-----------

The simplest way to scaffold a new project:

.. code-block:: bash

    litestar assets init

This starts an interactive wizard that guides you through the setup.

Available Frameworks
--------------------

The following frameworks are supported:

React
~~~~~

Modern React with Vite:

.. code-block:: bash

    litestar assets init --template react

Creates a React 18+ project with:

- JSX/TSX support
- React Router ready structure
- CSS modules support

React with Inertia.js
~~~~~~~~~~~~~~~~~~~~~

Server-side routing with React:

.. code-block:: bash

    litestar assets init --template react-inertia

Creates a React project with Inertia.js integration for building SPAs with server-side routing.

Vue 3
~~~~~

Vue 3 with Composition API:

.. code-block:: bash

    litestar assets init --template vue

Creates a Vue 3 project with:

- Single File Components (SFC)
- Composition API ready
- Vue Router ready structure

Vue with Inertia.js
~~~~~~~~~~~~~~~~~~~

Server-side routing with Vue:

.. code-block:: bash

    litestar assets init --template vue-inertia

Creates a Vue 3 project with Inertia.js integration.

Svelte
~~~~~~

Svelte 5 with Vite:

.. code-block:: bash

    litestar assets init --template svelte

Creates a Svelte project with:

- Svelte 5 runes support
- SvelteKit-compatible structure

Svelte with Inertia.js
~~~~~~~~~~~~~~~~~~~~~~

Server-side routing with Svelte:

.. code-block:: bash

    litestar assets init --template svelte-inertia

HTMX
~~~~

Hypermedia-driven applications:

.. code-block:: bash

    litestar assets init --template htmx

Creates an HTMX project with:

- HTMX and hyperscript
- Minimal JavaScript
- Server-rendered approach

Angular (Vite-based)
~~~~~~~~~~~~~~~~~~~~

Angular with Vite and AnalogJS:

.. code-block:: bash

    litestar assets init --template angular

Creates an Angular 18+ project using Vite for building:

- Standalone components
- Fast HMR via Vite
- Integration with litestar-vite-plugin

Angular CLI
~~~~~~~~~~~

Standard Angular CLI setup:

.. code-block:: bash

    litestar assets init --template angular-cli

Creates an Angular project using the standard Angular CLI:

- Uses webpack under the hood
- Proxy configuration for development
- Independent of litestar-vite-plugin

Command Options
---------------

The ``litestar assets init`` command accepts several options:

.. code-block:: text

    Usage: litestar assets init [OPTIONS]

    Options:
      --template TEXT     Framework template (react, vue, svelte, htmx, angular, etc.)
      --name TEXT         Project name
      --dest TEXT         Destination directory
      --no-install        Skip npm install
      --help              Show this message and exit

Examples
~~~~~~~~

Scaffold React project in a specific directory:

.. code-block:: bash

    litestar assets init --template react --dest ./frontend

Scaffold with custom project name:

.. code-block:: bash

    litestar assets init --template vue --name my-vue-app

Skip npm install (useful in CI):

.. code-block:: bash

    litestar assets init --template svelte --no-install

Generated Structure
-------------------

Each template generates a similar structure:

.. code-block:: text

    your-project/
    ├── package.json           # Dependencies and scripts
    ├── tsconfig.json          # TypeScript configuration
    ├── vite.config.ts         # Vite configuration
    ├── index.html             # Entry HTML (Vite-based)
    └── src/                   # Source files
        ├── main.ts            # Entry point
        ├── styles.css         # Global styles
        └── app/               # Framework-specific components
            └── ...

The exact structure varies by framework to follow each framework's conventions.

Customizing Templates
---------------------

After scaffolding, you can customize the generated files:

1. **Dependencies**: Edit ``package.json`` to add or remove packages
2. **Vite Config**: Modify ``vite.config.ts`` for custom plugins or settings
3. **TypeScript**: Adjust ``tsconfig.json`` for your needs
4. **Components**: Modify or replace the sample components

Adding TailwindCSS
~~~~~~~~~~~~~~~~~~

Most templates work well with TailwindCSS. After scaffolding:

.. code-block:: bash

    npm install -D tailwindcss postcss autoprefixer
    npx tailwindcss init -p

Then update your CSS entry point to include Tailwind directives.

Post-Scaffolding Steps
----------------------

After running the scaffold command:

1. **Install Dependencies** (if ``--no-install`` wasn't used):

   .. code-block:: bash

       npm install

2. **Start Development**:

   .. code-block:: bash

       npm run dev

3. **Configure Litestar**: Ensure your Litestar app is configured to use the VitePlugin
   with matching paths.

Example Litestar Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from pathlib import Path
    from litestar_vite import ViteConfig, VitePlugin
    from litestar_vite.config import PathConfig

    HERE = Path(__file__).parent

    vite = VitePlugin(
        config=ViteConfig(
            dev_mode=True,
            paths=PathConfig(
                bundle_dir=HERE / "public",
                resource_dir=HERE / "src",  # Or "resources" depending on template
                asset_url="/static/",
            ),
        )
    )

Troubleshooting
---------------

Common issues and solutions:

**"Template not found"**
    Ensure you're using a valid template name. Run ``litestar assets init --help`` to see available options.

**"Permission denied"**
    Ensure you have write access to the destination directory.

**"npm install failed"**
    Check your Node.js version (18+ recommended) and network connectivity.
    Try running ``npm install`` manually with ``--verbose`` for more details.

**"Vite dev server not connecting"**
    Ensure the ``assetUrl`` and ``bundleDir`` in your Vite config match your Litestar ViteConfig.

Next Steps
----------

After scaffolding your project:

- :doc:`getting-started` - Learn the basics if you're new
- :doc:`inertia-react` - Deep dive into Inertia.js with React
- :doc:`vue-integration` - Vue.js specific patterns
- :doc:`advanced-config` - Advanced Vite configuration

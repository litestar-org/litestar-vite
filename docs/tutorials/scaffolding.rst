======================
Project Scaffolding
======================

The Litestar Vite CLI provides a powerful scaffolding command to quickly generate new projects with your preferred frontend framework.

Overview
--------

The ``litestar assets init`` command creates a complete project structure including:

- Pre-configured Litestar application
- Vite configuration
- Frontend framework setup (React, Vue, Svelte, or HTMX)
- Example components and routes
- TypeScript configuration
- Ready-to-use development environment

Available Templates
-------------------

.. list-table::
   :widths: 20 30 50
   :header-rows: 1

   * - Template
     - Framework
     - Best For
   * - ``react``
     - React 18 + TypeScript
     - SPAs, complex UIs, large applications
   * - ``vue``
     - Vue 3 + TypeScript
     - Progressive enhancement, flexible apps
   * - ``svelte``
     - Svelte 5 + TypeScript
     - Performance-critical apps, small bundles
   * - ``htmx``
     - HTMX + Vanilla JS
     - Server-rendered apps with dynamic updates
   * - ``angular``
     - Angular 19 + Analog
     - Enterprise applications, full-featured framework

Quick Start
-----------

Run the scaffolding command:

.. code-block:: bash

    litestar assets init

You'll be prompted for:

1. **Project name**: The directory name for your new project
2. **Template choice**: Select from React, Vue, Svelte, HTMX, or Angular
3. **Confirmation**: Review and confirm your choices

Example Session
---------------

.. code-block:: text

    $ litestar assets init

    Welcome to Litestar Vite Project Generator!

    Project name: my-awesome-app

    Select a template:
    1. React
    2. Vue
    3. Svelte
    4. HTMX
    5. Angular

    Choice [1]: 1

    Creating project 'my-awesome-app' with React template...
    ✓ Project structure created
    ✓ Dependencies configured
    ✓ Git repository initialized

    Next steps:
      cd my-awesome-app
      npm install
      npm run dev        # Start Vite dev server
      litestar run       # In another terminal

Template-Specific Features
---------------------------

React Template
~~~~~~~~~~~~~~

**Includes:**

- React 18 with TypeScript
- React Router (optional with Inertia)
- Example components and pages
- CSS modules setup
- Development and production configurations

**Project Structure:**

.. code-block:: text

    my-app/
    ├── app.py                 # Litestar application
    ├── templates/
    │   └── index.html
    ├── resources/             # Frontend source
    │   ├── App.tsx
    │   ├── main.tsx
    │   └── components/
    ├── public/                # Built assets
    ├── vite.config.ts
    ├── tsconfig.json
    └── package.json

**Running the React Template:**

.. code-block:: bash

    cd my-app
    npm install

    # Terminal 1
    npm run dev

    # Terminal 2
    litestar run --reload

Vue Template
~~~~~~~~~~~~

**Includes:**

- Vue 3 with Composition API
- TypeScript support
- Single File Components (SFCs)
- Vue Router (optional with Inertia)

**Key Files:**

.. code-block:: text

    my-app/
    ├── resources/
    │   ├── App.vue            # Root component
    │   ├── main.ts            # Vue app initialization
    │   └── components/
    │       └── HelloWorld.vue

Svelte Template
~~~~~~~~~~~~~~~

**Includes:**

- Svelte 5 with runes
- TypeScript support
- SvelteKit-compatible structure
- Minimal bundle size

**Key Features:**

- Fast HMR
- Component-scoped styles
- Reactive statements
- Small production bundles

HTMX Template
~~~~~~~~~~~~~

**Includes:**

- HTMX for dynamic updates
- Minimal JavaScript
- Server-rendered templates
- Progressive enhancement

**Ideal For:**

- Traditional server-rendered apps
- Projects prioritizing simplicity
- Progressive enhancement approach

Angular Template
~~~~~~~~~~~~~~~~

**Includes:**

- Angular 19 with Analog
- TypeScript and SSR support
- Vite-powered development
- Full Angular CLI features

**Note:** Uses Angular CLI for development server by default.

Customizing Generated Projects
-------------------------------

After scaffolding, you can customize your project:

Modify Vite Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

Edit ``vite.config.ts`` to add plugins or change settings:

.. code-block:: typescript
    :caption: vite.config.ts

    import { defineConfig } from 'vite';
    import litestar from '@litestar/vite-plugin';
    import react from '@vitejs/plugin-react';  // For React template

    export default defineConfig({
      plugins: [
        litestar({
          input: 'resources/main.tsx',
          bundleDirectory: 'public',
        }),
        react(),
      ],
      server: {
        port: 5173,
        open: false,  // Don't auto-open browser
      },
    });

Update Litestar Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Modify ``app.py`` to add routes, middleware, or plugins:

.. code-block:: python
    :caption: app.py

    from pathlib import Path
    from litestar import Litestar, get
    from litestar.response import Template
    from litestar_vite import ViteConfig, VitePlugin

    @get("/")
    def index() -> Template:
        return Template(template_name="index.html")

    @get("/about")
    def about() -> Template:
        return Template(template_name="about.html")

    vite = VitePlugin(
        config=ViteConfig(
            bundle_dir=Path("public"),
            resource_dir=Path("resources"),
            hot_reload=True,
        )
    )

    app = Litestar(
        route_handlers=[index, about],
        plugins=[vite],
    )

Add Dependencies
~~~~~~~~~~~~~~~~

Install additional packages as needed:

.. code-block:: bash

    # Python dependencies
    uv add sqlalchemy alembic

    # Node.js dependencies
    npm install axios react-query

Managing Multiple Projects
---------------------------

You can scaffold multiple projects with different templates:

.. code-block:: bash

    litestar assets init  # Create first project
    cd ..
    litestar assets init  # Create another project

Each project is independent with its own dependencies and configuration.

Best Practices
--------------

1. **Keep templates directory clean**: Only Jinja templates in ``templates/``
2. **Organize resources**: Use subdirectories in ``resources/`` for components, styles, etc.
3. **Version control**: The generated ``.gitignore`` is pre-configured for Python and Node.js
4. **Development workflow**: Always run both Vite dev server and Litestar during development

Common Issues
-------------

**Scaffolding fails:**

Ensure you have write permissions in the current directory.

**Dependencies not installing:**

Run ``npm install`` manually after scaffolding.

**Port conflicts:**

Change the Vite port in ``vite.config.ts`` if port 5173 is in use.

Next Steps
----------

After scaffolding your project:

- Explore :doc:`getting-started` for a detailed walkthrough
- Learn :doc:`inertia-react` for SPA development
- Check :doc:`advanced-config` for optimization tips

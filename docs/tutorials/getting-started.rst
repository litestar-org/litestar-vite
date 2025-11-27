====================================
Getting Started with Vite + Litestar
====================================

This tutorial will guide you through creating your first Litestar application with Vite integration from scratch.

Prerequisites
-------------

Before starting, ensure you have:

- Python 3.9 or higher
- Node.js 18 or higher
- A text editor or IDE

Installation
------------

First, install Litestar Vite:

.. tab-set::

    .. tab-item:: pip

        .. code-block:: bash

            pip install litestar-vite litestar[jinja]

    .. tab-item:: uv

        .. code-block:: bash

            uv add litestar-vite "litestar[jinja]"

Step 1: Project Setup
---------------------

Create a new directory for your project:

.. code-block:: bash

    mkdir my-litestar-app
    cd my-litestar-app

Create the following directory structure:

.. code-block:: text

    my-litestar-app/
    ├── app.py
    ├── templates/
    │   └── index.html
    ├── resources/
    │   └── main.ts
    └── public/

Step 2: Create Your Litestar Application
-----------------------------------------

Create ``app.py`` with the following content:

.. code-block:: python
    :caption: app.py

    from pathlib import Path
    from litestar import Litestar, get
    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.response import Template
    from litestar.template.config import TemplateConfig
    from litestar_vite import ViteConfig, VitePlugin

    @get("/", sync_to_thread=False)
    def index() -> Template:
        return Template(template_name="index.html")

    vite = VitePlugin(
        config=ViteConfig(
            bundle_dir=Path("public"),
            resource_dir=Path("resources"),
            hot_reload=True,
        )
    )

    app = Litestar(
        route_handlers=[index],
        plugins=[vite],
        template_config=TemplateConfig(
            directory=Path("templates"),
            engine=JinjaTemplateEngine,
        ),
    )

Step 3: Create Your Template
-----------------------------

Create ``templates/index.html``:

.. code-block:: jinja
    :caption: templates/index.html

    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>My Litestar Vite App</title>
        {{ vite_hmr() }}
        {{ vite('resources/main.ts') }}
    </head>
    <body>
        <div id="app"></div>
    </body>
    </html>

**Template Tags Explained:**

- ``{{ vite_hmr() }}`` - Injects the HMR client in development mode
- ``{{ vite('resources/main.ts') }}`` - Loads your TypeScript entry point

Step 4: Create Your Frontend Code
----------------------------------

Create ``resources/main.ts``:

.. code-block:: typescript
    :caption: resources/main.ts

    // Create a simple counter app
    const app = document.getElementById('app');

    if (app) {
      let count = 0;

      app.innerHTML = `
        <div style="text-align: center; padding: 2rem; font-family: sans-serif;">
          <h1>Welcome to Litestar + Vite!</h1>
          <p>Count: <strong id="count">${count}</strong></p>
          <button id="increment">Increment</button>
        </div>
      `;

      const button = document.getElementById('increment');
      const countEl = document.getElementById('count');

      button?.addEventListener('click', () => {
        count++;
        if (countEl) countEl.textContent = String(count);
      });
    }

Step 5: Configure Vite
-----------------------

Create ``vite.config.ts`` in your project root:

.. code-block:: typescript
    :caption: vite.config.ts

    import { defineConfig } from 'vite';
    import litestar from '@litestar/vite-plugin';

    export default defineConfig({
      plugins: [
        litestar({
          input: 'resources/main.ts',
          bundleDirectory: 'public',
          resourceDirectory: 'resources',
        }),
      ],
    });

Create ``package.json``:

.. code-block:: json
    :caption: package.json

    {
      "name": "my-litestar-app",
      "private": true,
      "type": "module",
      "scripts": {
        "dev": "vite",
        "build": "vite build"
      },
      "devDependencies": {
        "@litestar/vite-plugin": "latest",
        "typescript": "^5.0.0",
        "vite": "^6.0.0"
      }
    }

Install Node.js dependencies:

.. code-block:: bash

    npm install

Step 6: Run Your Application
-----------------------------

**Development Mode:**

Start both the Litestar server and Vite dev server:

.. code-block:: bash

    # Terminal 1: Start Vite dev server
    npm run dev

    # Terminal 2: Start Litestar server
    litestar run --reload

Visit http://localhost:8000 and you should see your application running!

**Try Hot Module Replacement:**

1. Keep the browser open at http://localhost:8000
2. Edit ``resources/main.ts`` and change the heading text
3. Save the file
4. Watch the browser update instantly without a full reload!

Step 7: Build for Production
-----------------------------

When you're ready to deploy:

.. code-block:: bash

    # Build your frontend assets
    npm run build

    # Run Litestar in production mode
    litestar run --host 0.0.0.0 --port 8000

Vite will create optimized, versioned assets in the ``public/`` directory, and Litestar Vite will automatically serve them.

What's Next?
------------

Now that you have a basic Litestar + Vite application running:

- Try the :doc:`scaffolding` tutorial to quickly generate projects
- Learn about :doc:`inertia-react` for building SPAs
- Explore :doc:`advanced-config` for production optimization

Troubleshooting
---------------

**Port already in use:**

Change the Vite dev server port in ``vite.config.ts``:

.. code-block:: typescript

    export default defineConfig({
      server: {
        port: 5174,  // Change to any available port
      },
      // ... rest of config
    });

**Assets not loading:**

Ensure both Vite dev server and Litestar are running simultaneously in development mode.

**HMR not working:**

Check that ``hot_reload=True`` is set in your ``ViteConfig``.

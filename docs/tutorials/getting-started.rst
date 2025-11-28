===============
Getting Started
===============

This tutorial walks you through creating a basic Litestar application with Vite integration
from scratch. By the end, you'll have a working development setup with Hot Module Replacement (HMR).

Prerequisites
-------------

Before starting, ensure you have:

- Python 3.9 or higher
- Node.js 18 or higher
- A package manager (``pip``, ``uv``, ``pdm``, or ``poetry``)
- ``npm`` for frontend dependencies

Project Setup
-------------

1. Create Project Directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a new directory for your project:

.. code-block:: bash

    mkdir my-litestar-app
    cd my-litestar-app

2. Initialize Python Project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a virtual environment and install dependencies:

.. tab-set::

    .. tab-item:: uv

        .. code-block:: bash

            uv init
            uv add litestar litestar-vite jinja2

    .. tab-item:: pip

        .. code-block:: bash

            python -m venv .venv
            source .venv/bin/activate  # On Windows: .venv\Scripts\activate
            pip install litestar litestar-vite jinja2

3. Create the Application
~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``app.py`` with the following content:

.. code-block:: python
    :caption: app.py

    from pathlib import Path

    from litestar import Litestar, get
    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.response import Template
    from litestar.template.config import TemplateConfig

    from litestar_vite import ViteConfig, VitePlugin
    from litestar_vite.config import PathConfig

    HERE = Path(__file__).parent


    @get("/")
    async def index() -> Template:
        """Render the home page."""
        return Template(template_name="index.html")


    vite = VitePlugin(
        config=ViteConfig(
            dev_mode=True,
            paths=PathConfig(
                bundle_dir=HERE / "public",
                resource_dir=HERE / "resources",
                asset_url="/static/",
            ),
        )
    )

    app = Litestar(
        route_handlers=[index],
        plugins=[vite],
        template_config=TemplateConfig(
            directory=HERE / "templates",
            engine=JinjaTemplateEngine,
        ),
    )

4. Create Directory Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create the required directories:

.. code-block:: bash

    mkdir -p templates resources public

5. Create the HTML Template
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``templates/index.html``:

.. code-block:: jinja
    :caption: templates/index.html

    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>My Litestar App</title>
        {{ vite_hmr() }}
        {{ vite('resources/main.ts') }}
    </head>
    <body>
        <div id="app">
            <h1>Welcome to Litestar Vite!</h1>
            <p>Edit <code>resources/main.ts</code> to see HMR in action.</p>
        </div>
    </body>
    </html>

The template uses two Jinja2 functions provided by litestar-vite:

- ``vite_hmr()``: Injects the HMR client script during development
- ``vite('resources/main.ts')``: Includes your entry point with proper handling for dev/production

6. Initialize Frontend
~~~~~~~~~~~~~~~~~~~~~~

Create ``package.json``:

.. code-block:: json
    :caption: package.json

    {
      "name": "my-litestar-app",
      "version": "1.0.0",
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

Install dependencies:

.. code-block:: bash

    npm install

7. Configure Vite
~~~~~~~~~~~~~~~~~

Create ``vite.config.ts``:

.. code-block:: typescript
    :caption: vite.config.ts

    import { defineConfig } from "vite";
    import litestar from "@litestar/vite-plugin";

    export default defineConfig({
      plugins: [
        litestar({
          input: ["resources/main.ts"],
          assetUrl: "/static/",
          bundleDir: "public",
          resourceDir: "resources",
        }),
      ],
    });

8. Create Entry Point
~~~~~~~~~~~~~~~~~~~~~

Create ``resources/main.ts``:

.. code-block:: typescript
    :caption: resources/main.ts

    import "./styles.css";

    console.log("Hello from Litestar Vite!");

    // This demonstrates HMR - change this message and see it update instantly!
    const app = document.getElementById("app");
    if (app) {
      const p = document.createElement("p");
      p.textContent = "JavaScript is working!";
      app.appendChild(p);
    }

Create ``resources/styles.css``:

.. code-block:: css
    :caption: resources/styles.css

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      max-width: 800px;
      margin: 0 auto;
      padding: 2rem;
      background: #f5f5f5;
    }

    h1 {
      color: #1976d2;
    }

    code {
      background: #e3e3e3;
      padding: 0.2em 0.4em;
      border-radius: 4px;
    }

Running the Application
-----------------------

You need to run both the Litestar backend and Vite dev server:

1. Start Vite Dev Server
~~~~~~~~~~~~~~~~~~~~~~~~

In one terminal:

.. code-block:: bash

    npm run dev

This starts Vite on port 5173 (default).

2. Start Litestar
~~~~~~~~~~~~~~~~~

In another terminal:

.. code-block:: bash

    litestar run --reload

Visit http://localhost:8000 to see your application!

Testing HMR
-----------

With both servers running:

1. Open http://localhost:8000 in your browser
2. Open ``resources/main.ts`` in your editor
3. Change the message text
4. Save the file
5. Watch the browser update instantly without a full page reload!

Production Build
----------------

When you're ready to deploy:

1. Build the frontend assets:

   .. code-block:: bash

       npm run build

2. Update ``app.py`` to disable dev mode:

   .. code-block:: python

       vite = VitePlugin(
           config=ViteConfig(
               dev_mode=False,  # Changed from True
               paths=PathConfig(
                   bundle_dir=HERE / "public",
                   resource_dir=HERE / "resources",
                   asset_url="/static/",
               ),
           )
       )

3. Run Litestar (Vite dev server not needed):

   .. code-block:: bash

       litestar run

The built assets will be served from ``public/`` with proper cache headers.

Project Structure
-----------------

Your final project structure should look like:

.. code-block:: text

    my-litestar-app/
    ├── app.py                 # Litestar application
    ├── package.json           # Node.js dependencies
    ├── vite.config.ts         # Vite configuration
    ├── public/                # Built assets (production)
    │   └── manifest.json      # Asset manifest
    ├── resources/             # Source files
    │   ├── main.ts
    │   └── styles.css
    └── templates/             # Jinja2 templates
        └── index.html

Next Steps
----------

Now that you have a basic setup working, explore these topics:

- :doc:`scaffolding` - Use the CLI to scaffold more complex projects
- :doc:`inertia-react` - Build a full SPA with Inertia.js
- :doc:`advanced-config` - Customize your Vite configuration
- :doc:`/usage/index` - Learn about all available features

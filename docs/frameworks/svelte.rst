======
Svelte
======

Svelte 5 integration with Litestar Vite for lightweight, reactive applications.

Quick Start
-----------

.. code-block:: bash

    litestar assets init --template svelte

This creates a Svelte 5 project with TypeScript support.

Project Structure
-----------------

.. code-block:: text

    my-app/
    ├── app.py              # Litestar backend
    ├── package.json
    ├── vite.config.ts
    ├── svelte.config.js
    ├── templates/
    │   └── index.html      # Jinja template
    └── src/
        ├── main.ts         # Entry point
        ├── App.svelte      # Root component
        └── style.css

Backend Setup
-------------

.. code-block:: python

    from pathlib import Path
    from litestar import Litestar, get
    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.response import Template
    from litestar.template.config import TemplateConfig
    from litestar_vite import ViteConfig, VitePlugin
    from litestar_vite.config import PathConfig

    @get("/")
    async def index() -> Template:
        return Template(template_name="index.html")

    @get("/api/greeting")
    async def greeting() -> dict:
        return {"text": "Hello from Litestar!"}

    vite = VitePlugin(config=ViteConfig(dev_mode=True))

    app = Litestar(
        plugins=[vite],
        route_handlers=[index, greeting],
        template_config=TemplateConfig(
            directory=Path("templates"),
            engine=JinjaTemplateEngine,
        ),
    )

Vite Configuration
------------------

.. code-block:: typescript

    import { defineConfig } from "vite";
    import { svelte } from "@sveltejs/vite-plugin-svelte";
    import litestar from "litestar-vite-plugin";

    export default defineConfig({
      plugins: [
        svelte(),
        litestar({ input: ["src/main.ts"], resourceDirectory: "src" }),
      ],
    });

Template
--------

.. code-block:: jinja

    <!DOCTYPE html>
    <html>
    <head>
        {{ vite_hmr() }}
        {{ vite('src/main.ts') }}
    </head>
    <body>
        <div id="app"></div>
    </body>
    </html>

Svelte Component
----------------

.. code-block:: html

    <script lang="ts">
      import { onMount } from "svelte";

      let greeting = $state("");

      onMount(async () => {
        const res = await fetch("/api/greeting");
        const data = await res.json();
        greeting = data.text;
      });
    </script>

    <main>
      <h1>Svelte + Litestar</h1>
      <p>{greeting}</p>
    </main>

    <style>
      main {
        text-align: center;
        padding: 2rem;
      }
    </style>

Running
-------

.. code-block:: bash

    # Recommended: Litestar starts and proxies Vite automatically
    litestar run --reload

    # Two-port setup (optional)
    litestar assets serve
    litestar run --reload

See Also
--------

- :doc:`inertia` - Svelte with Inertia.js for server-side routing
- `Example: svelte <https://github.com/litestar-org/litestar-vite/tree/main/examples/svelte>`_

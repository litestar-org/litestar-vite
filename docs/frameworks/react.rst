=====
React
=====

React integration with Litestar Vite provides a modern development experience with
Hot Module Replacement (HMR) and optimized production builds.

Quick Start
-----------

.. code-block:: bash

    litestar assets init --template react

This creates a React 18+ project with TypeScript support.

Project Structure
-----------------

.. code-block:: text

    my-app/
    ├── app.py              # Litestar backend
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── templates/
    │   └── index.html      # Jinja template
    └── src/
        ├── main.tsx        # Entry point
        ├── App.tsx         # Root component
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

    @get("/api/data")
    async def get_data() -> dict:
        return {"message": "Hello from Litestar!"}

    vite = VitePlugin(config=ViteConfig(dev_mode=True))

    app = Litestar(
        plugins=[vite],
        route_handlers=[index, get_data],
        template_config=TemplateConfig(
            directory=Path("templates"),
            engine=JinjaTemplateEngine,
        ),
    )

Vite Configuration
------------------

.. code-block:: typescript

    import { defineConfig } from "vite";
    import react from "@vitejs/plugin-react";
    import litestar from "litestar-vite-plugin";

    export default defineConfig({
      plugins: [
        react(),
        litestar({ input: ["src/main.tsx"], resourceDirectory: "src" }),
      ],
    });

Template
--------

.. code-block:: jinja

    <!DOCTYPE html>
    <html>
    <head>
        {{ vite_hmr() }}
        {{ vite('src/main.tsx') }}
    </head>
    <body>
        <div id="root"></div>
    </body>
    </html>

React Component
---------------

.. code-block:: tsx

    import { useState, useEffect } from "react";

    function App() {
      const [message, setMessage] = useState("");

      useEffect(() => {
        fetch("/api/data")
          .then((res) => res.json())
          .then((data) => setMessage(data.message));
      }, []);

      return (
        <div>
          <h1>React + Litestar</h1>
          <p>{message}</p>
        </div>
      );
    }

    export default App;

Running
-------

.. code-block:: bash

    # Recommended: one process; Litestar starts and proxies Vite for you
    litestar run --reload

    # Two-port setup (optional)
    litestar assets serve  # starts Vite dev server
    # and in another shell
    litestar run --reload  # backend only

See Also
--------

- :doc:`inertia` - React with Inertia.js for server-side routing
- `Example: spa-react <https://github.com/litestar-org/litestar-vite/tree/main/examples/spa-react>`_

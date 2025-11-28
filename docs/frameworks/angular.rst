=======
Angular
=======

Litestar Vite supports Angular in two ways: Vite-based (using AnalogJS) and Angular CLI.

Option 1: Vite-Based (Recommended)
----------------------------------

Uses ``@analogjs/vite-plugin-angular`` for fast HMR and unified tooling.

.. code-block:: bash

    litestar assets init --template angular

Project Structure
~~~~~~~~~~~~~~~~~

.. code-block:: text

    my-app/
    ├── app.py              # Litestar backend
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── index.html          # Vite entry
    └── src/
        ├── main.ts         # Angular bootstrap
        └── app/
            ├── app.component.ts
            ├── app.component.html
            └── app.config.ts

Backend Setup
~~~~~~~~~~~~~

.. code-block:: python

    from pathlib import Path
    from litestar import Litestar, get
    from litestar_vite import ViteConfig, VitePlugin
    from litestar_vite.config import PathConfig

    @get("/api/hello")
    async def hello() -> dict:
        return {"message": "Hello from Litestar!"}

    vite = VitePlugin(
        config=ViteConfig(
            dev_mode=True,
            paths=PathConfig(
                bundle_dir=Path("public"),
                resource_dir=Path("src"),
            ),
        ),
    )

    app = Litestar(
        plugins=[vite],
        route_handlers=[hello],
    )

Vite Configuration
~~~~~~~~~~~~~~~~~~

.. code-block:: typescript

    import { defineConfig } from "vite";
    import analog from "@analogjs/vite-plugin-angular";
    import litestar from "@litestar/vite-plugin";

    export default defineConfig({
      plugins: [
        analog(),
        litestar({
          input: ["src/main.ts"],
          assetUrl: "/static/",
          bundleDir: "public",
          resourceDir: "src",
        }),
      ],
    });

Angular Component
~~~~~~~~~~~~~~~~~

.. code-block:: typescript

    import { Component, OnInit, inject } from "@angular/core";
    import { HttpClient } from "@angular/common/http";

    @Component({
      selector: "app-root",
      standalone: true,
      template: `
        <h1>Angular + Litestar</h1>
        <p>{{ message }}</p>
      `,
    })
    export class AppComponent implements OnInit {
      private http = inject(HttpClient);
      message = "";

      ngOnInit() {
        this.http.get<{message: string}>("/api/hello")
          .subscribe(res => this.message = res.message);
      }
    }

Option 2: Angular CLI
---------------------

Standard Angular CLI workflow with proxy to Litestar.

.. code-block:: bash

    litestar assets init --template angular-cli

This creates a standard Angular project that:

- Uses ``ng serve`` for development
- Proxies API requests to Litestar via ``proxy.conf.json``
- Builds to ``dist/browser/`` for production

Proxy Configuration
~~~~~~~~~~~~~~~~~~~

.. code-block:: json

    {
      "/api": {
        "target": "http://localhost:8000",
        "secure": false
      }
    }

Running Angular CLI
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Terminal 1: Litestar backend
    litestar run --reload

    # Terminal 2: Angular dev server
    npm start

Access at http://localhost:4200 (Angular proxies API calls to Litestar).

Comparison
----------

.. list-table::
   :widths: 30 35 35
   :header-rows: 1

   * - Aspect
     - Vite (Analog)
     - Angular CLI
   * - Build Tool
     - Vite
     - Webpack
   * - HMR Speed
     - Fast
     - Standard
   * - litestar-vite-plugin
     - Yes
     - No
   * - Type Generation
     - Enabled
     - Disabled
   * - Port
     - Single (8000)
     - Two (4200 + 8000)

See Also
--------

- `Example: angular <https://github.com/litestar-org/litestar-vite/tree/main/examples/angular>`_
- `Example: angular-cli <https://github.com/litestar-org/litestar-vite/tree/main/examples/angular-cli>`_

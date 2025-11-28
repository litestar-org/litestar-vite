===
Vue
===

Vue 3 integration with Litestar Vite using the Composition API and Single File Components.

Quick Start
-----------

.. code-block:: bash

    litestar assets init --template vue

This creates a Vue 3 project with TypeScript support.

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
        ├── main.ts         # Entry point
        ├── App.vue         # Root component
        ├── style.css
        └── components/
            └── Counter.vue

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

    @get("/api/users")
    async def get_users() -> dict:
        return {
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ]
        }

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
        route_handlers=[index, get_users],
        template_config=TemplateConfig(
            directory=Path("templates"),
            engine=JinjaTemplateEngine,
        ),
    )

Vite Configuration
------------------

.. code-block:: typescript

    import { defineConfig } from "vite";
    import vue from "@vitejs/plugin-vue";
    import litestar from "@litestar/vite-plugin";

    export default defineConfig({
      plugins: [
        vue(),
        litestar({
          input: ["src/main.ts"],
          assetUrl: "/static/",
          bundleDir: "public",
          resourceDir: "src",
        }),
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

Vue Component
-------------

.. code-block:: vue

    <script setup lang="ts">
    import { ref, onMounted } from "vue";

    interface User {
      id: number;
      name: string;
    }

    const users = ref<User[]>([]);

    onMounted(async () => {
      const res = await fetch("/api/users");
      const data = await res.json();
      users.value = data.users;
    });
    </script>

    <template>
      <div>
        <h1>Vue + Litestar</h1>
        <ul>
          <li v-for="user in users" :key="user.id">
            {{ user.name }}
          </li>
        </ul>
      </div>
    </template>

Running
-------

.. code-block:: bash

    # Terminal 1: Vite dev server
    npm run dev

    # Terminal 2: Litestar
    litestar run --reload

See Also
--------

- :doc:`inertia` - Vue with Inertia.js for server-side routing
- `Example: spa-vue <https://github.com/litestar-org/litestar-vite/tree/main/examples/spa-vue>`_
- `Example: spa-vue-inertia <https://github.com/litestar-org/litestar-vite/tree/main/examples/spa-vue-inertia>`_

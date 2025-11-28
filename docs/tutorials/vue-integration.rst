=================
Vue.js Integration
=================

This tutorial covers integrating Vue 3 with Litestar using the litestar-vite plugin.
Vue's Composition API and Single File Components (SFCs) work seamlessly with Vite.

Prerequisites
-------------

- Completed the :doc:`getting-started` tutorial or have a basic Litestar app
- Basic familiarity with Vue.js

Project Setup
-------------

1. Scaffold the Project
~~~~~~~~~~~~~~~~~~~~~~~

Use the CLI for a quick start:

.. code-block:: bash

    litestar assets init --template vue

Or install dependencies manually:

.. code-block:: bash

    npm install vue
    npm install -D @vitejs/plugin-vue

2. Configure Vite
~~~~~~~~~~~~~~~~~

Create or update ``vite.config.ts``:

.. code-block:: typescript
    :caption: vite.config.ts

    import { defineConfig } from "vite";
    import vue from "@vitejs/plugin-vue";
    import litestar from "@litestar/vite-plugin";

    export default defineConfig({
      plugins: [
        vue(),
        litestar({
          input: ["resources/main.ts"],
          assetUrl: "/static/",
          bundleDir: "public",
          resourceDir: "resources",
        }),
      ],
      resolve: {
        alias: {
          "@": "/resources",
        },
      },
    });

3. Configure Litestar
~~~~~~~~~~~~~~~~~~~~~

Create ``app.py``:

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
        """Render the main page."""
        return Template(template_name="index.html")


    @get("/api/users")
    async def get_users() -> list[dict]:
        """API endpoint for user data."""
        return [
            {"id": 1, "name": "Alice", "role": "Admin"},
            {"id": 2, "name": "Bob", "role": "User"},
            {"id": 3, "name": "Charlie", "role": "User"},
        ]


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
        route_handlers=[index, get_users],
        plugins=[vite],
        template_config=TemplateConfig(
            directory=HERE / "templates",
            engine=JinjaTemplateEngine,
        ),
    )

4. Create the HTML Template
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``templates/index.html``:

.. code-block:: jinja
    :caption: templates/index.html

    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Vue + Litestar</title>
        {{ vite_hmr() }}
        {{ vite('resources/main.ts') }}
    </head>
    <body>
        <div id="app"></div>
    </body>
    </html>

5. Create Vue Entry Point
~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``resources/main.ts``:

.. code-block:: typescript
    :caption: resources/main.ts

    import { createApp } from "vue";
    import App from "./App.vue";
    import "./styles.css";

    createApp(App).mount("#app");

6. Create the Root Component
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``resources/App.vue``:

.. code-block:: vue
    :caption: resources/App.vue

    <script setup lang="ts">
    import { ref, onMounted } from "vue";
    import UserList from "./components/UserList.vue";
    import Counter from "./components/Counter.vue";

    interface User {
      id: number;
      name: string;
      role: string;
    }

    const users = ref<User[]>([]);
    const loading = ref(true);
    const error = ref<string | null>(null);

    onMounted(async () => {
      try {
        const response = await fetch("/api/users");
        users.value = await response.json();
      } catch (e) {
        error.value = "Failed to load users";
      } finally {
        loading.value = false;
      }
    });
    </script>

    <template>
      <div class="app">
        <header>
          <h1>Vue + Litestar Vite</h1>
        </header>

        <main>
          <section class="card">
            <h2>Interactive Counter</h2>
            <Counter />
          </section>

          <section class="card">
            <h2>Users from API</h2>
            <p v-if="loading">Loading...</p>
            <p v-else-if="error" class="error">{{ error }}</p>
            <UserList v-else :users="users" />
          </section>
        </main>

        <footer>
          <p>Built with Vue 3 + Litestar</p>
        </footer>
      </div>
    </template>

    <style scoped>
    .app {
      max-width: 800px;
      margin: 0 auto;
      padding: 2rem;
    }

    header {
      text-align: center;
      margin-bottom: 2rem;
    }

    h1 {
      color: #42b883;
    }

    .card {
      background: white;
      border-radius: 8px;
      padding: 1.5rem;
      margin-bottom: 1rem;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    h2 {
      color: #333;
      margin-top: 0;
    }

    footer {
      text-align: center;
      color: #666;
      margin-top: 2rem;
    }

    .error {
      color: #e74c3c;
    }
    </style>

7. Create Vue Components
~~~~~~~~~~~~~~~~~~~~~~~~

Create ``resources/components/Counter.vue``:

.. code-block:: vue
    :caption: resources/components/Counter.vue

    <script setup lang="ts">
    import { ref } from "vue";

    const count = ref(0);

    function increment() {
      count.value++;
    }

    function decrement() {
      count.value--;
    }
    </script>

    <template>
      <div class="counter">
        <button @click="decrement" :disabled="count <= 0">-</button>
        <span class="count">{{ count }}</span>
        <button @click="increment">+</button>
      </div>
    </template>

    <style scoped>
    .counter {
      display: flex;
      align-items: center;
      gap: 1rem;
      justify-content: center;
    }

    button {
      padding: 0.5rem 1rem;
      font-size: 1.25rem;
      border: none;
      border-radius: 4px;
      background: #42b883;
      color: white;
      cursor: pointer;
      transition: background 0.2s;
    }

    button:hover:not(:disabled) {
      background: #3aa876;
    }

    button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .count {
      font-size: 2rem;
      font-weight: bold;
      min-width: 3rem;
      text-align: center;
    }
    </style>

Create ``resources/components/UserList.vue``:

.. code-block:: vue
    :caption: resources/components/UserList.vue

    <script setup lang="ts">
    interface User {
      id: number;
      name: string;
      role: string;
    }

    defineProps<{
      users: User[];
    }>();
    </script>

    <template>
      <ul class="user-list">
        <li v-for="user in users" :key="user.id" class="user-item">
          <span class="user-name">{{ user.name }}</span>
          <span class="user-role" :class="user.role.toLowerCase()">
            {{ user.role }}
          </span>
        </li>
      </ul>
    </template>

    <style scoped>
    .user-list {
      list-style: none;
      padding: 0;
      margin: 0;
    }

    .user-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.75rem;
      background: #f9f9f9;
      border-radius: 4px;
      margin-bottom: 0.5rem;
    }

    .user-name {
      font-weight: 500;
    }

    .user-role {
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.875rem;
    }

    .user-role.admin {
      background: #e74c3c;
      color: white;
    }

    .user-role.user {
      background: #3498db;
      color: white;
    }
    </style>

8. Add Global Styles
~~~~~~~~~~~~~~~~~~~~

Create ``resources/styles.css``:

.. code-block:: css
    :caption: resources/styles.css

    * {
      box-sizing: border-box;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      margin: 0;
      background: #f0f2f5;
      color: #333;
    }

TypeScript Configuration
------------------------

For proper Vue + TypeScript support, create ``tsconfig.json``:

.. code-block:: json
    :caption: tsconfig.json

    {
      "compilerOptions": {
        "target": "ES2020",
        "useDefineForClassFields": true,
        "module": "ESNext",
        "lib": ["ES2020", "DOM", "DOM.Iterable"],
        "skipLibCheck": true,
        "moduleResolution": "bundler",
        "allowImportingTsExtensions": true,
        "resolveJsonModule": true,
        "isolatedModules": true,
        "noEmit": true,
        "jsx": "preserve",
        "strict": true,
        "noUnusedLocals": true,
        "noUnusedParameters": true,
        "noFallthroughCasesInSwitch": true,
        "paths": {
          "@/*": ["./resources/*"]
        }
      },
      "include": ["resources/**/*.ts", "resources/**/*.vue"],
      "references": [{ "path": "./tsconfig.node.json" }]
    }

And ``tsconfig.node.json``:

.. code-block:: json
    :caption: tsconfig.node.json

    {
      "compilerOptions": {
        "composite": true,
        "skipLibCheck": true,
        "module": "ESNext",
        "moduleResolution": "bundler",
        "allowSyntheticDefaultImports": true
      },
      "include": ["vite.config.ts"]
    }

Running the Application
-----------------------

Start both servers:

.. code-block:: bash

    # Terminal 1
    npm run dev

    # Terminal 2
    litestar run --reload

Visit http://localhost:8000 to see your Vue application!

Vue with Inertia.js
-------------------

For server-side routing with Vue, use the Vue + Inertia template:

.. code-block:: bash

    litestar assets init --template vue-inertia

This provides:

- Server-side routing (no Vue Router needed)
- Seamless data passing from Litestar to Vue
- Full SPA experience with SEO-friendly URLs

Key differences from the basic Vue setup:

1. Uses ``InertiaResponse`` instead of ``Template``
2. Inertia handles component loading and transitions
3. Data is passed as props from the server

See :doc:`inertia-react` for Inertia concepts (they apply to Vue as well).

State Management
----------------

For larger applications, consider adding Pinia for state management:

.. code-block:: bash

    npm install pinia

.. code-block:: typescript
    :caption: resources/main.ts

    import { createApp } from "vue";
    import { createPinia } from "pinia";
    import App from "./App.vue";

    const app = createApp(App);
    app.use(createPinia());
    app.mount("#app");

Next Steps
----------

- :doc:`inertia-react` - Learn Inertia.js patterns (applicable to Vue)
- :doc:`advanced-config` - Advanced Vite configuration
- :doc:`/usage/index` - Complete usage guide
- `Vue 3 Documentation <https://vuejs.org/>`_ - Official Vue docs

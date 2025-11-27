==================
Vue.js Integration
==================

Learn how to integrate Vue 3 with Litestar using the Vite plugin for a modern development experience.

Prerequisites
-------------

- Completed :doc:`getting-started` tutorial
- Basic knowledge of Vue 3 and Composition API
- Understanding of Single File Components (SFCs)

Installation
------------

Install Vue and related dependencies:

.. code-block:: bash

    # Python
    uv add litestar-vite "litestar[jinja]"

    # Node.js
    npm install vue
    npm install -D @vitejs/plugin-vue @vue/tsconfig typescript

Project Setup
-------------

Create the following structure:

.. code-block:: text

    my-vue-app/
    ├── app.py
    ├── templates/
    │   └── index.html
    ├── resources/
    │   ├── main.ts
    │   ├── App.vue
    │   ├── components/
    │   │   ├── Counter.vue
    │   │   └── UserCard.vue
    │   └── composables/
    │       └── useCounter.ts
    ├── vite.config.ts
    ├── tsconfig.json
    └── package.json

Step 1: Configure Litestar
---------------------------

Create ``app.py``:

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
        return Template(
            template_name="index.html",
            context={"page_title": "Vue + Litestar"},
        )

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

Step 2: Create the Template
----------------------------

Create ``templates/index.html``:

.. code-block:: jinja
    :caption: templates/index.html

    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ page_title }}</title>
        {{ vite_hmr() }}
        {{ vite('resources/main.ts') }}
    </head>
    <body>
        <div id="app"></div>
    </body>
    </html>

Step 3: Configure Vite for Vue
-------------------------------

Create ``vite.config.ts``:

.. code-block:: typescript
    :caption: vite.config.ts

    import { defineConfig } from 'vite';
    import vue from '@vitejs/plugin-vue';
    import litestar from '@litestar/vite-plugin';

    export default defineConfig({
      plugins: [
        litestar({
          input: 'resources/main.ts',
          bundleDirectory: 'public',
          resourceDirectory: 'resources',
        }),
        vue(),
      ],
      resolve: {
        alias: {
          '@': '/resources',
        },
      },
    });

Create ``tsconfig.json``:

.. code-block:: json
    :caption: tsconfig.json

    {
      "extends": "@vue/tsconfig/tsconfig.dom.json",
      "compilerOptions": {
        "baseUrl": ".",
        "paths": {
          "@/*": ["./resources/*"]
        },
        "types": ["vite/client"]
      },
      "include": ["resources/**/*.ts", "resources/**/*.vue"],
      "exclude": ["node_modules"]
    }

Step 4: Initialize Vue Application
-----------------------------------

Create ``resources/main.ts``:

.. code-block:: typescript
    :caption: resources/main.ts

    import { createApp } from 'vue';
    import App from './App.vue';

    const app = createApp(App);
    app.mount('#app');

Step 5: Create Root Component
------------------------------

Create ``resources/App.vue``:

.. code-block:: vue
    :caption: resources/App.vue

    <script setup lang="ts">
    import { ref } from 'vue';
    import Counter from './components/Counter.vue';
    import UserCard from './components/UserCard.vue';

    const user = ref({
      name: 'John Doe',
      email: 'john@example.com',
      avatar: 'https://i.pravatar.cc/150?img=1',
    });
    </script>

    <template>
      <div class="app">
        <header>
          <h1>Vue + Litestar</h1>
          <p>Modern frontend development with Vite</p>
        </header>

        <main>
          <section class="demo-section">
            <h2>Counter Demo</h2>
            <Counter :initial-value="0" />
          </section>

          <section class="demo-section">
            <h2>User Profile</h2>
            <UserCard :user="user" />
          </section>
        </main>
      </div>
    </template>

    <style scoped>
    .app {
      font-family: system-ui, -apple-system, sans-serif;
      max-width: 800px;
      margin: 0 auto;
      padding: 2rem;
    }

    header {
      text-align: center;
      margin-bottom: 3rem;
    }

    h1 {
      color: #f50057;
      font-size: 2.5rem;
      margin: 0;
    }

    .demo-section {
      margin-bottom: 2rem;
      padding: 1.5rem;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
    }

    h2 {
      margin-top: 0;
      color: #333;
    }
    </style>

Step 6: Create Vue Components
------------------------------

Create ``resources/components/Counter.vue``:

.. code-block:: vue
    :caption: resources/components/Counter.vue

    <script setup lang="ts">
    import { ref } from 'vue';

    interface Props {
      initialValue?: number;
    }

    const props = withDefaults(defineProps<Props>(), {
      initialValue: 0,
    });

    const count = ref(props.initialValue);

    function increment() {
      count.value++;
    }

    function decrement() {
      count.value--;
    }

    function reset() {
      count.value = props.initialValue;
    }
    </script>

    <template>
      <div class="counter">
        <div class="count-display">{{ count }}</div>
        <div class="controls">
          <button @click="decrement">-</button>
          <button @click="reset">Reset</button>
          <button @click="increment">+</button>
        </div>
      </div>
    </template>

    <style scoped>
    .counter {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1rem;
    }

    .count-display {
      font-size: 3rem;
      font-weight: bold;
      color: #f50057;
    }

    .controls {
      display: flex;
      gap: 0.5rem;
    }

    button {
      padding: 0.5rem 1rem;
      font-size: 1rem;
      border: none;
      background: #f50057;
      color: white;
      cursor: pointer;
      border-radius: 4px;
      transition: background 0.2s;
    }

    button:hover {
      background: #c51162;
    }
    </style>

Create ``resources/components/UserCard.vue``:

.. code-block:: vue
    :caption: resources/components/UserCard.vue

    <script setup lang="ts">
    interface User {
      name: string;
      email: string;
      avatar: string;
    }

    interface Props {
      user: User;
    }

    defineProps<Props>();
    </script>

    <template>
      <div class="user-card">
        <img :src="user.avatar" :alt="user.name" class="avatar" />
        <div class="info">
          <h3>{{ user.name }}</h3>
          <p>{{ user.email }}</p>
        </div>
      </div>
    </template>

    <style scoped>
    .user-card {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 1rem;
      background: #f5f5f5;
      border-radius: 8px;
    }

    .avatar {
      width: 64px;
      height: 64px;
      border-radius: 50%;
    }

    .info h3 {
      margin: 0;
      color: #333;
    }

    .info p {
      margin: 0.25rem 0 0;
      color: #666;
    }
    </style>

Step 7: Create a Composable
----------------------------

Vue composables are reusable stateful logic. Create ``resources/composables/useCounter.ts``:

.. code-block:: typescript
    :caption: resources/composables/useCounter.ts

    import { ref, computed } from 'vue';

    export function useCounter(initialValue = 0) {
      const count = ref(initialValue);

      const doubled = computed(() => count.value * 2);

      function increment() {
        count.value++;
      }

      function decrement() {
        count.value--;
      }

      function reset() {
        count.value = initialValue;
      }

      return {
        count,
        doubled,
        increment,
        decrement,
        reset,
      };
    }

Use it in a component:

.. code-block:: vue

    <script setup lang="ts">
    import { useCounter } from '@/composables/useCounter';

    const { count, doubled, increment, decrement, reset } = useCounter(10);
    </script>

    <template>
      <div>
        <p>Count: {{ count }}</p>
        <p>Doubled: {{ doubled }}</p>
        <button @click="increment">+</button>
      </div>
    </template>

Step 8: Run Your Application
-----------------------------

.. code-block:: bash

    # Terminal 1: Vite dev server
    npm run dev

    # Terminal 2: Litestar server
    litestar run --reload

Visit http://localhost:8000 and test the application:

1. Click the counter buttons
2. Edit ``App.vue`` and watch it hot-reload instantly
3. Try changing styles in any component

Advanced Patterns
-----------------

State Management with Pinia
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For complex state, use Pinia:

.. code-block:: bash

    npm install pinia

.. code-block:: typescript
    :caption: resources/main.ts

    import { createApp } from 'vue';
    import { createPinia } from 'pinia';
    import App from './App.vue';

    const app = createApp(App);
    app.use(createPinia());
    app.mount('#app');

.. code-block:: typescript
    :caption: resources/stores/user.ts

    import { defineStore } from 'pinia';

    export const useUserStore = defineStore('user', {
      state: () => ({
        name: 'John Doe',
        email: 'john@example.com',
      }),
      actions: {
        updateName(name: string) {
          this.name = name;
        },
      },
    });

Fetching Data from Litestar
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create an API endpoint:

.. code-block:: python
    :caption: app.py

    from litestar import get

    @get("/api/users")
    async def get_users() -> list[dict]:
        return [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]

Fetch from Vue:

.. code-block:: vue

    <script setup lang="ts">
    import { ref, onMounted } from 'vue';

    interface User {
      id: number;
      name: string;
    }

    const users = ref<User[]>([]);

    onMounted(async () => {
      const response = await fetch('/api/users');
      users.value = await response.json();
    });
    </script>

    <template>
      <ul>
        <li v-for="user in users" :key="user.id">
          {{ user.name }}
        </li>
      </ul>
    </template>

Vue Router Integration
~~~~~~~~~~~~~~~~~~~~~~

For client-side routing:

.. code-block:: bash

    npm install vue-router

.. code-block:: typescript
    :caption: resources/router.ts

    import { createRouter, createWebHistory } from 'vue-router';
    import Home from './pages/Home.vue';
    import About from './pages/About.vue';

    export const router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: Home },
        { path: '/about', component: About },
      ],
    });

Next Steps
----------

- Learn :doc:`advanced-config` for optimization
- Check out `Vue.js documentation <https://vuejs.org/>`_
- Explore :doc:`inertia-react` for an alternative SPA approach

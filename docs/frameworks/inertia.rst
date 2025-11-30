==========
Inertia.js
==========

Inertia.js lets you build modern SPAs with server-side routing. No API layer needed -
your Litestar routes return page components directly.

Supported Frameworks
--------------------

- React: ``litestar assets init --template react-inertia``
- Vue: ``litestar assets init --template vue-inertia``
- Svelte: ``litestar assets init --template svelte-inertia``

How It Works
------------

1. Server returns ``InertiaResponse`` with component name and props
2. Inertia renders the component client-side
3. Navigation uses XHR, updating only the page component
4. Full SPA experience with server-side routing

Backend Setup
-------------

.. code-block:: python

    from pathlib import Path
    from litestar import Litestar, get
    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.template.config import TemplateConfig
    from litestar_vite import ViteConfig, VitePlugin
    from litestar_vite.config import PathConfig
    from litestar_vite.inertia import InertiaConfig, InertiaPlugin, InertiaResponse

    @get("/")
    async def home() -> InertiaResponse:
        return InertiaResponse(
            component="Home",
            props={"message": "Welcome!"},
        )

    @get("/users")
    async def users() -> InertiaResponse:
        return InertiaResponse(
            component="Users",
            props={
                "users": [
                    {"id": 1, "name": "Alice"},
                    {"id": 2, "name": "Bob"},
                ]
            },
        )

    vite = VitePlugin(
        config=ViteConfig(
            dev_mode=True,
            paths=PathConfig(
                bundle_dir=Path("public"),
                resource_dir=Path("resources"),  # Inertia uses resources/
            ),
        ),
    )

    inertia = InertiaPlugin(
        config=InertiaConfig(root_template="index.html")
    )

    app = Litestar(
        plugins=[vite, inertia],
        route_handlers=[home, users],
        template_config=TemplateConfig(
            directory=Path("templates"),
            engine=JinjaTemplateEngine,
        ),
    )

Root Template
-------------

.. code-block:: jinja

    <!DOCTYPE html>
    <html>
    <head>
        {{ vite_hmr() }}
        {{ vite('resources/main.tsx') }}
    </head>
    <body>
        {{ inertia_body() }}
    </body>
    </html>

React Example
-------------

**Entry Point (resources/main.tsx)**:

.. code-block:: tsx

    import { createInertiaApp } from "@inertiajs/react";
    import { createRoot } from "react-dom/client";

    const pages = import.meta.glob("./pages/**/*.tsx", { eager: true });

    createInertiaApp({
      resolve: (name) => pages[`./pages/${name}.tsx`],
      setup({ el, App, props }) {
        createRoot(el).render(<App {...props} />);
      },
    });

**Page Component (resources/pages/Home.tsx)**:

.. code-block:: tsx

    import { Link } from "@inertiajs/react";

    interface Props {
      message: string;
    }

    export default function Home({ message }: Props) {
      return (
        <div>
          <h1>{message}</h1>
          <Link href="/users">View Users</Link>
        </div>
      );
    }

Vue Example
-----------

**Entry Point (resources/main.ts)**:

.. code-block:: typescript

    import { createInertiaApp } from "@inertiajs/vue3";
    import { createApp, h } from "vue";

    const pages = import.meta.glob("./pages/**/*.vue", { eager: true });

    createInertiaApp({
      resolve: (name) => pages[`./pages/${name}.vue`],
      setup({ el, App, props, plugin }) {
        createApp({ render: () => h(App, props) })
          .use(plugin)
          .mount(el);
      },
    });

**Page Component (resources/pages/Home.vue)**:

.. code-block:: vue

    <script setup lang="ts">
    import { Link } from "@inertiajs/vue3";

    defineProps<{
      message: string;
    }>();
    </script>

    <template>
      <div>
        <h1>{{ message }}</h1>
        <Link href="/users">View Users</Link>
      </div>
    </template>

Forms
-----

Inertia provides form helpers for handling submissions:

.. code-block:: tsx

    import { useForm } from "@inertiajs/react";

    function CreateUser() {
      const { data, setData, post, processing, errors } = useForm({
        name: "",
        email: "",
      });

      function submit(e: React.FormEvent) {
        e.preventDefault();
        post("/users");
      }

      return (
        <form onSubmit={submit}>
          <input
            value={data.name}
            onChange={(e) => setData("name", e.target.value)}
          />
          {errors.name && <span>{errors.name}</span>}
          <button disabled={processing}>Create</button>
        </form>
      );
    }

See Also
--------

- :doc:`/usage/inertia` - Full Inertia.js documentation
- `Example: inertia <https://github.com/litestar-org/litestar-vite/tree/main/examples/vue-inertia>`_
- `Example: vue-inertia <https://github.com/litestar-org/litestar-vite/tree/main/examples/vue-inertia>`_
- `Inertia.js Documentation <https://inertiajs.com/>`_

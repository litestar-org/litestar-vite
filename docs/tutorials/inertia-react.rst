======================
Inertia.js with React
======================

This tutorial shows how to build a modern single-page application using Inertia.js with React
and Litestar. Inertia.js lets you build SPAs with server-side routing, eliminating the need
for a separate API layer.

What is Inertia.js?
-------------------

Inertia.js is the glue between your server-side framework and client-side framework. It allows you to:

- Build fully client-rendered SPAs
- Use server-side routing (no client-side router needed)
- Share data between server and client seamlessly
- Maintain SEO-friendly URLs

Prerequisites
-------------

- Completed the :doc:`getting-started` tutorial or have a basic Litestar app
- Familiarity with React

Project Setup
-------------

1. Scaffold the Project
~~~~~~~~~~~~~~~~~~~~~~~

Use the CLI to create a React + Inertia project:

.. code-block:: bash

    litestar assets init --template react-inertia

Or manually install the dependencies:

.. code-block:: bash

    npm install @inertiajs/react react react-dom
    npm install -D @types/react @types/react-dom @vitejs/plugin-react

2. Configure Litestar
~~~~~~~~~~~~~~~~~~~~~

Create or update your ``app.py``:

.. code-block:: python
    :caption: app.py

    from pathlib import Path
    from typing import Any

    from litestar import Litestar, get
    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.template.config import TemplateConfig

    from litestar_vite import ViteConfig, VitePlugin
    from litestar_vite.config import PathConfig
    from litestar_vite.inertia import InertiaConfig, InertiaPlugin, InertiaResponse

    HERE = Path(__file__).parent


    @get("/")
    async def home() -> InertiaResponse:
        """Home page."""
        return InertiaResponse(
            component="Home",
            props={"message": "Welcome to Inertia.js!"},
        )


    @get("/about")
    async def about() -> InertiaResponse:
        """About page."""
        return InertiaResponse(
            component="About",
            props={
                "title": "About Us",
                "description": "Learn more about our application.",
            },
        )


    @get("/users")
    async def users() -> InertiaResponse:
        """Users list page."""
        # In a real app, this would come from a database
        users_data = [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
            {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
        ]
        return InertiaResponse(
            component="Users",
            props={"users": users_data},
        )


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

    inertia = InertiaPlugin(
        config=InertiaConfig(
            root_template="index.html",
        )
    )

    app = Litestar(
        route_handlers=[home, about, users],
        plugins=[vite, inertia],
        template_config=TemplateConfig(
            directory=HERE / "templates",
            engine=JinjaTemplateEngine,
        ),
    )

3. Create the Root Template
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``templates/index.html``:

.. code-block:: jinja
    :caption: templates/index.html

    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ page.props.title if page.props.title else "My App" }}</title>
        {{ vite_hmr() }}
        {{ vite('resources/main.tsx') }}
    </head>
    <body>
        {{ inertia_body() }}
    </body>
    </html>

The ``inertia_body()`` function renders the Inertia.js root element with initial page data.

4. Configure Vite
~~~~~~~~~~~~~~~~~

Update ``vite.config.ts``:

.. code-block:: typescript
    :caption: vite.config.ts

    import { defineConfig } from "vite";
    import react from "@vitejs/plugin-react";
    import litestar from "@litestar/vite-plugin";

    export default defineConfig({
      plugins: [
        react(),
        litestar({
          input: ["resources/main.tsx"],
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

5. Create the React Entry Point
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``resources/main.tsx``:

.. code-block:: tsx
    :caption: resources/main.tsx

    import { createInertiaApp } from "@inertiajs/react";
    import { createRoot } from "react-dom/client";
    import "./styles.css";

    // Import all page components
    const pages = import.meta.glob("./pages/**/*.tsx", { eager: true });

    createInertiaApp({
      resolve: (name) => {
        const page = pages[`./pages/${name}.tsx`];
        if (!page) {
          throw new Error(`Page not found: ${name}`);
        }
        return page;
      },
      setup({ el, App, props }) {
        createRoot(el).render(<App {...props} />);
      },
    });

6. Create Page Components
~~~~~~~~~~~~~~~~~~~~~~~~~

Create the page components in ``resources/pages/``:

**Home.tsx**:

.. code-block:: tsx
    :caption: resources/pages/Home.tsx

    import { Link } from "@inertiajs/react";
    import Layout from "../components/Layout";

    interface HomeProps {
      message: string;
    }

    export default function Home({ message }: HomeProps) {
      return (
        <Layout title="Home">
          <h1>Home</h1>
          <p>{message}</p>
          <nav>
            <Link href="/about">About</Link> |{" "}
            <Link href="/users">Users</Link>
          </nav>
        </Layout>
      );
    }

**About.tsx**:

.. code-block:: tsx
    :caption: resources/pages/About.tsx

    import { Link } from "@inertiajs/react";
    import Layout from "../components/Layout";

    interface AboutProps {
      title: string;
      description: string;
    }

    export default function About({ title, description }: AboutProps) {
      return (
        <Layout title={title}>
          <h1>{title}</h1>
          <p>{description}</p>
          <Link href="/">Back to Home</Link>
        </Layout>
      );
    }

**Users.tsx**:

.. code-block:: tsx
    :caption: resources/pages/Users.tsx

    import { Link } from "@inertiajs/react";
    import Layout from "../components/Layout";

    interface User {
      id: number;
      name: string;
      email: string;
    }

    interface UsersProps {
      users: User[];
    }

    export default function Users({ users }: UsersProps) {
      return (
        <Layout title="Users">
          <h1>Users</h1>
          <ul>
            {users.map((user) => (
              <li key={user.id}>
                <strong>{user.name}</strong> - {user.email}
              </li>
            ))}
          </ul>
          <Link href="/">Back to Home</Link>
        </Layout>
      );
    }

7. Create a Layout Component
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``resources/components/Layout.tsx``:

.. code-block:: tsx
    :caption: resources/components/Layout.tsx

    import { Head } from "@inertiajs/react";
    import { ReactNode } from "react";

    interface LayoutProps {
      title: string;
      children: ReactNode;
    }

    export default function Layout({ title, children }: LayoutProps) {
      return (
        <>
          <Head title={title} />
          <div className="container">
            <header>
              <h2>My Inertia App</h2>
            </header>
            <main>{children}</main>
            <footer>
              <p>Built with Litestar + Inertia.js</p>
            </footer>
          </div>
        </>
      );
    }

8. Add Styles
~~~~~~~~~~~~~

Create ``resources/styles.css``:

.. code-block:: css
    :caption: resources/styles.css

    * {
      box-sizing: border-box;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      margin: 0;
      background: #f5f5f5;
    }

    .container {
      max-width: 800px;
      margin: 0 auto;
      padding: 2rem;
    }

    header {
      margin-bottom: 2rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid #ddd;
    }

    main {
      background: white;
      padding: 2rem;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    footer {
      margin-top: 2rem;
      text-align: center;
      color: #666;
    }

    a {
      color: #1976d2;
      text-decoration: none;
    }

    a:hover {
      text-decoration: underline;
    }

    ul {
      list-style: none;
      padding: 0;
    }

    li {
      padding: 0.5rem;
      background: #f9f9f9;
      margin-bottom: 0.5rem;
      border-radius: 4px;
    }

Running the Application
-----------------------

Start both servers:

.. code-block:: bash

    # Terminal 1: Vite dev server
    npm run dev

    # Terminal 2: Litestar
    litestar run --reload

Visit http://localhost:8000 and navigate between pages. Notice how:

- Page transitions are instant (no full page reload)
- The URL updates correctly
- Browser back/forward works as expected
- Data is passed from server to client seamlessly

Key Concepts
------------

InertiaResponse
~~~~~~~~~~~~~~~

Every Inertia page returns an ``InertiaResponse`` with:

- ``component``: The React component name to render
- ``props``: Data to pass to the component

.. code-block:: python

    @get("/dashboard")
    async def dashboard() -> InertiaResponse:
        return InertiaResponse(
            component="Dashboard",
            props={"user": {"name": "John"}, "stats": {"visits": 100}},
        )

Shared Data
~~~~~~~~~~~

Share data across all pages using the InertiaPlugin:

.. code-block:: python

    inertia = InertiaPlugin(
        config=InertiaConfig(
            root_template="index.html",
        )
    )

    # In a middleware or before request handler:
    @get("/")
    async def home(request: Request) -> InertiaResponse:
        # Access shared data from request state
        return InertiaResponse(
            component="Home",
            props={"user": request.user},  # From auth middleware
        )

Forms and Validation
~~~~~~~~~~~~~~~~~~~~

Handle forms with Inertia's form helper:

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

Server-side handler:

.. code-block:: python

    from litestar import post
    from litestar.params import Body
    from pydantic import BaseModel

    class CreateUserDTO(BaseModel):
        name: str
        email: str

    @post("/users")
    async def create_user(data: CreateUserDTO = Body()) -> InertiaResponse:
        # Create user in database...
        return InertiaResponse(
            component="Users",
            props={"message": "User created successfully!"},
        )

Next Steps
----------

- :doc:`/usage/inertia` - Complete Inertia.js reference
- :doc:`vue-integration` - Try Inertia with Vue instead
- :doc:`advanced-config` - Advanced configuration options
- `Inertia.js Documentation <https://inertiajs.com/>`_ - Official Inertia.js docs

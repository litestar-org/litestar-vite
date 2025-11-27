====================================
Building a React SPA with Inertia.js
====================================

This tutorial guides you through building a modern single-page application using React and Inertia.js with Litestar.

What is Inertia.js?
-------------------

Inertia.js allows you to build modern SPAs using classic server-side routing and controllers. You get the benefits of:

- Server-side routing (no separate API)
- React components for the frontend
- Automatic data hydration
- Shared state between pages
- No client-side routing complexity

Prerequisites
-------------

- Completed the :doc:`getting-started` tutorial
- Basic knowledge of React
- Understanding of Litestar route handlers

Installation
------------

Install Inertia dependencies:

.. code-block:: bash

    # Python
    uv add litestar-vite "litestar[jinja]"

    # Node.js
    npm install @inertiajs/react react react-dom
    npm install -D @types/react @types/react-dom @vitejs/plugin-react

Project Setup
-------------

Create the following structure:

.. code-block:: text

    my-inertia-app/
    ├── app.py
    ├── templates/
    │   └── app.html
    ├── resources/
    │   ├── main.tsx
    │   ├── Pages/
    │   │   ├── Home.tsx
    │   │   ├── About.tsx
    │   │   └── Dashboard.tsx
    │   └── Layouts/
    │       └── MainLayout.tsx
    └── vite.config.ts

Step 1: Configure Litestar with Inertia
----------------------------------------

Create ``app.py``:

.. code-block:: python
    :caption: app.py

    from pathlib import Path
    from litestar import Litestar, get
    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.template.config import TemplateConfig
    from litestar_vite import ViteConfig, VitePlugin
    from litestar_vite.inertia import (
        InertiaConfig,
        InertiaPlugin,
        InertiaResponse,
    )

    @get("/")
    async def home() -> InertiaResponse:
        return InertiaResponse(
            component="Pages/Home",
            props={
                "title": "Welcome to Inertia!",
                "message": "Build amazing SPAs with server-side routing",
            },
        )

    @get("/about")
    async def about() -> InertiaResponse:
        return InertiaResponse(
            component="Pages/About",
            props={"company": "Litestar Org"},
        )

    @get("/dashboard")
    async def dashboard() -> InertiaResponse:
        # Simulate fetching user data
        user = {"name": "John Doe", "email": "john@example.com"}
        return InertiaResponse(
            component="Pages/Dashboard",
            props={"user": user},
        )

    vite = VitePlugin(
        config=ViteConfig(
            bundle_dir=Path("public"),
            resource_dir=Path("resources"),
        )
    )

    inertia = InertiaPlugin(
        config=InertiaConfig(
            root_template="app.html",
        )
    )

    app = Litestar(
        route_handlers=[home, about, dashboard],
        plugins=[vite, inertia],
        template_config=TemplateConfig(
            directory=Path("templates"),
            engine=JinjaTemplateEngine,
        ),
    )

Step 2: Create the Root Template
---------------------------------

Create ``templates/app.html``:

.. code-block:: jinja
    :caption: templates/app.html

    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ page_title | default("My Inertia App") }}</title>
        {{ vite_hmr() }}
        {{ vite('resources/main.tsx') }}
        {{ inertia_head() }}
    </head>
    <body>
        {{ inertia_div() }}
    </body>
    </html>

**Template Tags:**

- ``{{ vite_hmr() }}`` - HMR client (dev mode only)
- ``{{ vite('resources/main.tsx') }}`` - Main entry point
- ``{{ inertia_head() }}`` - Inertia metadata
- ``{{ inertia_div() }}`` - React app mount point with initial page data

Step 3: Configure Vite for React
---------------------------------

Create ``vite.config.ts``:

.. code-block:: tsx
    :caption: vite.config.ts

    import { defineConfig } from 'vite';
    import react from '@vitejs/plugin-react';
    import litestar from '@litestar/vite-plugin';

    export default defineConfig({
      plugins: [
        litestar({
          input: 'resources/main.tsx',
          bundleDirectory: 'public',
          resourceDirectory: 'resources',
        }),
        react(),
      ],
      resolve: {
        alias: {
          '@': '/resources',
        },
      },
    });

Step 4: Initialize Inertia React App
-------------------------------------

Create ``resources/main.tsx``:

.. code-block:: tsx
    :caption: resources/main.tsx

    import { createRoot } from 'react-dom/client';
    import { createInertiaApp } from '@inertiajs/react';

    createInertiaApp({
      resolve: (name) => {
        const pages = import.meta.glob('./Pages/**/*.tsx', { eager: true });
        return pages[`./Pages/${name}.tsx`];
      },
      setup({ el, App, props }) {
        createRoot(el).render(<App {...props} />);
      },
    });

Step 5: Create React Pages
---------------------------

Create ``resources/Pages/Home.tsx``:

.. code-block:: tsx
    :caption: resources/Pages/Home.tsx

    import { Link } from '@inertiajs/react';

    interface HomeProps {
      title: string;
      message: string;
    }

    export default function Home({ title, message }: HomeProps) {
      return (
        <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
          <h1>{title}</h1>
          <p>{message}</p>

          <nav style={{ marginTop: '2rem' }}>
            <Link href="/" style={{ marginRight: '1rem' }}>
              Home
            </Link>
            <Link href="/about" style={{ marginRight: '1rem' }}>
              About
            </Link>
            <Link href="/dashboard">Dashboard</Link>
          </nav>
        </div>
      );
    }

Create ``resources/Pages/About.tsx``:

.. code-block:: tsx
    :caption: resources/Pages/About.tsx

    import { Link } from '@inertiajs/react';

    interface AboutProps {
      company: string;
    }

    export default function About({ company }: AboutProps) {
      return (
        <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
          <h1>About Us</h1>
          <p>This application is built by {company}</p>

          <nav style={{ marginTop: '2rem' }}>
            <Link href="/" style={{ marginRight: '1rem' }}>
              Home
            </Link>
            <Link href="/about" style={{ marginRight: '1rem' }}>
              About
            </Link>
            <Link href="/dashboard">Dashboard</Link>
          </nav>
        </div>
      );
    }

Create ``resources/Pages/Dashboard.tsx``:

.. code-block:: tsx
    :caption: resources/Pages/Dashboard.tsx

    import { Link } from '@inertiajs/react';

    interface User {
      name: string;
      email: string;
    }

    interface DashboardProps {
      user: User;
    }

    export default function Dashboard({ user }: DashboardProps) {
      return (
        <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
          <h1>Dashboard</h1>
          <p>Welcome back, {user.name}!</p>
          <p>Email: {user.email}</p>

          <nav style={{ marginTop: '2rem' }}>
            <Link href="/" style={{ marginRight: '1rem' }}>
              Home
            </Link>
            <Link href="/about" style={{ marginRight: '1rem' }}>
              About
            </Link>
            <Link href="/dashboard">Dashboard</Link>
          </nav>
        </div>
      );
    }

Step 6: Create a Shared Layout
-------------------------------

For consistent navigation across pages, create a layout:

Create ``resources/Layouts/MainLayout.tsx``:

.. code-block:: tsx
    :caption: resources/Layouts/MainLayout.tsx

    import { Link } from '@inertiajs/react';
    import { PropsWithChildren } from 'react';

    export default function MainLayout({ children }: PropsWithChildren) {
      return (
        <div style={{ fontFamily: 'sans-serif' }}>
          <nav style={{
            padding: '1rem',
            backgroundColor: '#f50057',
            color: 'white',
          }}>
            <Link href="/" style={{ color: 'white', marginRight: '1rem' }}>
              Home
            </Link>
            <Link href="/about" style={{ color: 'white', marginRight: '1rem' }}>
              About
            </Link>
            <Link href="/dashboard" style={{ color: 'white' }}>
              Dashboard
            </Link>
          </nav>
          <main style={{ padding: '2rem' }}>
            {children}
          </main>
        </div>
      );
    }

Update your pages to use the layout:

.. code-block:: tsx
    :caption: resources/Pages/Home.tsx (updated)

    import MainLayout from '../Layouts/MainLayout';

    interface HomeProps {
      title: string;
      message: string;
    }

    export default function Home({ title, message }: HomeProps) {
      return (
        <MainLayout>
          <h1>{title}</h1>
          <p>{message}</p>
        </MainLayout>
      );
    }

Step 7: Run Your Application
-----------------------------

.. code-block:: bash

    # Terminal 1: Vite dev server
    npm run dev

    # Terminal 2: Litestar server
    litestar run --reload

Visit http://localhost:8000 and navigate between pages. Notice how:

- Page transitions are instant (no full page reload)
- The URL updates correctly
- Browser back/forward buttons work
- Data is passed from server to client automatically

Advanced Features
-----------------

Sharing Data Globally
~~~~~~~~~~~~~~~~~~~~~

Share data across all pages using ``shared_props``:

.. code-block:: python

    from litestar_vite.inertia import share_inertia_props

    @share_inertia_props
    async def shared_data() -> dict:
        return {
            "auth": {"user": {"name": "John Doe"}},
            "flash": {"message": "Welcome back!"},
        }

    app = Litestar(
        route_handlers=[home, about, dashboard],
        plugins=[vite, inertia],
        on_startup=[shared_data],
    )

Form Handling
~~~~~~~~~~~~~

Handle forms with Inertia:

.. code-block:: tsx

    import { useForm } from '@inertiajs/react';

    export default function ContactForm() {
      const { data, setData, post, processing } = useForm({
        name: '',
        email: '',
        message: '',
      });

      const submit = (e: React.FormEvent) => {
        e.preventDefault();
        post('/contact');
      };

      return (
        <form onSubmit={submit}>
          <input
            value={data.name}
            onChange={e => setData('name', e.target.value)}
          />
          <button type="submit" disabled={processing}>
            Send
          </button>
        </form>
      );
    }

Next Steps
----------

- Explore :doc:`advanced-config` for optimization
- Check the `Inertia.js documentation <https://inertiajs.com/>`_
- See the :doc:`../reference/inertia/index` for API details

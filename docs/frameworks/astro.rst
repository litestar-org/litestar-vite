=====
Astro
=====

Astro integration with Litestar Vite for content-focused sites with optional islands of interactivity.

At a Glance
-----------

- Template: ``litestar assets init --template astro``
- Mode: ``ssg`` (alias: ``framework``)
- Dev: ``litestar run --reload`` (Litestar starts the Astro dev server via Vite)
- Types: ``TypeGenConfig`` generates Astro types

Quick Start
-----------

.. code-block:: bash

    litestar assets init --template astro

This creates an Astro project with TypeScript support and multi-framework component support.

Project Structure
-----------------

Astro applications use the Astro integration:

.. code-block:: text

    my-app/
    ├── app.py              # Litestar backend
    ├── package.json
    ├── astro.config.mjs    # Astro configuration with Litestar integration
    ├── tsconfig.json
    └── src/
        ├── pages/
        │   └── index.astro     # Pages (file-based routing)
        ├── components/
        │   └── Card.astro      # Astro components
        └── generated/          # Generated types from OpenAPI

Backend Setup
-------------

.. literalinclude:: /../examples/astro/app.py
   :language: python
   :caption: examples/astro/app.py

Key points:

- ``mode="ssg"`` enables static-site integration mode (alias: ``mode="framework"``)
- Litestar starts the Astro dev server via ``RuntimeConfig.start_dev_server=True`` (default)
- ``TypeGenConfig`` enables type generation for Astro

Astro Configuration
-------------------

.. literalinclude:: /../examples/astro/astro.config.mjs
   :language: javascript
   :caption: astro.config.mjs

The Litestar integration provides:

- API proxy configuration (``apiProxy``)
- Type generation integration
- Automatic port coordination with Litestar backend

Configuration options:

- ``apiProxy`` - URL of Litestar backend (default: ``http://localhost:8000``)
- ``apiPrefix`` - API route prefix to proxy (default: ``/api``)
- ``types`` - Type generation configuration

API Integration
---------------

Server-Side Data Fetching
~~~~~~~~~~~~~~~~~~~~~~~~~~

Astro pages can fetch data at build time or on-demand (SSR):

.. code-block:: astro

    ---
    // src/pages/users/[id].astro
    import type { User } from '../../generated/types.gen'
    import { route } from '../../generated/routes'

    const { id } = Astro.params
    const response = await fetch(route('users:show', { id }))
    const user: User = await response.json()
    ---

    <html>
      <head>
        <title>{user.name}</title>
      </head>
      <body>
        <h1>{user.name}</h1>
        <p>{user.email}</p>
      </body>
    </html>

Static Site Generation (SSG)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``getStaticPaths`` for static generation:

.. code-block:: astro

    ---
    import type { User } from '../../generated/types.gen'

    export async function getStaticPaths() {
      const response = await fetch('http://localhost:8000/api/users')
      const users: User[] = await response.json()

      return users.map(user => ({
        params: { id: user.id },
        props: { user },
      }))
    }

    const { user } = Astro.props
    ---

    <h1>{user.name}</h1>

Client-Side Interactivity
~~~~~~~~~~~~~~~~~~~~~~~~~

Add interactive islands with ``client:*`` directives:

.. code-block:: astro

    ---
    // src/pages/index.astro
    import Counter from '../components/Counter'
    ---

    <html>
      <body>
        <h1>Welcome</h1>
        <!-- Only hydrates on client when visible -->
        <Counter client:visible />
      </body>
    </html>

.. code-block:: tsx

    // src/components/Counter.tsx (React, Vue, Svelte, etc.)
    import { useState } from 'react'
    import { route } from '../generated/routes'

    export default function Counter() {
      const [count, setCount] = useState(0)
      const [summary, setSummary] = useState(null)

      async function loadSummary() {
        const res = await fetch(route('summary'))
        setSummary(await res.json())
      }

      return (
        <div>
          <button onClick={() => setCount(count + 1)}>Count: {count}</button>
          <button onClick={loadSummary}>Load Summary</button>
          {summary && <p>{summary.headline}</p>}
        </div>
      )
    }

Running
-------

.. code-block:: bash

    # Recommended: Litestar manages both servers
    litestar run --reload

    # Alternative: Run separately
    litestar assets serve  # Astro/Vite dev server
    litestar run --reload  # Backend API (in another terminal)

Type Generation
---------------

With ``types=TypeGenConfig()`` enabled in Python:

.. code-block:: bash

    litestar assets generate-types

This generates TypeScript types in ``src/generated/`` (path configured in ``astro.config.mjs``).

Deployment
----------

For production:

1. Build Astro:

   .. code-block:: bash

       litestar assets build

2. Serve the built site:

   - **Static mode (default)**: ``VITE_DEV_MODE=false litestar run`` (Litestar serves ``dist/``)
   - **Server/Hybrid**: ``litestar assets serve --production`` (Astro SSR server) + ``litestar run``

Rendering Modes
---------------

Astro supports multiple rendering modes:

.. list-table::
   :widths: 20 40 40
   :header-rows: 1

   * - Mode
     - Use Case
     - Output
   * - Static (SSG)
     - Blogs, marketing sites
     - Pre-built HTML files
   * - Server (SSR)
     - Dynamic content, auth
     - On-demand rendering
   * - Hybrid
     - Mix of static + dynamic
     - Some pre-built, some on-demand

Configure in ``astro.config.mjs``:

.. code-block:: javascript

    export default defineConfig({
      output: 'server',  // 'static', 'server', or 'hybrid'
      integrations: [litestar({ /* ... */ })],
    })

See Also
--------

- `Example: astro <https://github.com/litestar-org/litestar-vite/tree/main/examples/astro>`_
- `Astro Documentation <https://docs.astro.build/>`_
- :doc:`/usage/types` - TypeScript type generation

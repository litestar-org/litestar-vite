====
Nuxt
====

Nuxt 3+ integration with Litestar Vite for universal SSR applications.

Quick Start
-----------

.. code-block:: bash

    litestar assets init --template nuxt

This creates a Nuxt 3 project with TypeScript support and SSR capabilities.

Project Structure
-----------------

Nuxt applications use the Nuxt module for seamless integration:

.. code-block:: text

    my-app/
    ├── app.py              # Litestar backend
    ├── package.json
    ├── nuxt.config.ts      # Nuxt configuration with Litestar module
    ├── tsconfig.json
    ├── app.vue             # Root component
    ├── pages/
    │   └── index.vue       # Pages (file-based routing)
    ├── composables/
    │   └── useApi.ts       # Composables for API calls
    └── generated/          # Generated types from OpenAPI

Backend Setup
-------------

.. literalinclude:: /../examples/nuxt/app.py
   :language: python
   :caption: examples/nuxt/app.py

Key points:

- ``mode="framework"`` enables meta-framework integration mode (aliases: ``mode="ssr"`` / ``mode="ssg"``)
- ``ExternalDevServer`` delegates dev server to Nuxt
- ``TypeGenConfig`` enables type generation for Nuxt composables

Nuxt Configuration
------------------

.. literalinclude:: /../examples/nuxt/nuxt.config.ts
   :language: typescript
   :caption: nuxt.config.ts

The Litestar module provides:

- API proxy configuration (``apiProxy``)
- Type generation integration
- Automatic port coordination with Litestar backend

Runtime Configuration
---------------------

Nuxt reads runtime configuration from ``VITE_PORT`` and ``LITESTAR_PORT`` environment variables set by Litestar:

.. code-block:: typescript

    // In composables or pages
    const config = useRuntimeConfig()
    const apiUrl = config.public.apiProxy  // http://localhost:8000
    const apiPrefix = config.public.apiPrefix  // /api

API Integration
---------------

Using Composables
~~~~~~~~~~~~~~~~~

.. code-block:: typescript

    // composables/useApi.ts
    import type { Summary } from '~/generated/types.gen'
    import { route } from '~/generated/routes'

    export async function useSummary() {
      const { data, error } = await useFetch<Summary>(
        route('summary'),
        { key: 'summary' }
      )
      return { data, error }
    }

Server Routes (SSR)
~~~~~~~~~~~~~~~~~~~

For server-side API calls during SSR, create a server middleware:

.. code-block:: typescript

    // server/api/[...].ts
    export default defineEventHandler((event) => {
      const config = useRuntimeConfig()
      return proxyRequest(event, config.public.apiProxy + event.path)
    })

Client-Side Fetch
~~~~~~~~~~~~~~~~~

.. code-block:: vue

    <script setup lang="ts">
    import type { User } from '~/generated/types.gen'
    import { route } from '~/generated/routes'

    const { data: users } = await useFetch<User[]>(route('users:list'))
    </script>

    <template>
      <div>
        <h1>Users</h1>
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

    # Recommended: Litestar manages both servers
    litestar run --reload

    # Alternative: Run separately
    litestar assets serve --production  # Nuxt SSR server
    litestar run --reload               # Backend API (in another terminal)

Type Generation
---------------

With ``types=TypeGenConfig()`` enabled in Python:

.. code-block:: bash

    litestar assets generate-types

This generates TypeScript types in ``generated/`` (path configured in ``nuxt.config.ts``).

Deployment
----------

For production:

1. Build Nuxt:

   .. code-block:: bash

       litestar assets build

2. Serve both apps:

   .. code-block:: bash

       litestar assets serve --production  # Nuxt SSR server
       litestar run                        # Backend API

The ``--production`` flag runs ``npm run serve`` which starts Nuxt's production server.

See Also
--------

- `Example: nuxt <https://github.com/litestar-org/litestar-vite/tree/main/examples/nuxt>`_
- `Nuxt 3 Documentation <https://nuxt.com/>`_
- :doc:`/usage/types` - TypeScript type generation

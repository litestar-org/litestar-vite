==========
SvelteKit
==========

SvelteKit integration with Litestar Vite for full-stack Svelte applications.

At a Glance
-----------

- Template: ``litestar assets init --template sveltekit``
- Mode: ``ssr`` (alias: ``framework``)
- Dev: ``litestar run --reload`` (Litestar starts the SvelteKit dev server via Vite)
- Types: ``TypeGenConfig`` generates SvelteKit types

Quick Start
-----------

.. code-block:: bash

    litestar assets init --template sveltekit

This creates a SvelteKit project with TypeScript support and SSR capabilities.

Project Structure
-----------------

SvelteKit applications use a specialized Vite plugin:

.. code-block:: text

    my-app/
    ├── app.py              # Litestar backend
    ├── package.json
    ├── vite.config.ts      # Vite + SvelteKit plugin
    ├── svelte.config.js    # SvelteKit configuration
    ├── tsconfig.json
    ├── src/
    │   ├── app.html        # HTML template
    │   ├── routes/
    │   │   └── +page.svelte    # Pages (file-based routing)
    │   └── lib/
    │       └── generated/  # Generated types from OpenAPI
    └── build/              # SvelteKit build output

Backend Setup
-------------

.. literalinclude:: /../examples/sveltekit/app.py
   :language: python
   :caption: examples/sveltekit/app.py

Key points:

- ``mode="ssr"`` enables meta-framework integration mode (alias: ``mode="framework"``)
- Litestar starts the SvelteKit dev server via ``RuntimeConfig.start_dev_server=True`` (default)
- ``TypeGenConfig`` enables type generation for SvelteKit

Vite Configuration
------------------

.. literalinclude:: /../examples/sveltekit/vite.config.ts
   :language: typescript
   :caption: vite.config.ts

The ``litestarSvelteKit`` plugin must come **before** the ``sveltekit()`` plugin.

Configuration options:

- ``apiProxy`` - URL of Litestar backend (default: ``http://localhost:8000``)
- ``apiPrefix`` - API route prefix to proxy (default: ``/api``)
- ``types`` - Enable type generation (reads from ``.litestar.json`` or explicit config)

API Integration
---------------

Using Load Functions
~~~~~~~~~~~~~~~~~~~~

SvelteKit's ``load`` functions are perfect for SSR data fetching:

.. code-block:: typescript

    // src/routes/users/+page.ts
    import type { PageLoad } from './$types'
    import type { User } from '$lib/generated/types.gen'
    import { route } from '$lib/generated/routes'

    export const load: PageLoad = async ({ fetch }) => {
      const response = await fetch(route('users:list'))
      const users: User[] = await response.json()
      return { users }
    }

.. code-block:: svelte

    <!-- src/routes/users/+page.svelte -->
    <script lang="ts">
      import type { PageData } from './$types'

      export let data: PageData
    </script>

    <h1>Users</h1>
    <ul>
      {#each data.users as user (user.id)}
        <li>{user.name}</li>
      {/each}
    </ul>

Server-Side API Calls
~~~~~~~~~~~~~~~~~~~~~

Use ``+page.server.ts`` for server-only logic:

.. code-block:: typescript

    // src/routes/users/+page.server.ts
    import type { PageServerLoad } from './$types'
    import type { User } from '$lib/generated/types.gen'

    export const load: PageServerLoad = async ({ fetch }) => {
      const response = await fetch('http://localhost:8000/api/users')
      const users: User[] = await response.json()
      return { users }
    }

Client-Side Fetch
~~~~~~~~~~~~~~~~~

.. code-block:: svelte

    <script lang="ts">
      import { onMount } from 'svelte'
      import type { Summary } from '$lib/generated/types.gen'
      import { route } from '$lib/generated/routes'

      let summary = $state<Summary | null>(null)

      onMount(async () => {
        const res = await fetch(route('summary'))
        summary = await res.json()
      })
    </script>

    {#if summary}
      <h1>{summary.headline}</h1>
    {/if}

Running
-------

.. code-block:: bash

    # Recommended: Litestar manages both servers
    litestar run --reload

    # Alternative: Run separately
    litestar assets serve  # SvelteKit dev server
    litestar run --reload  # Backend API (in another terminal)

Type Generation
---------------

With ``types=TypeGenConfig()`` enabled in Python:

.. code-block:: bash

    litestar assets generate-types

This generates TypeScript types in ``src/lib/generated/`` (configured via ``.litestar.json``).

The types are accessible via SvelteKit's ``$lib`` alias:

.. code-block:: typescript

    import type { User } from '$lib/generated/types.gen'
    import { route } from '$lib/generated/routes'

Deployment
----------

For production:

1. Build SvelteKit:

   .. code-block:: bash

       litestar assets build

2. Serve both apps:

   .. code-block:: bash

       litestar assets serve --production  # SvelteKit adapter server
       litestar run                        # Backend API

The build uses SvelteKit's adapter (e.g., ``@sveltejs/adapter-node`` for Node.js deployment).

See Also
--------

- `Example: sveltekit <https://github.com/litestar-org/litestar-vite/tree/main/examples/sveltekit>`_
- `SvelteKit Documentation <https://kit.svelte.dev/>`_
- :doc:`/usage/types` - TypeScript type generation

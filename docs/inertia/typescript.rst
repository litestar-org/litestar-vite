======================
TypeScript Integration
======================

Full TypeScript support for Inertia applications.

.. seealso::
   Official Inertia.js docs: `TypeScript <https://inertiajs.com/typescript>`_

Overview
--------

Litestar-Vite provides comprehensive TypeScript integration:

- **Typed routes**: Generated ``routes.ts`` with type-safe ``route()`` helper
- **Typed page props**: Generated ``PageProps`` interface for each component
- **Typed shared props**: ``SharedProps`` interface for ``share()`` data
- **Default interfaces**: ``User``, ``AuthData``, ``FlashMessages``

Enabling Type Generation
------------------------

.. code-block:: python

   from litestar_vite import ViteConfig, VitePlugin

   VitePlugin(config=ViteConfig(
       dev_mode=True,
       types=True,      # Enable type generation
       inertia=True,    # Enable Inertia
   ))

Generate types:

.. code-block:: bash

   litestar assets generate-types

Generated Files
---------------

Type generation creates these files in your output directory (default: ``src/generated/``):

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - File
     - Description
   * - ``routes.ts``
     - Type-safe route helper and route names
   * - ``page-props.ts``
     - Typed props for each page component
   * - ``openapi.json``
     - OpenAPI schema (optional)

Using Generated Types
---------------------

Import types in your components:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import type { PageProps } from "@/generated/page-props";

         // Props are fully typed
         export default function Dashboard(props: PageProps["Dashboard"]) {
           return <h1>Users: {props.userCount}</h1>;
         }

   .. tab-item:: Vue

      .. code-block:: vue

         <script setup lang="ts">
         import type { PageProps } from "@/generated/page-props";

         defineProps<PageProps["Dashboard"]>();
         </script>

   .. tab-item:: Svelte

      .. code-block:: svelte

         <script lang="ts">
         import type { PageProps } from "@/generated/page-props";

         let { userCount }: PageProps["Dashboard"] = $props();
         </script>

Type-Safe Routes
----------------

Use the generated ``route()`` helper:

.. code-block:: typescript

   import { route } from "@/generated/routes";

   // Type-safe route names
   const url = route("dashboard");           // ✓
   const url = route("invalid-route");       // ✗ TypeScript error

   // Type-safe parameters
   const url = route("user-profile", { userId: 123 });  // ✓

TypeGenConfig Options
---------------------

Configure type generation behavior:

.. code-block:: python

   from litestar_vite.config import TypeGenConfig

   ViteConfig(
       types=TypeGenConfig(
           output=Path("src/generated"),
           generate_routes=True,
           generate_page_props=True,
           generate_sdk=True,
       ),
   )

See :doc:`type-generation` for full configuration reference.

Development Workflow
--------------------

1. Define your route handlers with typed returns
2. Run ``litestar assets generate-types``
3. Import generated types in components
4. TypeScript validates prop usage

For automatic regeneration during development, add to your Vite config:

.. code-block:: typescript

   // vite.config.ts
   import litestar from "litestar-vite-plugin";

   export default {
     plugins: [
       litestar({
         // Watch for type changes
         hotFile: "public/hot",
       }),
     ],
   };

See Also
--------

- :doc:`type-generation` - TypeGenConfig reference
- :doc:`typed-page-props` - PageProps usage
- :doc:`shared-props-typing` - SharedProps extension

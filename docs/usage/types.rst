===============
Type Generation
===============

Litestar Vite includes a type generation system that keeps your frontend in sync with your Python backend.

Overview
--------

The type generation pipeline:

1. Exports your Litestar OpenAPI schema to JSON
2. Generates TypeScript interfaces using ``@hey-api/openapi-ts``
3. Extracts route metadata from your application
4. Generates a typed ``route()`` helper for type-safe URL generation

Configuration
-------------

Enable type generation in your ``ViteConfig``:

.. code-block:: python

    from litestar_vite.config import TypeGenConfig

    VitePlugin(
        config=ViteConfig(
            types=TypeGenConfig(
                output=Path("src/generated"),  # default
                generate_sdk=True,             # generate API client
                generate_routes=True,          # generate routes.ts
            )
        )
    )

Or use the shortcut for defaults:

.. code-block:: python

    VitePlugin(config=ViteConfig(types=True))

TypeGenConfig Reference
-----------------------

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Parameter
     - Default
     - Description
   * - ``output``
     - ``src/generated``
     - Output directory for all generated files
   * - ``openapi_path``
     - ``{output}/openapi.json``
     - Path for exported OpenAPI schema
   * - ``routes_path``
     - ``{output}/routes.json``
     - Path for routes metadata JSON
   * - ``routes_ts_path``
     - ``{output}/routes.ts``
     - Path for typed route helper
   * - ``generate_zod``
     - ``False``
     - Generate Zod schemas for runtime validation
   * - ``generate_sdk``
     - ``True``
     - Generate API client SDK via hey-api
   * - ``generate_routes``
     - ``True``
     - Generate typed routes.ts file
   * - ``generate_page_props``
     - ``True``
     - Generate Inertia page props types
   * - ``page_props_path``
     - ``{output}/inertia-pages.json``
     - Path for page props metadata
   * - ``watch_patterns``
     - See below
     - File patterns to watch for regeneration

Default watch patterns:

.. code-block:: python

    watch_patterns=["**/routes.py", "**/handlers.py", "**/controllers/**/*.py"]

hey-api Configuration
---------------------

Litestar Vite uses `hey-api/openapi-ts <https://heyapi.dev/>`_ to generate TypeScript
types from your OpenAPI schema. Create an ``openapi-ts.config.ts`` in your project root:

.. literalinclude:: /../examples/react/openapi-ts.config.ts
   :language: typescript
   :caption: openapi-ts.config.ts

Available hey-api plugins:

- ``@hey-api/typescript`` - Core TypeScript types (always included)
- ``@hey-api/schemas`` - JSON Schema exports
- ``@hey-api/sdk`` - Type-safe API client
- ``@hey-api/client-axios`` - Axios-based HTTP client
- ``@hey-api/client-fetch`` - Fetch-based HTTP client
- ``@hey-api/zod`` - Zod runtime validators

Generating Types
----------------

Generate all types with a single command:

.. code-block:: bash

    litestar assets generate-types

This runs the full pipeline:

1. Exports OpenAPI schema to ``src/generated/openapi.json``
2. Runs ``npx openapi-ts`` to generate TypeScript types
3. Generates ``routes.ts`` with typed route helper

You can also export routes separately:

.. code-block:: bash

    litestar assets export-routes

Generated Files
---------------

After running ``generate-types``, your output directory contains:

.. code-block:: text

    src/generated/
    ├── openapi.json       # OpenAPI schema from Litestar
    ├── routes.json        # Route metadata
    ├── routes.ts          # Typed route() helper
    └── api/               # hey-api output (if generate_sdk=True)
        ├── index.ts       # Barrel export
        ├── types.gen.ts   # TypeScript interfaces
        ├── schemas.gen.ts # JSON schemas (if @hey-api/schemas)
        └── sdk.gen.ts     # API client (if @hey-api/sdk)

Using Generated Types
---------------------

Import types and the route helper in your frontend:

.. code-block:: typescript

    import { route } from './generated/routes';
    import type { Book, Summary } from './generated/api';

    // Type-safe URL generation
    const bookUrl = route('api:books.detail', { book_id: 123 });
    // => "/api/books/123"

    // Type-safe API calls
    const response = await fetch(route('api:summary'));
    const summary: Summary = await response.json();

Using the Generated SDK
-----------------------

If ``generate_sdk=True``, hey-api generates a fully typed API client:

.. code-block:: typescript

    import { client, getApiSummary, getApiBooks } from './generated/api';

    // Configure base URL (optional - defaults to same origin)
    client.setConfig({ baseUrl: '/api' });

    // Type-safe API calls with full IntelliSense
    const { data: summary } = await getApiSummary();
    const { data: books } = await getApiBooks();

    // Parameters are typed
    const { data: book } = await getApiBooksBookId({ path: { book_id: 1 } });

Typed Routes
------------

The generated ``routes.ts`` provides Ziggy-style type-safe routing:

.. code-block:: typescript

    // Generated types
    export type RouteName = "home" | "api:summary" | "api:books" | "api:books.detail";

    export interface RouteParams {
      "api:books.detail": { book_id: string | number };
      // ... other routes with params
    }

    // Type-safe route function
    export function route<T extends RouteName>(
      name: T,
      params?: RouteParams[T]
    ): string;

    // Usage
    route("home");                                  // "/"
    route("api:books.detail", { book_id: 123 });   // "/api/books/123"
    route("api:books.detail");                     // TypeScript Error!

Auto-Regeneration
-----------------

During development, types are regenerated when watched files change.
Configure patterns in ``TypeGenConfig``:

.. code-block:: python

    TypeGenConfig(
        watch_patterns=[
            "**/routes.py",
            "**/handlers.py",
            "**/controllers/**/*.py",
            "**/models/**/*.py",  # Add custom patterns
        ],
    )

Inertia Page Props
------------------

When using Inertia.js, enable page props generation:

.. code-block:: python

    VitePlugin(
        config=ViteConfig(
            types=TypeGenConfig(generate_page_props=True),
            inertia=True,
        )
    )

This generates ``inertia-pages.json`` which the Vite plugin uses to create
``page-props.ts`` with typed props for each page component.

See :doc:`/inertia/type-generation` for Inertia-specific details.

See Also
--------

- :doc:`/inertia/type-generation` - Inertia-specific type generation
- `hey-api Documentation <https://heyapi.dev/>`_
- `Example: react <https://github.com/litestar-org/litestar-vite/tree/main/examples/react>`_

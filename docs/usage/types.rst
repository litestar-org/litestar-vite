===============
Type Generation
===============

Litestar Vite v2 includes a powerful type generation system that keeps your frontend in sync with your Python backend.

Overview
--------

The type generation pipeline:

1. Exports your Litestar OpenAPI schema.
2. Generates TypeScript interfaces using ``@hey-api/openapi-ts``.
3. Extracts route metadata from your application.
4. Generates a typed ``route()`` helper for type-safe URL generation.

Configuration
-------------

Enable type generation in your ``ViteConfig``:

.. code-block:: python

    from litestar_vite.config import TypeGenConfig

    VitePlugin(
        config=ViteConfig(
            types=TypeGenConfig(
                enabled=True,
                output_dir="src/lib/api",
            )
        )
    )

Or use the shortcut:

.. code-block:: python

    VitePlugin(config=ViteConfig(types=True))

Usage in Frontend
-----------------

Import the generated types and route helper:

.. code-block:: typescript

    import { route } from './lib/api/routes';
    import type { User } from './lib/api/types.gen';

    // Type-safe URL generation
    const url = route('users.show', { id: 123 });

    // Type-safe API calls
    const response = await fetch(url);
    const user: User = await response.json();

Commands
--------

You can manually trigger type generation:

.. code-block:: bash

    litestar assets generate-types

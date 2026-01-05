===============
Type Generation
===============

Configure TypeScript type generation for routes and props.

Enabling Type Generation
------------------------

.. code-block:: python

   from litestar_vite import ViteConfig, VitePlugin

   # Simple - enable with defaults
   VitePlugin(config=ViteConfig(
       types=True,
       inertia=True,
   ))

   # Advanced - custom configuration
   from litestar_vite.config import TypeGenConfig

   VitePlugin(config=ViteConfig(
       types=TypeGenConfig(
           output=Path("src/generated"),
           generate_routes=True,
           generate_page_props=True,
       ),
       inertia=True,
   ))

TypeGenConfig Reference
-----------------------

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - ``output``
     - ``Path``
     - Output directory for generated files. Default: ``src/generated``
   * - ``openapi_path``
     - ``Path | None``
     - Path for OpenAPI schema. Default: ``{output}/openapi.json``
   * - ``routes_path``
     - ``Path | None``
     - Path for routes JSON. Default: ``{output}/routes.json``
   * - ``routes_ts_path``
     - ``Path | None``
     - Path for routes TypeScript. Default: ``{output}/routes.ts``
   * - ``schemas_ts_path``
     - ``Path | None``
     - Path for schemas helper types. Default: ``{output}/schemas.ts``
   * - ``page_props_path``
     - ``Path | None``
     - Path for page props JSON. Default: ``{output}/inertia-pages.json``
   * - ``generate_zod``
     - ``bool``
     - Generate Zod schemas. Default: ``False``
   * - ``generate_sdk``
     - ``bool``
     - Generate API client SDK. Default: ``True``
   * - ``generate_routes``
     - ``bool``
     - Generate typed routes.ts. Default: ``True``
   * - ``generate_page_props``
     - ``bool``
     - Generate page props types. Default: ``True``
   * - ``generate_schemas``
     - ``bool``
     - Generate schemas helper types. Default: ``True``
   * - ``fallback_type``
     - ``Literal["unknown", "any"]``
     - Fallback value type for untyped dict/list in page props. Default: ``unknown``
   * - ``type_import_paths``
     - ``dict[str, str]``
     - Map schema/type names to TypeScript import paths for props types excluded from OpenAPI. Default: ``{}``
   * - ``global_route``
     - ``bool``
     - Register ``route()`` globally on ``window``. Default: ``False``

Generating Types
----------------

.. code-block:: bash

   # Generate all types
   litestar assets generate-types

   # Or export routes only
   litestar assets export-routes

Generated routes.ts
-------------------

The ``routes.ts`` file provides type-safe route handling:

.. code-block:: typescript

   // If OpenAPI schemas include a `format`, `routes.ts` also emits semantic aliases
   // and uses them in route parameter types (aliases are plain primitives, no runtime parsing).
   export type UUID = string;
   export type DateTime = string;

   // Generated types
   export type RouteName = "home" | "dashboard" | "user-profile" | ...;

   export interface RoutePathParams {
     "user-profile": { userId: number };
     "home": Record<string, never>;
     // ...
   }

   export interface RouteQueryParams {
     "user-profile": Record<string, never>;
     "home": Record<string, never>;
     // ...
   }

   type EmptyParams = Record<string, never>
   type MergeParams<A, B> =
     A extends EmptyParams ? (B extends EmptyParams ? EmptyParams : B) : B extends EmptyParams ? A : A & B

   export type RouteParams<T extends RouteName> =
     MergeParams<RoutePathParams[T], RouteQueryParams[T]>;

   // Type-safe route function (params required only when needed)
   export function route<T extends RoutesWithoutRequiredParams>(name: T): string;
   export function route<T extends RoutesWithoutRequiredParams>(name: T, params?: RouteParams<T>): string;
   export function route<T extends RoutesWithRequiredParams>(name: T, params: RouteParams<T>): string;

   // Usage
   route("home");                           // "/"
   route("user-profile", { userId: 123 });  // "/users/123"
   route("user-profile");                   // TS Error: missing params

.. note::

   For URL generation, route params never require ``null`` values. Optionality is represented by optional
   query parameters (``?:``) and omission, matching how ``route()`` serializes values.

Generated inertia-pages.json
----------------------------

The Vite plugin reads this metadata to generate ``page-props.ts``:

.. code-block:: json

   {
     "pages": {
       "Dashboard": {
         "route": "/dashboard",
         "tsType": "DashboardProps",
         "schemaRef": "#/components/schemas/DashboardProps",
         "customTypes": ["DashboardProps"]
       }
     },
     "typeImportPaths": {
       "InternalProps": "@/types/internal"
     },
     "fallbackType": "unknown",
     "typeGenConfig": {
       "includeDefaultAuth": true,
       "includeDefaultFlash": true
     },
     "generatedAt": "2025-12-11T00:00:00Z"
   }

Vite Plugin Configuration
-------------------------

The Vite plugin generates the final ``page-props.ts``:

.. code-block:: typescript
   :caption: vite.config.ts

   import litestar from "litestar-vite-plugin";

   export default {
     plugins: [
       litestar({
         input: ["resources/main.ts"],
         hotFile: "public/hot",
         // Page props generation is automatic when inertia-pages.json exists
       }),
     ],
   };

Watch Mode
----------

Configure patterns to trigger regeneration:

.. code-block:: python

   TypeGenConfig(
       watch_patterns=[
           "**/routes.py",
           "**/handlers.py",
           "**/controllers/**/*.py",
       ],
   )

Output Structure
----------------

Default generated file structure:

.. code-block:: text

   src/generated/
   ├── openapi.json       # OpenAPI schema
   ├── routes.json        # Route metadata
   ├── routes.ts          # Type-safe route helper
   ├── inertia-pages.json # Page props metadata
   └── page-props.ts      # Generated by Vite plugin

See Also
--------

- :doc:`typescript` - TypeScript overview
- :doc:`typed-page-props` - Using PageProps
- :doc:`links` - Route helper usage

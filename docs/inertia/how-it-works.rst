============
How It Works
============

Understand the Inertia.js protocol and how it integrates with Litestar.

.. seealso::
   Official Inertia.js docs: `How It Works <https://inertiajs.com/how-it-works>`_

The Inertia Protocol
--------------------

Inertia.js is a protocol for building SPAs with server-side routing.
Instead of returning JSON from an API, your routes return page components:

1. **Initial page load**: Server renders full HTML with embedded page data
2. **Subsequent navigation**: Client makes XHR request, server returns JSON
3. **Client updates**: Inertia swaps page component without full reload

.. mermaid::

   sequenceDiagram
       participant Browser
       participant Server

       Note over Browser,Server: Initial Page Load
       Browser->>Server: GET /dashboard
       Server->>Browser: HTML with data-page JSON

       Note over Browser,Server: Subsequent Navigation
       Browser->>Server: XHR GET /users<br>X-Inertia: true
       Server->>Browser: JSON {component, props, url}
       Note over Browser: Swap component, update URL

Request Flow
------------

**Initial Load (Full HTML)**:

.. code-block:: html

   <!-- Server returns full HTML -->
   <div id="app" data-page='{"component":"Dashboard","props":{"user":"Alice"},"url":"/dashboard"}'></div>

**XHR Request (JSON)**:

.. code-block:: text

   GET /users HTTP/1.1
   X-Inertia: true
   X-Inertia-Version: abc123

.. code-block:: json

   {
     "component": "Users",
     "props": {"users": ["Alice", "Bob"]},
     "url": "/users",
     "version": "abc123"
   }

Inertia Headers
---------------

The protocol uses these HTTP headers:

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Header
     - Description
   * - ``X-Inertia``
     - Request: Client indicates Inertia request
   * - ``X-Inertia-Version``
     - Request: Asset version for cache invalidation
   * - ``X-Inertia-Partial-Data``
     - Request: Requested partial reload keys
   * - ``X-Inertia-Partial-Except``
     - Request: Keys to exclude (v2)
   * - ``X-Inertia-Reset``
     - Request: Props to reset (v2)
   * - ``X-Inertia``
     - Response: Server confirms Inertia response
   * - ``X-Inertia-Location``
     - Response: External redirect URL

Version Checking
----------------

Inertia uses asset versioning to detect outdated clients:

1. Client sends ``X-Inertia-Version`` header
2. Server compares with current manifest hash
3. On mismatch, server returns ``409 Conflict``
4. Client performs full page reload

Litestar-Vite automatically handles versioning using the Vite manifest.

Litestar Integration
--------------------

Litestar-Vite implements the protocol through:

- **InertiaPlugin**: Middleware for request/response handling
- **InertiaResponse**: Response class for page data
- **InertiaMiddleware**: Header parsing and validation
- **ViteAssetLoader**: Asset versioning via manifest hash

.. code-block:: python

   # Simple Inertia route
   @get("/dashboard", component="Dashboard")
   async def dashboard() -> dict:
       return {"user": "Alice", "stats": {"views": 100}}

   # The plugin handles:
   # 1. Detecting X-Inertia header
   # 2. Building PageProps object
   # 3. Returning JSON or HTML based on request type
   # 4. Version checking

See Also
--------

- `The Inertia Protocol <https://inertiajs.com/the-protocol>`_ - Official protocol docs
- :doc:`asset-versioning` - Version checking details
- :doc:`responses` - Response classes

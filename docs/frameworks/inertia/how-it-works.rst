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
       Server->>Browser: HTML with page JSON bootstrap

       Note over Browser,Server: Subsequent Navigation
       Browser->>Server: XHR GET /users<br>X-Inertia: true
       Server->>Browser: JSON {component, props, url}
       Note over Browser: Swap component, update URL

Request Flow
------------

The examples below show both bootstrap formats because litestar-vite now defaults to the
script-element transport while still supporting the classic ``data-page`` compatibility path.

**Initial Load (Full HTML)**:

.. code-block:: html

   <!-- Classic data-page bootstrap -->
   <div id="app" data-page='{"component":"Dashboard","props":{"user":"Alice"},"url":"/dashboard"}'></div>

.. code-block:: html

   <!-- Default script-element bootstrap -->
   <div id="app"></div>
   <script type="application/json" id="app_page" data-page="app">
     {"component":"Dashboard","props":{"user":"Alice"},"url":"/dashboard"}
   </script>

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
   * - ``X-Inertia-Partial-Component``
     - Request: Target component name for scoped partial reloads
   * - ``X-Inertia-Partial-Data``
     - Request: Requested partial reload keys
   * - ``X-Inertia-Partial-Except``
     - Request: Keys to exclude (v2)
   * - ``X-Inertia-Except-Once-Props``
     - Request: Once-prop keys already cached client-side and safe to omit
   * - ``X-Inertia-Reset``
     - Request: Props to reset (v2)
   * - ``X-Inertia-Error-Bag``
     - Request: Validation error bag name scoping form errors
   * - ``X-Inertia``
     - Response: Server confirms Inertia response
   * - ``X-Inertia-Location``
     - Response: External redirect URL

Status Codes
------------

Litestar's Inertia integration produces and responds to standard HTTP status codes:

.. list-table::
   :widths: 15 45 40
   :header-rows: 1

   * - Status
     - When Triggered
     - Client Behavior
   * - ``200 OK``
     - Normal Inertia page response for initial navigation or subsequent XHR visits (see ``src/py/litestar_vite/inertia/response.py``).
     - Inertia unpacks page JSON props and swaps the page component without a full browser reload.
   * - ``204 No Content``
     - Background actions or Precognition pre-validation requests where validation succeeded without errors (asserted in ``src/js/src/inertia-helpers/index.ts`` via ``Precognition-Success: true``).
     - Inertia leaves the current component and scroll position untouched; Precognition marks validated fields valid.
   * - ``303 See Other``
     - Form submissions using ``PUT``, ``PATCH``, or ``DELETE`` (or validation failures redirected back via ``src/py/litestar_vite/inertia/response.py``).
     - Automatically converts the subsequent redirect navigation to a ``GET`` request in the browser.
   * - ``409 Conflict``
     - Asset version hash mismatch between client ``X-Inertia-Version`` and current Vite manifest (see :ref:`inertia-version-checking`).
     - Inertia intercepts the response and triggers a full hard browser reload to download fresh frontend assets.
   * - ``422 Unprocessable Entity``
     - Server-side validation errors raised by Litestar DTO or handler validation (handled in ``src/py/litestar_vite/inertia/exception_handler.py`` and Precognition validation).
     - Inertia maps returned error bags into form component ``errors`` props or Precognition field error states.

.. _inertia-version-checking:

Version Checking
----------------

Inertia uses asset versioning to detect outdated clients:

1. Client sends ``X-Inertia-Version`` header
2. Server compares with current manifest hash
3. On mismatch, server returns ``409 Conflict``
4. Client performs full page reload

Litestar-Vite automatically handles versioning using the Vite manifest.


Page Object Schema
------------------

The Inertia page object represents the server-rendered payload delivered to the client on initial load
(via the script transport) and on XHR visits. In Litestar, this payload is modeled by the ``PageProps``
dataclass (``src/py/litestar_vite/inertia/types.py:257-316``).

On the wire, Python ``snake_case`` attribute names are automatically converted to ``camelCase`` keys by
``to_inertia_dict()`` (citing ``src/py/litestar_vite/inertia/types.py:39-54``).

Top-Level Fields
~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 22 26 14 38
   :header-rows: 1

   * - Wire Key (camelCase)
     - Type
     - Required
     - Description
   * - ``component``
     - ``string``
     - Yes
     - Name of the target page component (Python: ``component``).
   * - ``props``
     - ``object``
     - Yes
     - Data dictionary passed as component props (Python: ``props``).
   * - ``url``
     - ``string``
     - Yes
     - Current request URL path and query parameters (Python: ``url``).
   * - ``version``
     - ``string | null``
     - Yes
     - Current asset version hash for cache validation (Python: ``version``).
   * - ``encryptHistory``
     - ``boolean``
     - No
     - Encrypt history state in browser history (Python: ``encrypt_history``). See :doc:`history-encryption`.
   * - ``clearHistory``
     - ``boolean``
     - No
     - Clear existing browser history state when navigating (Python: ``clear_history``).
   * - ``mergeProps``
     - ``string[] | null``
     - No
     - Prop keys to shallow-merge with existing page props (Python: ``merge_props``). See :doc:`merging-props`.
   * - ``prependProps``
     - ``string[] | null``
     - No
     - Prop array keys to prepend to existing lists (Python: ``prepend_props``). See :doc:`merging-props`.
   * - ``deepMergeProps``
     - ``string[] | null``
     - No
     - Prop object keys to merge recursively (Python: ``deep_merge_props``). See :doc:`merging-props`.
   * - ``matchPropsOn``
     - ``string[] | null``
     - No
     - Array property keys to match items on when merging (Python: ``match_props_on``). See :doc:`merging-props`.
   * - ``deferredProps``
     - ``Record<string, string[]> | null``
     - No
     - Deferred prop keys grouped by fetch group (Python: ``deferred_props``). See :doc:`deferred-props`.
   * - ``onceProps``
     - ``Record<string, Record<string, any>> | null``
     - No
     - Once-prop values and client cache keys (Python: ``once_props``). See :doc:`once-props`.
   * - ``scrollProps``
     - ``Record<string, ScrollPropsConfig> | null``
     - No
     - Scroll region reset and preservation configs (Python: ``scroll_props``). See :doc:`infinite-scroll`.
   * - ``flash``
     - ``Record<string, string[]>``
     - No
     - Flashed session messages scoped by category (Python: ``flash``, defaults to ``{}``). See :doc:`flash-data`.

Omission Rules
~~~~~~~~~~~~~~

The serialization pipeline implements two omission rules:

1. **None-value omission**: Optional fields with a ``None`` value are dropped entirely from the serialized
   dictionary (``src/py/litestar_vite/inertia/types.py:103-104``).
2. **Boolean false suppression**: ``encryptHistory`` and ``clearHistory`` are deleted when ``False``
   (``src/py/litestar_vite/inertia/types.py:312-315``). On the wire, absent and ``false`` are identical;
   only ``true`` is ever emitted.

Scroll Configuration
~~~~~~~~~~~~~~~~~~~~

The ``scrollProps`` mapping uses ``ScrollPropsConfig`` (``src/py/litestar_vite/inertia/types.py:134-141``)
with the shape:

- ``pageName``: Query parameter for pagination (default: ``"page"``)
- ``currentPage``: Current page number (integer)
- ``previousPage``: Previous page number or ``null``
- ``nextPage``: Next page number or ``null``

This matches the client-side ``ScrollProps`` TypeScript interface defined at
``src/js/src/inertia-helpers/index.ts:323-332``.

Complete Response Payload Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json

   {
     "component": "Users/Index",
     "props": {
       "users": [
         {"id": 1, "name": "Alice"}
       ]
     },
     "url": "/users?page=1",
     "version": "b4a8e91",
     "encryptHistory": true,
     "flash": {
       "success": ["User created successfully"]
     },
     "deferredProps": {
       "default": ["analytics", "activityLog"]
     },
     "onceProps": {
       "userPermissions": {
         "can_edit": true,
         "cache_key": "perm_u1"
       }
     },
     "scrollProps": {
       "usersList": {
         "pageName": "page",
         "currentPage": 1,
         "previousPage": null,
         "nextPage": 2
       }
     }
   }

Litestar Integration
--------------------

Litestar-Vite implements the protocol through:

- **InertiaPlugin**: Middleware for request/response handling
- **InertiaResponse**: Response class for page data
- **InertiaMiddleware**: Header parsing and validation
- **ViteAssetLoader**: Asset versioning via manifest hash

.. code-block:: python

   from typing import Any

   from litestar import get

   # Simple Inertia route
   @get("/dashboard", component="Dashboard")
   async def dashboard() -> dict[str, Any]:
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

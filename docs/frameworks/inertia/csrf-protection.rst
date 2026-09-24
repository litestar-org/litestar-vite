===============
CSRF Protection
===============

Configure CSRF protection for Inertia applications.

.. seealso::
   Official Inertia.js docs: `CSRF Protection <https://inertiajs.com/csrf-protection>`_

Overview
--------

Unsafe requests need a CSRF token. ``litestar-vite`` exposes that token through
page state, so browser code does not need to read the CSRF cookie directly.

Recommended Litestar Configuration
----------------------------------

For ``litestar-vite`` helpers and generated Inertia scaffolds, the minimal
recommended setup is:

.. code-block:: python

   from litestar import Litestar
   from litestar.config.csrf import CSRFConfig

   app = Litestar(
       csrf_config=CSRFConfig(
           secret="your-secret-key-min-32-chars-long",
           cookie_httponly=True,
       ),
   )

This keeps Litestar's default cookie/header names (``csrftoken`` and
``x-csrftoken``) and works with ``cookie_httponly=True`` because the browser
reads the token from injected page state instead of the cookie itself.

.. note::
   If you intentionally use a client library that reads the CSRF cookie directly,
   such as a legacy Axios XSRF-cookie setup, keep ``cookie_httponly=False`` and
   align the cookie/header names explicitly for that client. Consumers of
   ``litestar-vite-plugin/helpers`` do not need manual alignment: configured names
   are injected into browser state and used automatically.

Token in Templates
------------------

The CSRF token is available in templates:

.. code-block:: html

   <!-- Hidden input for traditional forms -->
   {{ csrf_input }}

   <!-- Or access the token directly -->
   <meta name="csrf-token" content="{{ csrf_token }}">

Token in Props
--------------

The ``csrf_token`` prop is automatically included in shared props:

.. code-block:: tsx

   import { usePage } from "@inertiajs/react";

   interface SharedProps {
     csrf_token: string;
     // ...other props
   }

   const { csrf_token } = usePage<SharedProps>().props;

Inertia Client Visits
---------------------

The generated Inertia templates wire Litestar's default CSRF header into global
visit options so unsafe Inertia requests work with ``cookie_httponly=True``:

.. code-block:: typescript

   import { createInertiaApp } from "@inertiajs/react";
   import { csrfHeaders } from "litestar-vite-plugin/helpers";

   createInertiaApp({
     defaults: {
       visitOptions: (_href: string, options: Record<string, any>) => ({
         headers: csrfHeaders(options.headers ?? {}),
       }),
     },
     // ...
   });

The same pattern works for ``@inertiajs/vue3`` and ``@inertiajs/svelte``.

SPA Mode
--------

In SPA mode, CSRF tokens are injected via HTML transformation:

.. code-block:: javascript

   // Available as a global variable
   const token = window.__LITESTAR_CSRF__;

Configure the variable name:

.. code-block:: python

   from litestar_vite.config import SPAConfig

   ViteConfig(
       spa=SPAConfig(
           inject_csrf=True,
           csrf_var_name="__LITESTAR_CSRF__",  # Default
       ),
   )

Token Resolution Order
----------------------

When ``getCsrfToken()`` is invoked on the client, it searches for a valid CSRF token in a strict,
deterministic sequence:

1. **SPA global injection short-circuit**: Checks ``window.__LITESTAR_CSRF__``. If present and truthy,
   this value is **returned immediately**, short-circuiting all subsequent checks.
2. **Multi-source fallback chain**: If ``window.__LITESTAR_CSRF__`` is not set, the helper evaluates
   three candidate sources in order using nullish coalescing (``metaToken ?? inertiaToken ?? cookieToken ?? ""``):

   a. **HTML meta tag**: Reads the ``content`` attribute of ``document.querySelector('meta[name="csrf-token"]')``.
   b. **Inertia page state**: Evaluates three potential Inertia token locations in order:

      - Global page state: ``window.__INERTIA_PAGE__.props.csrf_token`` (if present as a string).
      - Default script transport: Parses JSON from ``document.getElementById("app_page")`` and reads ``page.props.csrf_token`` (parse failures fall through).
      - Compatibility container: Parses JSON from ``document.querySelector("[data-page]")``. Note: if the element has ``data-page="app"`` (the sentinel pointer used in script-element mode), it is explicitly **skipped** to avoid JSON parse errors.

   c. **Cookie fallback**: Inspects browser cookies in precedence order:

      - Custom cookie name from ``window.__LITESTAR_CSRF_COOKIE_NAME__``.
      - Explicit ``cookieName`` option passed to the helper.
      - Default Litestar cookie name: ``csrftoken``.
      - Standard legacy cookie name: ``XSRF-TOKEN``.

3. **Empty string fallback**: If no token is found in any source, ``getCsrfToken()`` returns an empty string
   (``""``) rather than throwing or returning ``undefined``.

Header Name Resolution
~~~~~~~~~~~~~~~~~~~~~~

Header names are resolved independently via ``getCsrfHeaderName()``. It prefers the configured header name in
``window.__LITESTAR_CSRF_HEADER_NAME__`` and falls back to the default ``"X-CSRFToken"`` header name.

CSRF Helper Functions
---------------------

The ``litestar-vite-plugin/helpers`` package provides utility functions for CSRF token handling:

.. code-block:: typescript

   import {
     csrfFetch,
     csrfHeaders,
     getCsrfHeaderName,
     getCsrfToken,
   } from 'litestar-vite-plugin/helpers';

   // Get CSRF token following the resolution order documented above (global, meta, Inertia, or cookie)
   const token = getCsrfToken();

   // Get the configured header name and a ready-to-use headers object
   const headerName = getCsrfHeaderName();
   const headers = csrfHeaders();

   const data = { title: "Test" };

   // Make a fetch request with CSRF token automatically included
   await csrfFetch('/api/submit', {
     method: 'POST',
     body: JSON.stringify(data),
   });

These helpers work in both SPA and template modes, automatically detecting the
token source. When ``CSRFConfig`` customizes ``cookie_name`` or ``header_name``,
the HTML handler injects ``window.__LITESTAR_CSRF_COOKIE_NAME__`` and
``window.__LITESTAR_CSRF_HEADER_NAME__`` alongside the token, so no separate
JavaScript configuration is required.

Legacy Cookie-Readable Clients
------------------------------

If you intentionally rely on a client that reads the CSRF cookie directly,
configure the middleware for that flow explicitly:

.. code-block:: python

   from litestar.config.csrf import CSRFConfig

   CSRFConfig(
       secret="your-secret-key-min-32-chars-long",
       cookie_name="XSRF-TOKEN",
       header_name="X-XSRF-TOKEN",
       cookie_httponly=False,
   )

The Litestar Vite helpers automatically follow those configured names. Manual
cookie/header alignment is still required for clients that bypass the helpers,
such as a raw Axios XSRF-cookie configuration.

Excluding Routes
----------------

Exclude specific routes from CSRF protection:

.. code-block:: python

   from litestar.config.csrf import CSRFConfig

   CSRFConfig(
       secret="...",
       exclude=["/api/webhook", "/api/health"],
   )

Troubleshooting
---------------

**403 Forbidden errors**:

1. Verify the request sends Litestar's default CSRF header (``x-csrftoken`` / ``X-CSRFToken``)
2. Verify the CSRF cookie is set on the correct domain/path
3. If you use a cookie-readable client, verify ``cookie_httponly=False``
4. If you customized ``header_name``, the provided helpers follow it
   automatically. For hand-written fetch/XHR clients that do not use
   ``csrfHeaders()`` or ``csrfFetch()``, make sure the client sends the same
   header.

**Token not found**:

1. Ensure CSRF middleware is registered
2. Check the token is present in injected page state (global, meta tag, or Inertia props)
3. Verify the token is included in the request headers

See Also
--------

- :doc:`forms` - Form handling
- `Litestar CSRF docs <https://docs.litestar.dev/latest/usage/middleware/builtin-middleware.html#csrf>`_

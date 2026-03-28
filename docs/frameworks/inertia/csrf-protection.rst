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
   align the cookie/header names explicitly for that client.

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
       visitOptions: (_href, options) => ({
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

CSRF Helper Functions
---------------------

The ``litestar-vite-plugin/helpers`` package provides utility functions for CSRF token handling:

.. code-block:: typescript

   import { getCsrfToken, csrfHeaders, csrfFetch } from 'litestar-vite-plugin/helpers';

   // Get CSRF token (from window.__LITESTAR_CSRF__, meta tag, or Inertia props)
   const token = getCsrfToken();

   // Get headers object with Litestar's default X-CSRFToken header
   const headers = csrfHeaders();

   // Make a fetch request with CSRF token automatically included
   await csrfFetch('/api/submit', {
     method: 'POST',
     body: JSON.stringify(data),
   });

These helpers work in both SPA and template modes, automatically detecting the token source.

Legacy Cookie-Readable Clients
------------------------------

If you intentionally rely on a client that reads the CSRF cookie directly,
configure the middleware for that flow explicitly:

.. code-block:: python

   CSRFConfig(
       secret="your-secret-key-min-32-chars-long",
       cookie_name="XSRF-TOKEN",
       header_name="X-XSRF-TOKEN",
       cookie_httponly=False,
   )

Excluding Routes
----------------

Exclude specific routes from CSRF protection:

.. code-block:: python

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
4. If you customized ``header_name``, make sure your client sends the same header

**Token not found**:

1. Ensure CSRF middleware is registered
2. Check the token is present in injected page state (global, meta tag, or Inertia props)
3. Verify the token is included in the request headers

See Also
--------

- :doc:`forms` - Form handling
- `Litestar CSRF docs <https://docs.litestar.dev/latest/usage/middleware/builtin-middleware.html#csrf>`_

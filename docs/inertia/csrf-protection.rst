===============
CSRF Protection
===============

Configure CSRF protection for Inertia applications.

.. seealso::
   Official Inertia.js docs: `CSRF Protection <https://inertiajs.com/csrf-protection>`_

Overview
--------

Inertia uses Axios for XHR requests, which automatically handles CSRF tokens
via the ``XSRF-TOKEN`` cookie pattern.

Litestar Configuration
----------------------

Configure Litestar's CSRF middleware to work with Inertia:

.. code-block:: python

   from litestar import Litestar
   from litestar.config.csrf import CSRFConfig

   app = Litestar(
       csrf_config=CSRFConfig(
           secret="your-secret-key-min-32-chars-long",
           cookie_name="XSRF-TOKEN",      # Axios looks for this
           header_name="X-XSRF-TOKEN",    # Axios sends this
           cookie_httponly=False,         # Axios needs to read it
       ),
   )

.. warning::
   ``cookie_httponly=False`` is required for Axios to read the token.
   This is safe because the token is not a session identifier.

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

Axios Configuration
-------------------

Inertia's Axios instance is pre-configured, but for manual requests:

.. code-block:: typescript

   import axios from "axios";

   axios.defaults.xsrfCookieName = "XSRF-TOKEN";
   axios.defaults.xsrfHeaderName = "X-XSRF-TOKEN";

   // Or use the usePage hook
   import { usePage } from "@inertiajs/react";

   const { csrf_token } = usePage().props;
   axios.defaults.headers.common["X-XSRF-TOKEN"] = csrf_token;

SPA Mode
--------

In SPA mode, CSRF tokens are injected via ``HtmlTransformer``:

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

Form Submissions
----------------

Inertia form helpers automatically include the CSRF token:

.. code-block:: tsx

   const { post } = useForm({ name: "" });

   function submit(e) {
     e.preventDefault();
     post("/users");  // CSRF token included automatically
   }

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

1. Verify cookie name is ``XSRF-TOKEN``
2. Verify header name is ``X-XSRF-TOKEN``
3. Verify ``cookie_httponly=False``
4. Check cookie is set on the correct domain/path

**Token not found**:

1. Ensure CSRF middleware is registered
2. Check the token cookie exists in browser DevTools
3. Verify the token is included in the request headers

See Also
--------

- :doc:`forms` - Form handling
- `Litestar CSRF docs <https://docs.litestar.dev/latest/usage/middleware/builtin-middleware.html#csrf>`_

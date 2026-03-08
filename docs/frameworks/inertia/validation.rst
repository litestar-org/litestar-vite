==========
Validation
==========

Handle validation errors and error bags with Inertia.

.. seealso::
   Official Inertia.js docs: `Validation <https://inertiajs.com/validation>`_

How Validation Works
--------------------

Inertia expects validation errors to be returned with the next page response.
Litestar-Vite stores errors in the session and includes them in the ``errors``
prop on the next Inertia response.

Backend Usage
-------------

Use the ``error()`` helper for custom validation, then return
``InertiaBack`` or ``InertiaRedirect``:

.. code-block:: python

   from litestar import post
   from litestar.request import Request
   from litestar_vite.inertia import error, InertiaBack, InertiaRedirect

   @post("/users")
   async def create_user(request: Request) -> InertiaBack:
       data = await request.json()

       if await User.email_exists(data["email"]):
           error(request, "email", "Email already exists")
           return InertiaBack(request)

       await User.create(**data)
       return InertiaRedirect(request, "/users")

Errors are available on the frontend as ``page.props.errors``.

Litestar Validation
-------------------

Litestar can validate request bodies with any supported data type (dataclasses,
attrs classes, TypedDicts, Pydantic models, msgspec, and more). Map those
validation errors into ``error()`` calls or return ``InertiaBack`` from an
exception handler to keep the error response in the Inertia flow.

Error Bags
----------

Use error bags to isolate errors for multiple forms:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { useForm } from "@inertiajs/react";

         const form = useForm({ name: "", email: "" });

         form.post("/users", { errorBag: "createUser" });

   .. tab-item:: Vue

      .. code-block:: vue

         <script setup lang="ts">
         import { useForm } from "@inertiajs/vue3";

         const form = useForm({ name: "", email: "" });

         form.post("/users", { errorBag: "createUser" });
         </script>

When using an error bag, errors are nested under ``errors.createUser``.

Displaying Errors
-----------------

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { usePage } from "@inertiajs/react";

         const { errors } = usePage().props;

         {errors.email && <span>{errors.email}</span>}

   .. tab-item:: Vue

      .. code-block:: vue

         <template>
           <span v-if="$page.props.errors.email">{{ $page.props.errors.email }}</span>
         </template>

Clearing Errors
---------------

Clear errors after handling them:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         form.clearErrors();

   .. tab-item:: Vue

      .. code-block:: typescript

         form.clearErrors();

See Also
--------

- :doc:`forms` - Form submissions
- :doc:`flash-data` - Flash messages
- :doc:`partial-reloads` - Reset errors during reloads

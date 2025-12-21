===========
Precognition
===========

Real-time form validation without executing handler side effects.

.. seealso::
   Official Laravel Precognition docs: `Precognition <https://laravel.com/docs/precognition>`_

Overview
--------

Precognition allows you to validate form inputs in real-time as users type,
without executing the route handler's main logic. This provides instant feedback
while preventing side effects like database writes or emails.

The protocol works by:

1. Frontend sends a validation-only request with ``Precognition: true`` header
2. Server runs DTO/Pydantic validation but skips the handler body
3. Returns 204 on success or 422 with validation errors
4. Handler only executes on final form submission (without Precognition header)

Configuration
-------------

Enable Precognition support in your ``InertiaConfig``:

.. code-block:: python

   from litestar_vite.config import InertiaConfig

   InertiaConfig(
       precognition=True,  # Enable Precognition support
   )

When enabled, the plugin automatically formats validation errors in Laravel's
format (422 responses). To prevent handler execution on successful validation
(204 responses), add the ``@precognition`` decorator to your route handlers.

Backend Usage
-------------

Add the ``@precognition`` decorator to route handlers that should support
real-time validation:

.. code-block:: python

   from litestar import post
   from litestar_vite.inertia import precognition, InertiaRedirect

   @post("/users")
   @precognition
   async def create_user(request: Request, data: UserCreate) -> InertiaRedirect:
       # This code only runs for actual form submissions
       # Precognition validation requests return 204 automatically
       user = await User.create(**data.model_dump())
       return InertiaRedirect(request, f"/users/{user.id}")

The decorator:

- Returns 204 No Content with ``Precognition-Success: true`` when validation passes
- Skips the handler body entirely for Precognition requests
- Allows normal execution for regular requests

Validation errors are formatted automatically by the exception handler.

Frontend Usage
--------------

Use the official ``laravel-precognition-vue`` or ``laravel-precognition-react``
libraries on the frontend:

.. tab-set::

   .. tab-item:: React

      Install the library:

      .. code-block:: bash

         npm install laravel-precognition-react

      Use the form helper:

      .. code-block:: tsx

         import { useForm } from "laravel-precognition-react";

         export default function CreateUser() {
           const form = useForm("post", "/users", {
             name: "",
             email: "",
           });

           function submit(e: React.FormEvent) {
             e.preventDefault();
             form.submit();
           }

           return (
             <form onSubmit={submit}>
               <input
                 value={form.data.name}
                 onChange={(e) => form.setData("name", e.target.value)}
                 onBlur={() => form.validate("name")}  // Validate on blur
               />
               {form.errors.name && <span>{form.errors.name}</span>}

               <input
                 value={form.data.email}
                 onChange={(e) => form.setData("email", e.target.value)}
                 onBlur={() => form.validate("email")}
               />
               {form.errors.email && <span>{form.errors.email}</span>}

               <button disabled={form.processing}>Create</button>
             </form>
           );
         }

   .. tab-item:: Vue

      Install the library:

      .. code-block:: bash

         npm install laravel-precognition-vue

      Use the form composable:

      .. code-block:: vue

         <script setup lang="ts">
         import { useForm } from "laravel-precognition-vue";

         const form = useForm("post", "/users", {
           name: "",
           email: "",
         });

         function submit() {
           form.submit();
         }
         </script>

         <template>
           <form @submit.prevent="submit">
             <input
               v-model="form.name"
               @change="form.validate('name')"
             />
             <span v-if="form.errors.name">{{ form.errors.name }}</span>

             <input
               v-model="form.email"
               @change="form.validate('email')"
             />
             <span v-if="form.errors.email">{{ form.errors.email }}</span>

             <button :disabled="form.processing">Create</button>
           </form>
         </template>

Partial Field Validation
------------------------

Precognition supports validating individual fields via the
``Precognition-Validate-Only`` header. The frontend libraries handle this
automatically when you call ``form.validate("fieldName")``.

The server only returns errors for the specified fields, reducing noise
during real-time validation.

Request Properties
------------------

``InertiaRequest`` provides properties for Precognition:

.. code-block:: python

   request.is_precognition  # True if Precognition header present
   request.precognition_validate_only  # Set of field names to validate

Rate Limiting
-------------

.. warning::
   Real-time validation can generate many requests. Consider throttling.

Laravel has no official rate limiting solution for Precognition. The frontend
libraries include debouncing (typically 300-500ms), but you should still
consider server-side protection:

- **Separate rate limits**: Consider higher limits for Precognition requests
- **Field-level throttling**: Limit requests per field per session
- **Abuse prevention**: Monitor for excessive validation attempts

Example rate limiting approach:

.. code-block:: python

   from litestar.middleware.rate_limit import RateLimitConfig

   # You could check for Precognition header in a custom rate limiter
   # to apply different limits for validation vs. submission requests

Error Format
------------

Precognition responses use Laravel's validation error format for compatibility:

.. code-block:: json

   {
     "message": "The given data was invalid.",
     "errors": {
       "email": ["The email field is required."],
       "password": ["The password must be at least 8 characters."]
     }
   }

This format is expected by the ``laravel-precognition-vue`` and
``laravel-precognition-react`` libraries.

TypeScript Types
----------------

Types are available from the plugin:

.. code-block:: typescript

   import {
     PrecognitionHeaders,
     PrecognitionValidationErrors,
     PrecognitionFormConfig,
     isPrecognitionSuccess,
     isPrecognitionError,
     extractPrecognitionErrors,
   } from "litestar-vite-plugin/inertia-helpers";

   // Check response types
   if (isPrecognitionSuccess(response)) {
     // Validation passed (204)
   }

   if (isPrecognitionError(response)) {
     const errors = await extractPrecognitionErrors(response);
     console.log(errors.errors);  // { email: ["..."], ... }
   }

See Also
--------

- :doc:`forms` - Form handling basics
- `Laravel Precognition <https://laravel.com/docs/precognition>`_ - Official protocol docs
- `laravel-precognition-vue <https://github.com/laravel/precognition>`_ - Vue frontend library
- `laravel-precognition-react <https://github.com/laravel/precognition>`_ - React frontend library

==========
Flash Data
==========

Send one-time messages that disappear after display.

.. seealso::
   Official Inertia.js docs: `Flash Data <https://inertiajs.com/flash-data>`_

What Is Flash Data?
-------------------

Flash data is short-lived state (like success or error messages) that is only
meant to be displayed once. Flash messages are removed after they are read,
so they do not persist in browser history state.

Backend Usage
-------------

Use the ``flash()`` helper to queue messages for the next Inertia response:

.. code-block:: python

   from litestar import post
   from litestar.request import Request
   from litestar_vite.inertia import flash, InertiaRedirect

   @post("/users")
   async def create_user(request: Request, data: UserCreate) -> InertiaRedirect:
       user = await User.create(**data.dict())
       flash(request, "User created successfully!", "success")
       return InertiaRedirect(request, f"/users/{user.id}")

Flash categories are grouped under their category name (``success``, ``error``,
``warning``, ``info``). Each category contains a list of messages.

Frontend Usage
--------------

Flash data is available on the page object:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { usePage } from "@inertiajs/react";

         export default function Layout({ children }) {
           const { flash } = usePage();

           return (
             <div>
               {flash.success?.map((message) => (
                 <div key={message} className="alert alert-success">
                   {message}
                 </div>
               ))}
               {children}
             </div>
           );
         }

   .. tab-item:: Vue

      .. code-block:: vue

         <script setup lang="ts">
         import { usePage } from "@inertiajs/vue3";

         const { flash } = usePage();
         </script>

         <template>
           <div>
             <div
               v-for="message in flash.success || []"
               :key="message"
               class="alert alert-success"
             >
               {{ message }}
             </div>
             <slot />
           </div>
         </template>

Client-Side Flash Messages
--------------------------

You can also set flash data on the client without a server round trip:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { router } from "@inertiajs/react";

         router.flash((current) => ({
           ...current,
           info: ["Profile updated"],
         }));

   .. tab-item:: Vue

      .. code-block:: typescript

         import { router } from "@inertiajs/vue3";

         router.flash((current) => ({
           ...current,
           info: ["Profile updated"],
         }));

Typing Flash Data
-----------------

Add custom types for flash data in TypeScript:

.. code-block:: typescript

   declare module "@inertiajs/core" {
     interface Page {
       flash: {
         success?: string[];
         error?: string[];
         warning?: string[];
         info?: string[];
       };
     }
   }

See Also
--------

- :doc:`forms` - Form submissions and redirects
- :doc:`validation` - Validation error handling
- :doc:`partial-reloads` - Reset flash on reloads

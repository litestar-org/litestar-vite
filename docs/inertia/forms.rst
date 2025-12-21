=====
Forms
=====

Handle form submissions and validation with Inertia.

.. seealso::
   Official Inertia.js docs: `Forms <https://inertiajs.com/forms>`_

Form Submissions
----------------

Inertia handles forms via XHR. The client-side form helpers manage state,
validation errors, and submissions.

Backend Handler
~~~~~~~~~~~~~~~

.. code-block:: python

   from litestar import post
   from litestar.request import Request
   from litestar_vite.inertia import InertiaRedirect, error

   @post("/users")
   async def create_user(request: Request, data: UserCreate) -> InertiaRedirect:
       # Validation errors are available for any Litestar-supported data type
       user = await User.create(**data.dict())
       return InertiaRedirect(request, f"/users/{user.id}")

Frontend Form
~~~~~~~~~~~~~

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { useForm } from "@inertiajs/react";

         export default function CreateUser() {
           const { data, setData, post, processing, errors } = useForm({
             name: "",
             email: "",
           });

           function submit(e: React.FormEvent) {
             e.preventDefault();
             post("/users");
           }

           return (
             <form onSubmit={submit}>
               <input
                 value={data.name}
                 onChange={(e) => setData("name", e.target.value)}
               />
               {errors.name && <span>{errors.name}</span>}

               <input
                 value={data.email}
                 onChange={(e) => setData("email", e.target.value)}
               />
               {errors.email && <span>{errors.email}</span>}

               <button disabled={processing}>Create</button>
             </form>
           );
         }

   .. tab-item:: Vue

      .. code-block:: vue

         <script setup lang="ts">
         import { useForm } from "@inertiajs/vue3";

         const form = useForm({
           name: "",
           email: "",
         });

         function submit() {
           form.post("/users");
         }
         </script>

         <template>
           <form @submit.prevent="submit">
             <input v-model="form.name" />
             <span v-if="form.errors.name">{{ form.errors.name }}</span>

             <input v-model="form.email" />
             <span v-if="form.errors.email">{{ form.errors.email }}</span>

             <button :disabled="form.processing">Create</button>
           </form>
         </template>

Validation, Flash, and Uploads
-------------------------------

Validation errors, flash messages, and file uploads have dedicated guides with
full examples and patterns:

- :doc:`validation` - Error handling and error bags
- :doc:`flash-data` - One-time messaging patterns
- :doc:`file-uploads` - Multipart uploads and progress

See Also
--------

- :doc:`redirects` - Post-redirect-get pattern
- :doc:`validation` - Validation errors and error bags
- :doc:`flash-data` - Flash messages
- :doc:`file-uploads` - Upload handling

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
       # Validation errors are automatically available via Pydantic
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

Validation Errors
-----------------

Set validation errors using the ``error()`` helper:

.. code-block:: python

   from litestar_vite.inertia import error, InertiaBack

   @post("/users")
   async def create_user(request: Request) -> InertiaBack:
       data = await request.json()

       # Custom validation
       if await User.email_exists(data["email"]):
           error(request, "email", "Email already exists")
           return InertiaBack(request)

       await User.create(**data)
       return InertiaRedirect(request, "/users")

Errors are available in the ``errors`` prop on the frontend.

Error Bags
----------

Use error bags to scope validation errors:

.. code-block:: python

   # Backend: errors are scoped by the X-Inertia-Error-Bag header
   # Frontend sends this header automatically when using form.setError()

Flash Messages
--------------

Add flash messages with the ``flash()`` helper:

.. code-block:: python

   from litestar_vite.inertia import flash, InertiaRedirect

   @post("/users")
   async def create_user(request: Request, data: UserCreate) -> InertiaRedirect:
       user = await User.create(**data.dict())
       flash(request, "User created successfully!", "success")
       return InertiaRedirect(request, f"/users/{user.id}")

Flash messages are available in the ``flash`` prop:

.. code-block:: tsx

   interface Props {
     flash: {
       success?: string[];
       error?: string[];
       info?: string[];
     };
   }

   export default function Layout({ flash, children }: Props) {
     return (
       <div>
         {flash.success?.map((msg) => (
           <div className="alert-success">{msg}</div>
         ))}
         {children}
       </div>
     );
   }

File Uploads
------------

Use FormData for file uploads on the frontend:

.. code-block:: tsx

   const { data, setData, post } = useForm({
     name: "",
     avatar: null as File | null,
   });

   function submit(e: React.FormEvent) {
     e.preventDefault();
     post("/users", {
       forceFormData: true,  // Required for file uploads
     });
   }

See Also
--------

- :doc:`redirects` - Post-redirect-get pattern
- `Inertia.js Forms <https://inertiajs.com/forms>`_ - Official docs
- `Inertia.js Validation <https://inertiajs.com/validation>`_ - Validation docs

=====
Pages
=====

Define Inertia page components in your route handlers.

.. seealso::
   Official Inertia.js docs: `Pages <https://inertiajs.com/pages>`_

Defining Pages
--------------

Use the ``component`` parameter in your route decorator:

.. code-block:: python

   from typing import Any

   from litestar import get

   @get("/", component="Home")
   async def home() -> dict[str, Any]:
       return {"message": "Welcome!"}

   @get("/dashboard", component="Dashboard")
   async def dashboard() -> dict[str, Any]:
       return {"stats": {"users": 100, "sales": 50}}

The ``component`` value maps to your frontend page component path
(e.g., ``pages/Home.tsx`` or ``pages/Dashboard.vue``).

Alternative Syntax
------------------

You can also use ``page`` instead of ``component``:

.. code-block:: python

   from typing import Any

   from litestar import get

   @get("/", page="Home")
   async def home() -> dict[str, Any]:
       return {"message": "Welcome!"}

Props
-----

The dictionary returned from your handler becomes the page props:

.. code-block:: python

   from typing import Any

   from litestar import get

   @get("/users/{user_id:int}", component="Users/Show")
   async def show_user(user_id: int) -> dict[str, Any]:
       user = await User.get(user_id)
       return {
           "user": {
               "id": user.id,
               "name": user.name,
               "email": user.email,
           },
       }

Frontend Usage
--------------

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         // pages/Users/Show.tsx
         interface Props {
           user: { id: number; name: string; email: string };
         }

         export default function Show({ user }: Props) {
           return (
             <div>
               <h1>{user.name}</h1>
               <p>{user.email}</p>
             </div>
           );
         }

   .. tab-item:: Vue

      .. code-block:: vue

         <!-- pages/Users/Show.vue -->
         <script setup lang="ts">
         defineProps<{
           user: { id: number; name: string; email: string };
         }>();
         </script>

         <template>
           <div>
             <h1>{{ user.name }}</h1>
             <p>{{ user.email }}</p>
           </div>
         </template>

   .. tab-item:: Svelte

      .. code-block:: svelte

         <!-- pages/Users/Show.svelte -->
         <script lang="ts">
         interface Props {
           user: { id: number; name: string; email: string };
         }
         let { user }: Props = $props();
         </script>

         <div>
           <h1>{user.name}</h1>
           <p>{user.email}</p>
         </div>

Nested Components
-----------------

Use path separators for nested page organization:

.. code-block:: python

   from typing import Any

   from litestar import get

   @get("/users", component="Users/Index")
   async def list_users() -> dict[str, Any]: ...

   @get("/users/{id}", component="Users/Show")
   async def show_user(id: int) -> dict[str, Any]: ...

   @get("/users/{id}/edit", component="Users/Edit")
   async def edit_user(id: int) -> dict[str, Any]: ...

See Also
--------

- :doc:`responses` - InertiaResponse for advanced usage
- :doc:`typed-page-props` - TypeScript integration for props
- :doc:`/frameworks/inertia` - Framework setup guides

================
Typed Page Props
================

Type-safe props for your Inertia page components.

Overview
--------

Litestar-Vite generates TypeScript types for your page props:

.. code-block:: python

   @get("/dashboard", component="Dashboard")
   async def dashboard() -> dict:
       return {
           "userCount": 42,
           "recentActivity": [...],
       }

Generates:

.. code-block:: typescript

   interface PageProps {
     Dashboard: {
       userCount: number;
       recentActivity: any[];
     };
   }

Using PageProps
---------------

Import and use the generated types:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import type { PageProps } from "@/generated/page-props";

         export default function Dashboard(props: PageProps["Dashboard"]) {
           return (
             <div>
               <h1>Dashboard</h1>
               <p>Users: {props.userCount}</p>
               {props.recentActivity.map((item) => (
                 <ActivityItem key={item.id} item={item} />
               ))}
             </div>
           );
         }

   .. tab-item:: Vue

      .. code-block:: vue

         <script setup lang="ts">
         import type { PageProps } from "@/generated/page-props";

         const props = defineProps<PageProps["Dashboard"]>();
         </script>

         <template>
           <div>
             <h1>Dashboard</h1>
             <p>Users: {{ props.userCount }}</p>
           </div>
         </template>

   .. tab-item:: Svelte

      .. code-block:: svelte

         <script lang="ts">
         import type { PageProps } from "@/generated/page-props";

         let { userCount, recentActivity }: PageProps["Dashboard"] = $props();
         </script>

         <div>
           <h1>Dashboard</h1>
           <p>Users: {userCount}</p>
         </div>

Type Inference
--------------

Types are inferred from your Python return types:

.. code-block:: python

   from dataclasses import dataclass

   @dataclass
   class DashboardStats:
       user_count: int
       active_sessions: int
       revenue: float

   @get("/dashboard", component="Dashboard")
   async def dashboard() -> dict:
       stats = DashboardStats(user_count=42, active_sessions=10, revenue=1234.56)
       return {"stats": stats}

Generates types based on serialization output.

Nested Components
-----------------

Use path separators for component organization:

.. code-block:: python

   @get("/users", component="Users/Index")
   async def list_users() -> dict: ...

   @get("/users/{id}", component="Users/Show")
   async def show_user(id: int) -> dict: ...

Access via:

.. code-block:: typescript

   PageProps["Users/Index"]
   PageProps["Users/Show"]

Shared Props Access
-------------------

Access shared props via ``FullSharedProps``:

.. code-block:: typescript

   import type { FullSharedProps, PageProps } from "@/generated/page-props";

   // Page-specific props + shared props
   type DashboardProps = PageProps["Dashboard"] & FullSharedProps;

   export default function Dashboard(props: DashboardProps) {
     const { userCount, flash, auth } = props;
     return ...;
   }

With usePage Hook
-----------------

Using the Inertia ``usePage`` hook:

.. code-block:: tsx

   import { usePage } from "@inertiajs/react";
   import type { PageProps, FullSharedProps } from "@/generated/page-props";

   type AllProps = PageProps["Dashboard"] & FullSharedProps;

   export default function Dashboard() {
     const { props } = usePage<{ props: AllProps }>();
     return <p>Users: {props.userCount}</p>;
   }

Regenerating Types
------------------

Types are regenerated when you run:

.. code-block:: bash

   litestar assets generate-types

Or automatically during build:

.. code-block:: bash

   litestar assets build

Handling Optional Props
-----------------------

Optional props are marked with ``?``:

.. code-block:: python

   @get("/users/{id}", component="Users/Show")
   async def show_user(id: int) -> dict:
       user = await User.get_or_none(id)
       return {
           "user": user,  # Can be None
           "posts": user.posts if user else [],
       }

.. code-block:: typescript

   PageProps["Users/Show"] = {
     user: User | null;
     posts: Post[];
   }

See Also
--------

- :doc:`typescript` - TypeScript overview
- :doc:`shared-props-typing` - Extending SharedProps
- :doc:`type-generation` - Generation configuration

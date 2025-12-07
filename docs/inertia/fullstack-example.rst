=================
Fullstack Example
=================

Learn from a complete production-ready Inertia application.

Litestar Fullstack Inertia
--------------------------

The `litestar-fullstack-inertia <https://github.com/litestar-org/litestar-fullstack-inertia>`_
project is the official reference implementation for building Inertia applications
with Litestar.

.. tip::
   This template demonstrates best practices for production applications.
   Use it as a starting point for your own projects.

Getting Started
---------------

.. code-block:: bash

   # Clone the template
   git clone https://github.com/litestar-org/litestar-fullstack-inertia.git
   cd litestar-fullstack-inertia

   # Install dependencies
   make install

   # Run development server
   make run

Project Structure
-----------------

.. code-block:: text

   litestar-fullstack-inertia/
   ├── src/
   │   └── app/
   │       ├── domain/           # Business logic
   │       │   ├── accounts/     # User accounts
   │       │   ├── teams/        # Team management
   │       │   └── system/       # System utilities
   │       ├── server/           # Litestar server
   │       │   ├── plugins.py    # Plugin configuration
   │       │   └── routes.py     # Route registration
   │       └── lib/              # Shared utilities
   ├── resources/                # Frontend assets
   │   ├── main.ts               # Entry point
   │   ├── pages/                # Inertia page components
   │   └── components/           # Reusable components
   └── templates/
       └── index.html            # Root template

Key Features
------------

**Authentication**

- Session-based authentication
- Login, logout, registration flows
- Password reset functionality
- ``auth`` shared prop pattern

**Team Management**

- Multi-tenant team support
- Team invitation system
- Role-based permissions

**Type Safety**

- Full TypeScript support
- Generated route types
- Generated page prop types
- Extended SharedProps

Best Practices
--------------

**Component kwarg pattern**:

.. code-block:: python

   # Preferred - clean and declarative
   @get("/", component="Home")
   async def home() -> dict:
       return {"message": "Hello"}

   # Instead of
   @get("/")
   async def home() -> InertiaResponse:
       return InertiaResponse(component="Home", props={"message": "Hello"})

**Guard-based sharing**:

.. code-block:: python

   async def auth_guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
       share(connection, "auth", {
           "isAuthenticated": bool(connection.user),
           "user": serialize_user(connection.user),
       })

**Type extension**:

.. code-block:: typescript

   declare module "litestar-vite/inertia" {
     interface User {
       avatarUrl?: string;
       teams: Team[];
     }
     interface SharedProps {
       auth: AuthData;
       currentTeam?: Team;
     }
   }

**Layout pattern**:

.. code-block:: tsx

   // pages/Dashboard.tsx
   import Layout from "@/layouts/AppLayout";

   Dashboard.layout = (page) => <Layout>{page}</Layout>;

   export default function Dashboard({ stats }: Props) {
     return <DashboardContent stats={stats} />;
   }

Related Examples
----------------

Other example projects in the litestar-vite repository:

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Example
     - Description
   * - ``vue-inertia``
     - Vue 3 + Inertia.js
   * - ``react-inertia``
     - React 18 + Inertia.js
   * - ``svelte``
     - SvelteKit + Inertia.js
   * - ``react``
     - React SPA (no Inertia)
   * - ``vue``
     - Vue SPA (no Inertia)

Browse examples: `github.com/litestar-org/litestar-vite/tree/main/examples <https://github.com/litestar-org/litestar-vite/tree/main/examples>`_

See Also
--------

- :doc:`installation` - Getting started
- :doc:`configuration` - Configuration reference
- :doc:`typescript` - TypeScript integration

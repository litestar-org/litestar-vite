===================
Shared Props Typing
===================

TypeScript types for shared data across pages.

Overview
--------

Litestar-Vite generates types for shared props:

- ``GeneratedSharedProps``: Built-in props (flash, errors, csrf_token)
- ``User``: Default user interface (extensible)
- ``AuthData``: Default auth interface (extensible)
- ``SharedProps``: User-extensible interface for ``share()`` data
- ``FullSharedProps``: Combined ``GeneratedSharedProps & SharedProps``

Generated Types
---------------

Default generated ``page-props.ts``:

.. code-block:: typescript

   // Built-in props
   export interface GeneratedSharedProps {
     csrf_token?: string;
     auth?: AuthData;
   }

   // Default user interface - extend via module augmentation
   export interface User {
     id: string;
     email: string;
     name?: string | null;
   }

   // Default auth interface
   export interface AuthData {
     isAuthenticated: boolean;
     user?: User | null;
   }

   // Flash messages
   export interface FlashMessages {
     [category: string]: string[];
   }

   // User-extensible interface
   export interface SharedProps {}

   // Combined type
   export type FullSharedProps = GeneratedSharedProps & SharedProps;

Flash and validation errors are **not** props. Inertia carries them on the page
object itself, so they are typed by ``@inertiajs/core`` rather than generated here:

.. code-block:: typescript

   const page = usePage()

   page.flash          // top-level, NOT page.props.flash
   page.props.errors   // typed by Inertia as Errors & ErrorBag

Errors need nothing extra — Inertia types error values as ``string``, which is
exactly what the runtime sends.

Flash does. Inertia leaves ``page.flash`` as ``{ [key: string]: unknown }`` by
default and exposes a ``flashDataType`` slot to narrow it, so an ``inertia.d.ts``
is generated alongside ``page-props.ts`` to fill that slot:

.. code-block:: typescript

   // generated/inertia.d.ts
   declare module "@inertiajs/core" {
     interface InertiaConfig {
       flashDataType: FlashMessages
     }
   }

With it, ``page.flash.success`` is ``string[]`` instead of ``unknown``. The
declaration is ambient, so ``page-props.ts`` references it directly — that way it
still applies when a ``tsconfig.json`` excludes the generated directory.

Setting ``include_default_flash=False`` skips the declaration entirely.

Extending Interfaces
--------------------

Use TypeScript module augmentation to extend types:

.. code-block:: typescript
   :caption: src/types/shared-props.ts

   // Extend the User interface
   declare module "litestar-vite-plugin/inertia" {
     interface User {
       avatarUrl?: string | null;
       roles: string[];
       createdAt: string;
     }
   }

   // Extend SharedProps for share() data
   declare module "litestar-vite-plugin/inertia" {
     interface SharedProps {
       auth: AuthData;
       locale: string;
       notifications: Notification[];
     }
   }

Then import in your app:

.. code-block:: typescript
   :caption: src/main.ts

   import "./types/shared-props";  // Load augmentations

   // Now User and SharedProps are extended everywhere

Using in Components
-------------------

.. code-block:: tsx

   import { usePage } from "@inertiajs/react";
   import type { FullSharedProps, PageProps } from "@/generated/page-props";

   type Props = PageProps["Dashboard"] & FullSharedProps;

   export default function Dashboard() {
     const { props } = usePage<{ props: Props }>();

     // Type-safe access to shared props
     const { auth, flash, locale } = props;

     return (
       <div>
         {auth.isAuthenticated && (
           <span>Hello, {auth.user?.name}</span>
         )}
         {flash.success?.map((msg) => (
           <Alert type="success">{msg}</Alert>
         ))}
       </div>
     );
   }

Disabling Defaults
------------------

If your user model doesn't match the defaults:

.. code-block:: python

   from litestar_vite.config import InertiaTypeGenConfig

   InertiaConfig(
       type_gen=InertiaTypeGenConfig(
           include_default_auth=False,  # No default User/AuthData
           include_default_flash=True,  # Keep FlashMessages
       ),
   )

Then define your own types:

.. code-block:: typescript

   // Define custom User from scratch
   declare module "litestar-vite-plugin/inertia" {
     interface User {
       uuid: string;         // No id!
       username: string;     // No email!
       permissions: string[];
     }

     interface AuthData {
       loggedIn: boolean;    // Different naming
       currentUser?: User;
     }
   }

Common Patterns
---------------

**Guard-based sharing**:

.. code-block:: python

   # In guard
   share(connection, "auth", {
       "isAuthenticated": bool(connection.user),
       "user": serialize_user(connection.user),
   })

**Middleware sharing**:

.. code-block:: python

   # In middleware
   share(request, "locale", request.headers.get("Accept-Language", "en"))
   share(request, "notifications", get_unread_notifications(request.user))

**Type definition**:

.. code-block:: typescript

   interface SharedProps {
     auth: AuthData;
     locale: string;
     notifications: Array<{
       id: number;
       message: string;
       read: boolean;
     }>;
   }

See Also
--------

- :doc:`shared-data` - Using share()
- :doc:`typed-page-props` - PageProps usage
- :doc:`configuration` - InertiaTypeGenConfig

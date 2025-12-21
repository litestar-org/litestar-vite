==========
Inertia.js
==========

Build modern single-page applications with server-side routing using
`Inertia.js <https://inertiajs.com/>`_.

.. seealso::
   Official Inertia.js docs: `Getting Started <https://inertiajs.com/>`_

Inertia.js is a protocol that lets you build SPAs without building an API.
Your Litestar routes return page components directly, and Inertia handles
the rest - routing, navigation, and state management.

.. tip::
   See `litestar-fullstack-inertia <https://github.com/litestar-org/litestar-fullstack-inertia>`_
   for a complete production example.

Quick Example
-------------

.. code-block:: python

   from typing import Any

   from litestar import Litestar, get
   from litestar_vite import ViteConfig, VitePlugin
   from litestar_vite.inertia import InertiaConfig, InertiaPlugin

   @get("/", component="Home")
   async def home() -> dict[str, Any]:
       return {"message": "Hello, World!"}

   app = Litestar(
       route_handlers=[home],
       plugins=[
           VitePlugin(config=ViteConfig(dev_mode=True, inertia=True)),
       ],
   )

.. toctree::
   :maxdepth: 1
   :caption: Getting Started

   installation
   configuration

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts

   how-it-works

.. toctree::
   :maxdepth: 1
   :caption: The Basics

   pages
   responses
   redirects
   routing
   links
   forms
   file-uploads
   validation

.. toctree::
   :maxdepth: 1
   :caption: Data & Props

   shared-data
   flash-data
   partial-reloads
   deferred-props
   once-props
   merging-props
   load-when-visible
   polling
   prefetching
   infinite-scroll
   remembering-state

.. toctree::
   :maxdepth: 1
   :caption: Security

   csrf-protection
   history-encryption
   precognition

.. toctree::
   :maxdepth: 1
   :caption: Advanced

   templates
   error-handling
   asset-versioning

.. toctree::
   :maxdepth: 1
   :caption: TypeScript Integration

   typescript
   type-generation
   typed-page-props
   shared-props-typing

.. toctree::
   :maxdepth: 1
   :caption: Examples

   fullstack-example

See Also
--------

- :doc:`installation` - Set up Inertia with Litestar
- :doc:`how-it-works` - Protocol and request lifecycle overview

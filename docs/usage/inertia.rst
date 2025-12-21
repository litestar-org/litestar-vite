===================
Inertia Integration
===================

.. note::
   This page has moved to the :doc:`/inertia/index` section for comprehensive documentation.

The Inertia.js documentation has been reorganized into a dedicated section with focused pages:

Getting Started
---------------

- :doc:`/inertia/installation` - Installation and setup
- :doc:`/inertia/configuration` - InertiaConfig reference
- :doc:`/inertia/how-it-works` - Protocol overview

The Basics
----------

- :doc:`/inertia/pages` - Page components
- :doc:`/inertia/responses` - InertiaResponse
- :doc:`/inertia/redirects` - Redirect responses
- :doc:`/inertia/routing` - Routing and named routes
- :doc:`/inertia/forms` - Form handling
- :doc:`/inertia/file-uploads` - File upload patterns
- :doc:`/inertia/validation` - Validation errors and error bags
- :doc:`/inertia/links` - Navigation

Data & Props
------------

- :doc:`/inertia/shared-data` - Shared props
- :doc:`/inertia/flash-data` - Flash messages
- :doc:`/inertia/partial-reloads` - Lazy props and partial reloads
- :doc:`/inertia/deferred-props` - Deferred loading
- :doc:`/inertia/once-props` - Client-cached props
- :doc:`/inertia/merging-props` - Infinite scroll
- :doc:`/inertia/load-when-visible` - Optional props + WhenVisible
- :doc:`/inertia/polling` - Polling updates
- :doc:`/inertia/prefetching` - Prefetching visits
- :doc:`/inertia/infinite-scroll` - Infinite scroll guide
- :doc:`/inertia/remembering-state` - Remembered client state

Security
--------

- :doc:`/inertia/csrf-protection` - CSRF configuration
- :doc:`/inertia/history-encryption` - History encryption
- :doc:`/inertia/precognition` - Precognition validation

TypeScript
----------

- :doc:`/inertia/typescript` - TypeScript integration
- :doc:`/inertia/type-generation` - Type generation config
- :doc:`/inertia/typed-page-props` - Typed page props
- :doc:`/inertia/shared-props-typing` - Shared props typing

Quick Reference
---------------

**Installation**:

.. code-block:: bash

   pip install litestar-vite

**Basic Usage**:

.. code-block:: python

   from typing import Any

   from litestar import Litestar, get
   from litestar_vite import ViteConfig, VitePlugin

   @get("/", component="Home")
   async def home() -> dict[str, Any]:
       return {"message": "Hello, World!"}

   app = Litestar(
       route_handlers=[home],
       plugins=[
           VitePlugin(config=ViteConfig(dev_mode=True, inertia=True)),
       ],
   )

**Helpers**:

.. code-block:: python

   from litestar_vite.inertia import (
       share,      # Share props across requests
       flash,      # Flash messages
       error,      # Validation errors
       lazy,       # Lazy props (partial reloads)
       defer,      # Deferred props (auto-load)
       merge,      # Merge props (infinite scroll)
       scroll_props,   # Pagination metadata
       clear_history,  # Clear encrypted history
       only,       # Prop filter (include)
       except_,    # Prop filter (exclude)
   )

**Response Classes**:

.. code-block:: python

   from litestar_vite.inertia import (
       InertiaResponse,         # Page response
       InertiaRedirect,         # Same-origin redirect
       InertiaBack,             # Back navigation
       InertiaExternalRedirect, # External redirect
   )

See Also
--------

- :doc:`/inertia/index` - Complete documentation
- :doc:`/inertia/fullstack-example` - Production example

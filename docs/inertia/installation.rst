============
Installation
============

Install litestar-vite and set up Inertia.js for your frontend framework.

.. seealso::
   Official Inertia.js docs: `Installation <https://inertiajs.com/server-side-setup>`_

Backend Setup
-------------

Install the Python package:

.. tab-set::

   .. tab-item:: pip

      .. code-block:: bash

         pip install litestar-vite

   .. tab-item:: uv

      .. code-block:: bash

         uv add litestar-vite

   .. tab-item:: pdm

      .. code-block:: bash

         pdm add litestar-vite

Frontend Setup
--------------

Install the Inertia.js client and litestar-vite-plugin:

.. tab-set::

   .. tab-item:: React

      .. code-block:: bash

         npm install @inertiajs/react litestar-vite-plugin

   .. tab-item:: Vue

      .. code-block:: bash

         npm install @inertiajs/vue3 litestar-vite-plugin

   .. tab-item:: Svelte

      .. code-block:: bash

         npm install @inertiajs/svelte litestar-vite-plugin

Or use project scaffolding:

.. code-block:: bash

   # Scaffold a complete Inertia project
   litestar assets init --template react-inertia
   litestar assets init --template vue-inertia
   litestar assets init --template svelte-inertia

Minimal Configuration
---------------------

.. code-block:: python

   from litestar import Litestar, get
   from litestar_vite import ViteConfig, VitePlugin

   @get("/", component="Home")
   async def home() -> dict:
       return {"message": "Welcome!"}

   app = Litestar(
       route_handlers=[home],
       plugins=[
           VitePlugin(config=ViteConfig(
               dev_mode=True,
               inertia=True,  # Enables Inertia with defaults
           )),
       ],
   )

The ``inertia=True`` shortcut enables Inertia with sensible defaults.
For custom configuration, see :doc:`configuration`.

See Also
--------

- :doc:`configuration` - Full configuration reference
- :doc:`/frameworks/inertia` - Framework-specific setup (React, Vue, Svelte)

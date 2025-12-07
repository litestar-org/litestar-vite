================
Asset Versioning
================

Automatic cache invalidation for frontend assets.

.. seealso::
   Official Inertia.js docs: `Asset Versioning <https://inertiajs.com/asset-versioning>`_

How It Works
------------

Inertia uses asset versioning to detect outdated clients:

1. Server includes a version identifier in every response
2. Client sends this version with each request (``X-Inertia-Version``)
3. If versions don't match, server returns ``409 Conflict``
4. Client performs a hard page reload to get fresh assets

This ensures users always have the latest frontend code.

Automatic Versioning
--------------------

Litestar-Vite automatically generates version IDs from the Vite manifest:

.. code-block:: python

   # No configuration needed - works automatically
   VitePlugin(config=ViteConfig(dev_mode=False))

The version is computed from the manifest hash, so it changes whenever
your frontend assets are rebuilt.

Version Header
--------------

The version is included in response headers:

.. code-block:: text

   X-Inertia: true
   X-Inertia-Version: a1b2c3d4

And in the page response:

.. code-block:: json

   {
     "component": "Dashboard",
     "props": {"user": "Alice"},
     "url": "/dashboard",
     "version": "a1b2c3d4"
   }

409 Conflict Response
---------------------

When versions mismatch:

.. code-block:: text

   HTTP/1.1 409 Conflict

The client detects this and performs a full page reload.

Development Mode
----------------

In development mode, versioning is simplified:

- Version is based on the hot file URL
- Changes trigger HMR instead of hard reloads
- No 409 responses during development

Deployment Flow
---------------

1. Build new frontend assets: ``litestar assets build``
2. Deploy new manifest with application
3. Old clients receive ``409`` on next navigation
4. Clients reload to get new assets

Multi-Server Deployments
------------------------

For load-balanced deployments, ensure:

- All servers have the same manifest file
- Deployments update all servers atomically
- Consider sticky sessions during rolling updates

Troubleshooting
---------------

**Constant 409 errors**:

- Verify manifest exists at expected location
- Check all servers have identical manifests
- Ensure build step ran successfully

**No 409 on updates**:

- Verify you rebuilt assets after changes
- Check manifest hash actually changed
- Clear CDN cache if using one

Checking Version
----------------

Access the current version:

.. code-block:: python

   vite_plugin = app.plugins.get(VitePlugin)
   version = vite_plugin.asset_loader.version_id

In templates:

.. code-block:: html

   <!-- Version: {{ vite_version }} -->

See Also
--------

- :doc:`how-it-works` - Protocol overview
- :doc:`/usage/vite` - Vite configuration

========================
Migration Guide (0.14.x)
========================

Litestar Vite 0.14 introduces the nested configuration structure and the `assets` CLI group. Use this guide when upgrading from earlier 0.x versions.

Configuration Changes
---------------------

The configuration structure has been nested for better organization.

**Before 0.14:**

.. code-block:: python

    ViteConfig(
        bundle_dir="public",
        resource_dir="resources",
        hot_reload=True,
        port=5173,
    )

**0.14+:**

.. code-block:: python

    from litestar_vite.config import PathConfig, RuntimeConfig

    ViteConfig(
        paths=PathConfig(
            bundle_dir="public",
            resource_dir="resources",
        ),
        runtime=RuntimeConfig(
            hot_reload=True,
            port=5173,
        ),
    )

Template Engine
---------------

The `ViteTemplateEngine` has been removed. Use the standard Litestar `JinjaTemplateEngine` instead.

.. code-block:: python

    # 0.14+
    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.template.config import TemplateConfig

    app = Litestar(
        template_config=TemplateConfig(
            engine=JinjaTemplateEngine(directory="templates")
        ),
        plugins=[VitePlugin(...)]
    )

CLI Commands
------------

Commands are available under the ``assets`` group.

- ``litestar assets init`` - Initialize a new project.
- ``litestar assets build`` - Build assets.
- ``litestar assets serve`` - Serve assets.
- ``litestar assets generate-types`` - Generate TypeScript types.

=============
Litestar Vite
=============

.. image:: https://raw.githubusercontent.com/litestar-org/branding/main/assets/Branding%20-%20SVG%20-%20Transparent/Vite%20-%20Banner%20-%20Inline%20-%20Light.svg
   :alt: Litestar Vite
   :class: landing-logo
   :width: 400px
   :align: center

.. raw:: html

   <div style="text-align: center; margin: 2rem 0;">
      <img alt="PyPI - Version" src="https://img.shields.io/pypi/v/litestar-vite?labelColor=202235&color=edb641&logo=python&logoColor=edb641">
      <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/litestar-vite?logo=python&logoColor=edb641&labelColor=202235&color=edb641">
      <a href="https://github.com/litestar-org/litestar-vite/actions/workflows/ci.yml"><img alt="CI Status" src="https://img.shields.io/github/actions/workflow/status/litestar-org/litestar-vite/ci.yml?labelColor=202235&logo=github&logoColor=edb641&label=CI"></a>
      <img alt="Coverage" src="https://img.shields.io/codecov/c/github/litestar-org/litestar-vite?labelColor=202235&logo=codecov&logoColor=edb641">
   </div>

----

Supercharge your Litestar applications with Vite's modern frontend tooling. Litestar-Vite seamlessly integrates
`Vite <https://vitejs.dev/>`_ - the next generation frontend build tool - with your Litestar web applications.

.. grid:: 2 2 4 4
    :gutter: 2

    .. grid-item-card:: :octicon:`rocket` Getting Started
        :link: usage/index
        :link-type: doc

        Quick start guide for integrating Vite with Litestar

    .. grid-item-card:: :octicon:`stack` Frameworks
        :link: frameworks/index
        :link-type: doc

        React, Vue, Svelte, Angular, Inertia.js, and HTMX

    .. grid-item-card:: :octicon:`code` API Reference
        :link: reference/index
        :link-type: doc

        Complete API documentation

    .. grid-item-card:: :octicon:`beaker` Examples
        :link: https://github.com/litestar-org/litestar-vite/tree/main/examples
        :link-type: url

        View example projects

----

Key Features
------------

.. grid:: 1 1 2 2
    :gutter: 3

    .. grid-item-card:: :octicon:`zap` Lightning-fast HMR
        :text-align: center
        :class-card: sd-border-0

        Get instant feedback with Vite's blazing fast Hot Module Replacement during development

    .. grid-item-card:: :octicon:`tools` Zero Config
        :text-align: center
        :class-card: sd-border-0

        Works out of the box with sensible defaults - no complex setup required

    .. grid-item-card:: :octicon:`package` Asset Management
        :text-align: center
        :class-card: sd-border-0

        Automatically serves your static files and handles asset manifests in production

    .. grid-item-card:: :octicon:`rocket` Development Mode
        :text-align: center
        :class-card: sd-border-0

        Integrated dev server with automatic proxy configuration for seamless development

    .. grid-item-card:: :octicon:`shield-check` Production Ready
        :text-align: center
        :class-card: sd-border-0

        Optimized asset serving for production builds with versioned URLs and caching

    .. grid-item-card:: :octicon:`plug` Inertia.js Support
        :text-align: center
        :class-card: sd-border-0

        Build modern single-page applications with server-side routing using Inertia.js

----

See it in Action
----------------

.. tab-set::

    .. tab-item:: Project Scaffolding

        Quickly scaffold a new project with your preferred frontend framework:

        .. image:: _static/demos/scaffolding.gif
           :alt: Project scaffolding demo
           :align: center
           :width: 100%

        *Create a new Litestar + Vite project with React, Vue, Svelte, or HTMX*

    .. tab-item:: Hot Module Replacement

        Experience instant feedback during development with HMR:

        .. image:: _static/demos/hmr.gif
           :alt: HMR demo
           :align: center
           :width: 100%

        *Changes to your frontend code are reflected instantly without page reload*

----

Installation
------------

Installing ``litestar-vite`` is as easy as calling your favorite Python package manager:

.. tab-set::

    .. tab-item:: pip
        :sync: key1

        .. code-block:: bash
            :caption: Using pip

            python3 -m pip install litestar-vite

    .. tab-item:: uv

        .. code-block:: bash
            :caption: Using uv

            uv add litestar-vite

    .. tab-item:: pdm

        .. code-block:: bash
            :caption: Using PDM

            pdm add litestar-vite

    .. tab-item:: Poetry

        .. code-block:: bash
            :caption: Using Poetry

            poetry add litestar-vite

    .. tab-item:: npm (TypeScript Library)

        .. code-block:: bash
            :caption: For the TypeScript/JavaScript library

            npm install litestar-vite-plugin

----

Quick Start
-----------

Here's a minimal example to get you started:

.. code-block:: python
    :caption: app.py

    from pathlib import Path
    from litestar import Litestar, get
    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.response import Template
    from litestar.template.config import TemplateConfig
    from litestar_vite import ViteConfig, VitePlugin

    @get("/")
    async def index() -> Template:
        return Template(template_name="index.html")

    vite = VitePlugin(config=ViteConfig(dev_mode=True))  # defaults: SPA mode, bundle_dir="public", resource_dir="src"

    app = Litestar(
        route_handlers=[index],
        plugins=[vite],
        template_config=TemplateConfig(
            directory=Path("templates"),
            engine=JinjaTemplateEngine,
        ),
    )

Then in your template:

.. code-block:: jinja
    :caption: templates/index.html

    <!DOCTYPE html>
    <html>
    <head>
        {{ vite_hmr() }}
        {{ vite('resources/main.ts') }}
    </head>
    <body>
        <div id="app"></div>
    </body>
    </html>

Install frontend dependencies with ``litestar assets install`` (uses the configured executor), run the backend in development with ``litestar run --reload`` (Vite is proxied automatically when ``dev_mode=True``), and build production assets with ``litestar assets build``.

Run your app with ``litestar run`` and start developing!

----

Why Litestar Vite?
------------------

**Modern Development Experience**
    Vite provides an incredibly fast development server with HMR that makes frontend development a joy.
    Litestar-Vite brings this experience seamlessly to your Litestar applications.

**Framework Flexibility**
    Use any frontend framework you prefer - React, Vue, Svelte, vanilla JS, or even HTMX.
    The plugin works with all of them.

**Production Optimized**
    Automatic asset versioning, code splitting, and optimized bundles ensure your production
    deployment is fast and efficient.

**Inertia.js Integration**
    Build modern SPAs without the complexity of a separate API layer. Server-side routing
    meets client-side rendering with full TypeScript support.

----

Architecture
------------

.. mermaid::

   flowchart LR
       A[Litestar App] --> B[VitePlugin]
       B --> C{Mode?}
       C -->|Development| D[Vite Dev Server]
       C -->|Production| E[Asset Manifest]
       D --> F[HMR WebSocket]
       E --> G[Versioned Assets]
       F --> H[Browser]
       G --> H

----

Explore the Documentation
--------------------------

.. grid:: 1 1 2 3
    :gutter: 3

    .. grid-item-card:: :octicon:`book` Usage Guide
        :link: usage/index
        :link-type: doc
        :class-card: sd-text-center

        Learn how to use Litestar Vite

    .. grid-item-card:: :octicon:`stack` Framework Examples
        :link: frameworks/index
        :link-type: doc
        :class-card: sd-text-center

        React, Vue, Svelte, Angular & more

    .. grid-item-card:: :octicon:`log` Changelog
        :link: changelog
        :link-type: doc
        :class-card: sd-text-center

        See what's new in recent releases

    .. grid-item-card:: :octicon:`issue-opened` Issues
        :link: https://github.com/litestar-org/litestar-vite/issues
        :link-type: url
        :class-card: sd-text-center

        Report bugs and request features

    .. grid-item-card:: :octicon:`git-pull-request` Contributing
        :link: contribution-guide
        :link-type: doc
        :class-card: sd-text-center

        Learn how to contribute to the project

    .. grid-item-card:: :octicon:`mark-github` Source Code
        :link: https://github.com/litestar-org/litestar-vite
        :link-type: url
        :class-card: sd-text-center

        Browse the source code on GitHub

.. toctree::
    :titlesonly:
    :caption: Litestar Vite Documentation
    :hidden:

    usage/index
    inertia/index
    frameworks/index
    reference/index

.. toctree::
    :titlesonly:
    :caption: Development
    :hidden:

    changelog
    contribution-guide

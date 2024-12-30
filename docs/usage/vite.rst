================
Vite Integration
================

Litestar Vite provides seamless integration with Vite, a modern frontend build tool.

Installation
------------

Install the package:

.. code-block:: bash

    pip install litestar-vite

**Note:** If you do not have an existing node environment, you can use `nodeenv` to automatically configure one for you by using the ``litestar-vite[nodeenv]`` extras option.

Setup Options
-------------

There are two ways to set up Vite with Litestar:

1. Using the CLI (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The CLI provides a streamlined setup process:

.. code-block:: bash

    # Initialize a new Vite project
    litestar assets init

This command will:

- Create a new Vite project structure
- Install necessary dependencies
- Set up configuration files
- Create example templates

The generated project structure will look like this:

.. code-block:: text

    my_project/
    ├── public/           # Compiled assets
    ├── resources/        # Source assets
    │   ├── js/
    │   ├── css/
    │   └── templates/
    ├── src/             # Python source code
    ├── package.json     # Node.js dependencies
    ├── vite.config.js   # Vite configuration
    └── pyproject.toml   # Python dependencies

2. Manual Setup
~~~~~~~~~~~~~~~

If you prefer more control, you can set up Vite manually:

1. Initialize the frontend project:

.. code-block:: bash

    npm init -y
    npm install vite
    npm install -D litestar-vite-plugin

2. Create ``vite.config.js``:

.. code-block:: javascript

    import { defineConfig } from 'vite'
    import litestar from 'litestar-vite-plugin'

    export default defineConfig({
        plugins: [
            litestar({
                input: {
                    main: 'resources/js/main.js',
                    styles: 'resources/css/styles.css'
                },
                reload: true
            })
        ]
    })

Configuration
-------------

Litestar Configuration
~~~~~~~~~~~~~~~~~~~~~~

Configure your Litestar application:

.. code-block:: python

    from litestar import Litestar
    from litestar_vite import ViteConfig, VitePlugin

    app = Litestar(
        plugins=[
            VitePlugin(
                config=ViteConfig(
                    use_server_lifespan=True,    # Manage Vite server lifecycle
                    dev_mode=True,               # Enable vite dev mode
                    hot_reload=True,             # Enable HMR in development
                )
            )
        ]
    )

Template Integration
~~~~~~~~~~~~~~~~~~~~

Create templates that use Vite assets:

.. code-block:: html

    <!DOCTYPE html>
    <html>
    <head>
        {{ vite('resources/css/styles.css') }}
    </head>
    <body>
        <div id="app"></div>
        {{ vite('resources/js/main.js') }}
        {{ vite_hmr() }}
    </body>
    </html>

Development Workflow
--------------------

Development Server
~~~~~~~~~~~~~~~~~~

The litestar CLI is able to manage the Vite development process when using the `use_server_lifespan` option.  When this is enabled,
the CLI will automatically manage the Vite server lifecycle with the Litestar application.  This command will automatically serve the the application in dev and production mode.

.. code-block:: bash

    litestar run

However, if you would like to manage the Vite server lifecycle manually, you can use the following commands:

**Note:** You will likely need to disable the ``use_server_lifespan`` option in your ``ViteConfig`` if you are managing the Vite server lifecycle manually.

1. Start the Vite development server using the CLI:

.. code-block:: bash

    # Using the CLI
    litestar assets serve


2. Run your Litestar application:

.. code-block:: bash

    litestar run


Production
----------

Building Assets
~~~~~~~~~~~~~~~

Build your assets for production:

.. code-block:: bash

    # Using the CLI
    litestar assets build

    # Or manually
    npm run build

The build process will:

1. Bundle and optimize all assets
2. Generate a manifest file
3. Output files to the ``bundle_dir``


For more information about Inertia integration, refer to the :doc:`Inertia </usage/inertia>` documentation.

====
HTMX
====

HTMX integration for hypermedia-driven applications with minimal JavaScript.

Quick Start
-----------

.. code-block:: bash

    litestar assets init --template htmx

Project Structure
-----------------

.. code-block:: text

    my-app/
    ├── app.py              # Litestar backend
    ├── package.json
    ├── vite.config.ts
    ├── templates/
    │   ├── index.html      # Main page
    │   └── partials/       # HTMX partials
    │       └── items.html
    └── src/
        ├── main.ts         # Entry (minimal)
        └── style.css

Backend Setup
-------------

.. code-block:: python

    from pathlib import Path
    from litestar import Litestar, get
    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.response import Template
    from litestar.template.config import TemplateConfig
    from litestar_vite import ViteConfig, VitePlugin
    from litestar_vite.config import PathConfig

    @get("/")
    async def index() -> Template:
        return Template(template_name="index.html")

    @get("/items")
    async def get_items() -> Template:
        items = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
        ]
        return Template(
            template_name="partials/items.html",
            context={"items": items},
        )

    vite = VitePlugin(
        config=ViteConfig(
            dev_mode=True,
            paths=PathConfig(
                bundle_dir=Path("public"),
                resource_dir=Path("src"),
            ),
        ),
    )

    app = Litestar(
        plugins=[vite],
        route_handlers=[index, get_items],
        template_config=TemplateConfig(
            directory=Path("templates"),
            engine=JinjaTemplateEngine,
        ),
    )

Main Template
-------------

.. code-block:: jinja

    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://unpkg.com/htmx.org@1.9.10"></script>
        {{ vite_hmr() }}
        {{ vite('src/main.ts') }}
    </head>
    <body>
        <h1>HTMX + Litestar</h1>

        <button hx-get="/items" hx-target="#items">
            Load Items
        </button>

        <div id="items">
            <!-- Items loaded here -->
        </div>
    </body>
    </html>

Partial Template
----------------

.. code-block:: jinja

    {# templates/partials/items.html #}
    <ul>
    {% for item in items %}
        <li>{{ item.name }}</li>
    {% endfor %}
    </ul>

HTMX Patterns
-------------

**Inline Editing**:

.. code-block:: jinja

    <div hx-get="/edit/{{ item.id }}"
         hx-trigger="click"
         hx-swap="outerHTML">
        {{ item.name }}
    </div>

**Form Submission**:

.. code-block:: jinja

    <form hx-post="/items"
          hx-target="#items"
          hx-swap="beforeend">
        <input name="name" required>
        <button type="submit">Add</button>
    </form>

**Delete with Confirmation**:

.. code-block:: jinja

    <button hx-delete="/items/{{ item.id }}"
            hx-confirm="Delete this item?"
            hx-target="closest li"
            hx-swap="outerHTML">
        Delete
    </button>

Why HTMX?
---------

- **Minimal JavaScript**: Most interactivity via HTML attributes
- **Server-rendered**: Full HTML responses, great for SEO
- **Progressive enhancement**: Works without JS (degrades gracefully)
- **Simple mental model**: Request → HTML response → DOM update

See Also
--------

- `Example: template-htmx <https://github.com/litestar-org/litestar-vite/tree/main/examples/template-htmx>`_
- `HTMX Documentation <https://htmx.org/>`_

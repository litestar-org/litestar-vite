====
HTMX
====

HTMX integration for hypermedia-driven applications with minimal JavaScript.
Litestar-Vite provides seamless integration with the `litestar-htmx <https://github.com/litestar-org/litestar-htmx>`_ extension.

At a Glance
-----------

- Template: ``litestar assets init --template htmx``
- Mode: ``template`` (or ``htmx``) with ``HTMXPlugin``
- Entry: ``resources/main.js`` (minimal JS)
- Dev: ``litestar run --reload`` (or ``litestar assets serve`` + ``litestar run``)

Quick Start
-----------

.. code-block:: bash

    litestar assets init --template htmx

Project Structure
-----------------

.. code-block:: text

    my-app/
    ├── app.py                    # Litestar backend with HTMX
    ├── package.json
    ├── vite.config.ts
    ├── templates/
    │   ├── base.html.j2          # Base template with Vite + HTMX
    │   ├── index.html.j2         # Main page
    │   └── partials/
    │       └── book_card.html.j2 # Reusable fragment
    └── resources/
        ├── main.js               # Entry (minimal)
        └── style.css

Backend Setup
-------------

HTMX applications use ``mode="template"`` with the ``HTMXPlugin`` from ``litestar-htmx``:

.. literalinclude:: /../examples/jinja-htmx/app.py
   :language: python
   :start-after: # [docs-start:htmx-imports]
   :end-before: # [docs-end:htmx-imports]
   :caption: Imports for HTMX application

.. literalinclude:: /../examples/jinja-htmx/app.py
   :language: python
   :start-after: # [docs-start:htmx-vite-config]
   :end-before: # [docs-end:htmx-vite-config]
   :caption: VitePlugin and app configuration

Key points:

- ``mode="template"`` enables Jinja2 template rendering
- ``HTMXPlugin()`` adds HTMX-specific request/response handling
- Templates use ``.html.j2`` extension (Jinja2)

Base Template
-------------

The base template sets up Vite HMR and the Litestar HTMX extension:

.. literalinclude:: /../examples/jinja-htmx/templates/base.html.j2
   :language: html+jinja
   :caption: templates/base.html.j2

Key features:

- ``{{ vite_hmr() }}`` - Enables hot module replacement in development
- ``{{ vite('resources/main.js') }}`` - Loads bundled assets
- ``hx-ext="litestar"`` - Enables the Litestar HTMX extension for JSON templating
- ``csrf_token`` - CSRF protection for forms and HTMX requests

Frontend Entry Point
--------------------

The Litestar HTMX extension must be registered explicitly from your Vite entry file:

.. literalinclude:: /../examples/jinja-htmx/resources/main.js
   :language: javascript
   :caption: resources/main.js

HTMX Fragments
--------------

Return partial HTML for HTMX swaps using ``HTMXTemplate``:

.. literalinclude:: /../examples/jinja-htmx/app.py
   :language: python
   :start-after: # [docs-start:htmx-fragment]
   :end-before: # [docs-end:htmx-fragment]
   :caption: Fragment endpoint with HTMXTemplate

The ``HTMXTemplate`` response allows:

- ``re_target`` - Override the target element
- ``re_swap`` - Override the swap method
- ``push_url`` - Control browser history

Partial Template
----------------

Fragment templates are simple Jinja2 partials:

.. literalinclude:: /../examples/jinja-htmx/templates/partials/book_card.html.j2
   :language: html+jinja
   :caption: templates/partials/book_card.html.j2

JSON Templating (Litestar Extension)
------------------------------------

The ``hx-ext="litestar"`` extension enables client-side JSON templating
using ``hx-swap="json"`` with template directives:

.. code-block:: html+jinja

    <!-- Fetch JSON and render client-side -->
    <button hx-get="/api/books" hx-target="#books" hx-swap="json">
        Load Books
    </button>

    <div id="books">
        <!-- ls-for iterates over JSON array -->
        <template ls-for="book in $data" ls-key="book.id">
            <article>
                <h3>${book.title}</h3>
                <p>${book.author} - ${book.year}</p>
            </article>
        </template>
    </div>

Template directives:

- ``ls-for="item in $data"`` - Iterate over JSON response (``$data`` is the response)
- ``ls-key="item.id"`` - Unique key for efficient updates
- ``ls-if="condition"`` - Conditional rendering
- ``ls-else`` - Else branch for conditionals
- ``${expression}`` - Interpolate values (JavaScript template literal syntax)

This enables hybrid rendering: server-side HTML for initial load, client-side
templating for dynamic updates from JSON APIs.

HTMX Patterns
-------------

**Inline Editing**:

.. code-block:: html+jinja

    <div hx-get="/edit/{{ item.id }}"
         hx-trigger="click"
         hx-swap="outerHTML">
        {{ item.name }}
    </div>

**Form Submission**:

.. code-block:: html+jinja

    <form hx-post="/items"
          hx-target="#items"
          hx-swap="beforeend">
        <input name="name" required>
        <button type="submit">Add</button>
    </form>

**Delete with Confirmation**:

.. code-block:: html+jinja

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
- **JSON templating**: Client-side rendering when needed via Litestar extension

See Also
--------

- `Example: jinja-htmx <https://github.com/litestar-org/litestar-vite/tree/main/examples/jinja-htmx>`_
- `HTMX Documentation <https://htmx.org/>`_
- `litestar-htmx <https://github.com/litestar-org/litestar-htmx>`_

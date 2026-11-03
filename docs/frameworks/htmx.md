# HTMX

Combine Litestar's server-rendered Jinja2 templates (`litestar-htmx`) with Vite asset bundling, CSRF header injection, client-side JSON templating (`hx-swap="json"`), and declarative `<litestar-stream>` updates.

---

## Quick Start

```bash
litestar assets init --template htmx
litestar assets install
litestar run --reload
```

---

## Project Structure

```text
my-project/
├── app.py                  # Litestar + VitePlugin(mode="htmx") + HTMXPlugin
├── package.json
├── vite.config.ts
├── resources/
│   ├── main.ts             # Imports htmx.org + registerHtmxExtension()
│   └── styles.css
└── templates/
    ├── base.html.j2        # Layout with vite_hmr(), vite(), csrf-token, hx-ext="litestar"
    ├── index.html.j2       # Full page template
    └── partials/
        └── item.html.j2    # HTMX partial fragment
```

---

## Configuration

=== "Python (`app.py`)"

    <!-- docs-example: skip -->
    ```python title="app.py"
    from pathlib import Path

    from litestar import Litestar, get, post
    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.plugins.htmx import HTMXPlugin, HTMXRequest, HTMXTemplate
    from litestar.response import Template
    from litestar.template.config import TemplateConfig
    from litestar_vite import PathConfig, ViteConfig, VitePlugin


    @get("/", sync_to_thread=False)
    def index() -> Template:
        """Render main HTMX page."""
        return Template(template_name="index.html.j2", context={"items": ["Task A", "Task B"]})


    @post("/items", sync_to_thread=False)
    def add_item(request: HTMXRequest, data: dict[str, str]) -> Template:
        """Return partial HTML fragment for HTMX swap."""
        item = data.get("name", "New Task")
        if request.htmx:
            return HTMXTemplate(template_name="partials/item.html.j2", context={"item": item})
        return Template(template_name="index.html.j2", context={"items": [item]})


    app = Litestar(
        route_handlers=[index, add_item],
        Request=HTMXRequest,
        plugins=[
            VitePlugin(
                config=ViteConfig(
                    mode="htmx",
                    dev_mode=True,
                    paths=PathConfig(resource_dir=Path("resources")),
                ),
            ),
            HTMXPlugin(),
        ],
        template_config=TemplateConfig(
            directory=Path("templates"),
            engine=JinjaTemplateEngine,
        ),
    )
    ```

=== "Frontend Entry (`resources/main.ts`)"

    <!-- docs-example: skip -->
    ```typescript title="resources/main.ts"
    import "htmx.org";
    import { registerHtmxExtension } from "litestar-vite-plugin/helpers";
    import "./styles.css";

    // Registers the "litestar" HTMX extension:
    // 1. Automatically attaches X-CSRF-Token to non-GET HTMX requests
    // 2. Enables hx-swap="json" client-side <template> rendering
    registerHtmxExtension();
    ```

=== "Base Template (`templates/base.html.j2`)"

    ```html title="templates/base.html.j2"
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta name="csrf-token" content="{{ csrf_token }}" />
        <title>Litestar + HTMX</title>
        {{ vite_hmr() }}
        {{ vite('resources/main.ts') }}
      </head>
      <body hx-ext="litestar">
        {% block content %}{% endblock %}
      </body>
    </html>
    ```

---

## Client-Side JSON Templating

When an endpoint returns JSON instead of HTML, the `litestar` HTMX extension (`registerHtmxExtension()`) lets you render JSON directly into a `<template>` element using `hx-swap="json"`:

```html title="templates/index.html.j2"
<button hx-get="/api/books" hx-target="#book-list" hx-swap="json">
  Load Books from JSON API
</button>

<div id="book-list">
  <ul>
    <template ls-for="book in $data">
      <li>
        <strong ls-text="book.title"></strong> by <span ls-text="book.author"></span>
        <span ls-show="book.featured" class="badge">Featured</span>
      </li>
    </template>
  </ul>
</div>
```

### Supported Directive Grammar

| Directive | Description | Example |
| --- | --- | --- |
| `<template ls-for="item in expr">` (or `ls-each`) | Repeat `<template>` content for each item in an array | `<template ls-for="row in $data.items">` |
| `<template ls-if="expr">` / `<template ls-else>` | Conditional `<template>` structural rendering | `<template ls-if="item.active">` |
| `ls-show="expr"` / `ls-hide="expr"` | Toggle `style.display` visibility on any element | `ls-show="item.featured"` |
| `ls-scope="expr"` | Narrow evaluation context for descendant elements | `ls-scope="item.author"` |
| `ls-text="expr"` / `${expr}` | Safe `textContent` binding or text-node interpolation | `ls-text="item.name"`, `<h3>${item.name}</h3>` |
| `ls-html="expr"` | Sanitized `innerHTML` content binding | `ls-html="item.summaryHtml"` |
| `:attr="expr"` | Dynamic attribute or `:class` object binding (`boolean` toggles presence) | `:href="item.url"`, `:disabled="!item.ready"` |
| `@event="expr"` | Event listener expression with wrapped `$event` context | `@click="selected = item.id"` |

!!! important
    **Security Model**: `registerHtmxExtension()` evaluates directive expressions using a restricted property-path and comparison parser — never `eval()` or `new Function()`. Arbitrary function calls and prototype-chain properties (`__proto__`, `constructor`, `prototype`) are blocked.

---

## Declarative Realtime Streams

Pair HTMX templates with `<litestar-stream>` (`defineStreamElement()`) to append or replace live SSE/WebSocket events without writing custom JavaScript glue. See [Realtime Event Streams](../typegen/event-streams.md) for full details.

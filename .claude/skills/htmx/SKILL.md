---
name: htmx
description: Expert knowledge for HTMX development. Use when building hypermedia-driven applications with Litestar templates and partial HTML responses.
---

# HTMX Framework Skill

## Quick Reference

### Basic HTMX Patterns

```html
<!-- GET request on click -->
<button hx-get="/api/items" hx-target="#items-list" hx-swap="innerHTML">
  Load Items
</button>

<!-- POST with form data -->
<form hx-post="/api/items" hx-target="#items-list" hx-swap="beforeend">
  <input name="title" type="text" />
  <button type="submit">Add Item</button>
</form>

<!-- Polling -->
<div hx-get="/api/status" hx-trigger="every 2s" hx-swap="outerHTML">
  Loading...
</div>

<!-- Lazy loading -->
<div hx-get="/api/expensive" hx-trigger="revealed" hx-swap="outerHTML">
  Loading...
</div>
```

### Litestar Backend

```python
from litestar import get, post, Response
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response import Template

@get("/partials/items")
async def get_items_partial() -> Template:
    items = await fetch_items()
    return Template(
        template_name="partials/items.html",
        context={"items": items},
    )

@post("/api/items")
async def create_item(data: ItemCreate) -> Template:
    item = await save_item(data)
    return Template(
        template_name="partials/item-row.html",
        context={"item": item},
    )

# Trigger client-side events
@post("/api/items/{id}/delete")
async def delete_item(id: int) -> Response:
    await remove_item(id)
    return Response(
        content="",
        headers={"HX-Trigger": "itemDeleted"},
    )
```

### HTMX Headers

```python
# Check if request is HTMX
def is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"

# Response headers for HTMX
headers = {
    "HX-Trigger": "myEvent",           # Trigger client event
    "HX-Trigger-After-Swap": "event",  # Trigger after swap
    "HX-Redirect": "/new-url",         # Client-side redirect
    "HX-Refresh": "true",              # Full page refresh
    "HX-Retarget": "#other",           # Change target
    "HX-Reswap": "outerHTML",          # Change swap method
}
```

### Template Partials

```html
<!-- templates/partials/item-row.html -->
<tr id="item-{{ item.id }}">
  <td>{{ item.name }}</td>
  <td>
    <button
      hx-delete="/api/items/{{ item.id }}"
      hx-target="#item-{{ item.id }}"
      hx-swap="outerHTML swap:1s"
    >
      Delete
    </button>
  </td>
</tr>

<!-- templates/partials/items.html -->
{% for item in items %}
  {% include "partials/item-row.html" %}
{% endfor %}
```

### Vite + HTMX Setup

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import { litestarVitePlugin } from 'litestar-vite-plugin';

export default defineConfig({
  plugins: [
    litestarVitePlugin({
      input: ['resources/main.ts'],
    }),
  ],
});
```

```typescript
// resources/main.ts
import htmx from 'htmx.org';

// Add HTMX extensions if needed
htmx.defineExtension('my-extension', {
  // ...
});
```

## Project-Specific Patterns

- Use Jinja2 templates with partials
- Return HTML fragments, not JSON
- Use HX-Trigger for client updates
- Combine with Alpine.js for reactivity

## Context7 Lookup

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/bigskysoftware/htmx",
    topic="attributes triggers swapping",
    mode="code"
)
```

## Related Files

- `examples/template-htmx/` - HTMX example
- `src/py/litestar_vite/templates/htmx/` - HTMX templates

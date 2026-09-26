=====================================================
HTMX & Server-Rendered UI Component Fragments
=====================================================

``litestar-vite`` can render individual React, Vue, Svelte, or Astro components on the server into HTML fragments for HTMX partial swaps and Jinja2 templates.

-------------------------
Fragment Rendering Flow
-------------------------

Instead of rendering an entire page tree, ``FragmentEngine`` renders a single component entry point over IPC and prepends any CSS chunks associated with that component in Vite's ``manifest.json``:

.. mermaid::

   sequenceDiagram
       autonumber
       participant Browser as Browser (HTMX)
       participant Litestar as Litestar Controller
       participant Engine as FragmentEngine
       participant Worker as Node/Bun IPC Worker

       Browser->>Litestar: GET /users/42 (hx-target="#user-card")
       Litestar->>Engine: render_fragment("components/UserProfile.vue", props={"id": 42})
       Engine->>Worker: NDJSON IPC request
       Worker->>Worker: Render component to HTML string
       Worker-->>Engine: HTML markup
       Engine->>Engine: Resolve manifest CSS & prepend <link> tags
       Engine-->>Litestar: Fragment HTML string
       Litestar-->>Browser: ComponentResponse (HTML partial)
       Browser->>Browser: HTMX swaps innerHTML into #user-card

------------------------------------------
``static`` vs ``island`` Rendering Modes
------------------------------------------

Component fragments support two rendering modes:

1. **``static`` Mode**:
   Renders the component on the server and returns plain HTML markup without client-side hydration scripts.

2. **``island`` Mode**:
   Renders the component on the server and wraps the output in a ``<litestar-island>`` custom element containing the component path and serialized props, followed by an inline hydration script that mounts the component on the client.

---------------------------------
Scoped CSS Chunk Resolution
---------------------------------

When an HTMX request swaps a component fragment into the DOM, any stylesheets imported by that component must also be present in the document:

- In production builds, ``FragmentEngine`` traverses ``manifest.json`` starting from the component entry point, collects CSS files from the entry and its transitive ``imports``, and prepends ``<link rel="stylesheet">`` tags to the returned HTML fragment.
- In development mode, ``FragmentEngine`` only emits ``<link rel="stylesheet">`` tags for ``.css`` entries to avoid browser MIME-type rejections on JavaScript/TypeScript module URLs.

---------------------------------
Jinja2 Template Integration
---------------------------------

Use the ``vite_fragment`` template global to render component fragments inside Jinja2 templates:

.. docs-example: skip
.. code-block:: html+jinja

   {% extends "base.html" %}

   {% block content %}
   <div class="dashboard-grid">
     <div id="user-profile">
       {{ vite_fragment("components/UserProfile.vue", user=user, mode="static") }}
     </div>
     <div id="stats-widget">
       {{ vite_fragment("components/StatsWidget.tsx", stats=metrics, mode="island") }}
     </div>
   </div>
   {% endblock %}

---------------------------------
Litestar HTMX Controller Example
---------------------------------

Return ``ComponentResponse`` from Litestar route handlers to serve component fragments directly:

.. code-block:: python

   from pathlib import Path
   from litestar import Controller, Litestar, get, post
   from litestar.response import Template
   from litestar_vite import ComponentResponse, PathConfig, ViteConfig, VitePlugin

   class UserDashboardController(Controller):
       path = "/users"

       @get("/")
       async def index(self) -> Template:
           """Render the dashboard shell using Jinja2."""
           return Template(template_name="dashboard.html")

       @get("/{user_id:int}/card")
       async def get_user_card(self, user_id: int) -> ComponentResponse:
           """Return a server-rendered Vue component fragment for an HTMX GET request."""
           user_data = {
               "id": user_id,
               "name": "Jane Doe",
               "email": "jane@example.com",
               "role": "Lead Architect",
           }
           return ComponentResponse(
               component="components/UserCard.vue",
               props={"user": user_data},
               mode="static",
           )

       @post("/{user_id:int}/status")
       async def update_user_status(self, user_id: int, data: dict[str, str]) -> ComponentResponse:
           """Handle an HTMX form POST and return an updated React component fragment."""
           updated_status = data.get("status", "Active")
           return ComponentResponse(
               component="components/UserBadge.tsx",
               props={"userId": user_id, "status": updated_status},
               mode="static",
           )

   vite_config = ViteConfig(
       paths=PathConfig(
           root=Path(__file__).parent,
           resource_dir="resources",
           bundle_dir="public",
       ),
   )
   vite_plugin = VitePlugin(config=vite_config)
   app = Litestar(route_handlers=[UserDashboardController], plugins=[vite_plugin])

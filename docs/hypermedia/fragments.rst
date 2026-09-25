==================================================================
Building Hypermedia Applications with HTMX & Component Fragments
==================================================================

Modern hypermedia architectures—driven by tools such as `HTMX <https://htmx.org/>`_—offer an attractive alternative to monolithic Single Page Applications (SPAs). Rather than maintaining parallel client-side routers, state management stores, and complex JSON APIs, hypermedia applications keep routing, authorization, and business logic centered in Python while updating targeted subtrees of the Document Object Model (DOM) over standard HTTP.

However, developers frequently miss the component ecosystems, declarative templating, and scoped styles offered by modern UI libraries such as React, Vue, and Svelte. Litestar Vite unites these two approaches through its native **Fragment Rendering Engine**: you can author reusable UI components in your favorite frontend framework, render them on the server into HTML fragments via high-speed IPC, and swap them dynamically into the client page using HTMX.

---------------------------------
The Hypermedia Component Concept
---------------------------------

In traditional full-page server rendering with Inertia, every navigation replaces the page root or reconciles virtual DOM trees across the entire screen. With component fragments, you render individual component files:

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
       Worker-->>Engine: HTML markup + Scoped CSS URLs
       Engine->>Engine: Resolve manifest CSS & inject <link> tags
       Engine-->>Litestar: Fragment HTML string
       Litestar-->>Browser: ComponentResponse (HTML partial)
       Browser->>Browser: HTMX swaps innerHTML into #user-card

This architecture delivers key benefits:

- **Unified Backend Logic**: Litestar remains the single authority for data queries, authentication, session state, and security validation.
- **Framework Flexibility**: Author a complex interactive form in React, a data visualization widget in Vue, and a lean information card in Svelte within the same application.
- **Low Network Payload**: Payloads consist of plain HTML fragments rather than multi-megabyte JavaScript bundles and JSON serializers.

------------------------------------------
``static`` vs ``island`` Rendering Modes
------------------------------------------

Litestar Vite supports two rendering modes for component fragments:

1. **Static Mode (Zero Client JavaScript)**:
   The component is executed on the server, producing pure HTML markup. No hydration scripts, event listeners, or client-side runtime libraries are sent to the browser. This mode is optimal for content display, tables, modal dialogues, and HTMX-driven form replacements.

2. **Island Mode (Interactive Hydration)**:
   The component is pre-rendered into HTML on the server and wrapped in a custom ``<vite-island>`` custom element with serialized component props. A targeted client hydration script is emitted, allowing client-side React or Vue instances to hydrate only that specific element on the page (similar to Astro Islands).

---------------------------------
Scoped CSS Chunk Resolution
---------------------------------

A common hazard in hypermedia partial swapping is **Unstyled Content Flashing (FOUC)** or missing styles:

- When an HTMX request injects a newly rendered component fragment into the DOM, any CSS classes defined inside that component (such as Vue scoped styles or CSS Modules) will not take effect unless the corresponding stylesheet is present in the document.
- In production builds, Vite bundles CSS into hashed chunk files (e.g. ``assets/UserProfile-B18a9c.css``) recorded in ``manifest.json``.

Litestar Vite's ``FragmentEngine`` automatically traverses ``manifest.json`` for the requested component entry point and its transitive dependencies, extracts all associated CSS chunk URLs, and prepends ``<link rel="stylesheet">`` tags directly to the fragment response. When HTMX performs an inner HTML swap, the browser loads the required styles immediately, ensuring that swapped components render with complete styling fidelity.

In local development mode, stylesheets are served directly via Vite module URLs or hot module reloading (HMR), avoiding MIME-type collisions.

---------------------------------
Jinja2 Template Integration
---------------------------------

If you use Jinja2 page shells, you can invoke component fragments directly from within your templates using the ``vite_fragment`` template callable:

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

The callable resolves the component asynchronously through the lifespan-managed IPC transport, injects required stylesheet links, and returns safe markup ready for insertion into the template response.

---------------------------------
Complete Litestar HTMX Controller
---------------------------------

The following complete controller demonstrates how to serve a base HTML shell, return server-rendered React and Vue component fragments on GET and POST requests, and handle HTMX partial updates:

.. docs-example: skip
.. code-block:: python

   from pathlib import Path
   from litestar import Controller, Litestar, get, post
   from litestar.response import Template
   from litestar_vite import ComponentResponse, PathConfig, ViteConfig, VitePlugin

   class UserDashboardController(Controller):
       path = "/users"

       @get("/")
       async def index(self) -> Template:
           """Render the initial dashboard shell using Jinja2."""
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

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
   Renders the component on the server and wraps the output in a ``<litestar-island>`` custom element containing the component identifier and serialized props. A module script loads your compiled browser registry, which hydrates the component with the matching framework adapter. React, Vue, and Svelte support islands; Astro fragments support static rendering only.

---------------------------------
Compile and Register Components
---------------------------------

Production rendering requires components compiled by your application SSR build.
A source path sent from Python is a registry key, not a filename that Node can
compile at runtime. Use matching keys in the server and browser registries.

For example, a React island browser entry can register a compiled component:

.. docs-example: skip
.. code-block:: typescript

   // resources/islands.ts
   import { hydrateIslands } from "litestar-vite-plugin/fragments/client"
   import { hydrateReact } from "litestar-vite-plugin/fragments/react"

   hydrateIslands({
     "resources/components/Counter.tsx": {
       load: () => import("./components/Counter.tsx"),
       hydrate: hydrateReact,
     },
   })

For Vue use ``hydrateVue`` from ``litestar-vite-plugin/fragments/vue``; for Svelte
use ``hydrateSvelte`` from ``litestar-vite-plugin/fragments/svelte``. Register all
islands in one client entry. Newly inserted ``litestar-island`` elements hydrate
automatically once that entry has loaded. The framework adapters return cleanup
callbacks so removed islands unmount their framework instances. If you provide a
custom ``hydrate`` function, return a teardown callback that releases subscriptions
and other component resources.

Build a production worker with an explicit server registry:

.. docs-example: skip
.. code-block:: typescript

   // resources/fragment-worker.ts
   import { createFragmentRenderer } from "litestar-vite-plugin/fragments"
   import { startSsrWorker } from "litestar-vite-plugin/ssr-worker"

   const clientEntry = process.env.ISLAND_CLIENT_ENTRY
   if (!clientEntry) throw new Error("Set ISLAND_CLIENT_ENTRY to the built browser entry URL")

   startSsrWorker({
     renderFragment: createFragmentRenderer({
       "resources/components/Counter.tsx": () => import("./components/Counter.tsx"),
     }, { clientEntry }),
   })

Build ``resources/islands.ts`` as a browser entry and
``resources/fragment-worker.ts`` as an SSR entry using the framework's Vite plugin.
Resolve ``ISLAND_CLIENT_ENTRY`` from the browser build manifest, including your
asset prefix and the emitted filename hash. Deploy both builds. The default
Python worker command expects ``ssr.js`` under ``PathConfig.ssr_output_dir`` when
configured, or under ``<resource_dir>/bootstrap/ssr`` otherwise, anchored to the
project root. With this example's ``resource_dir="resources"``, the default bundle
is ``resources/bootstrap/ssr/ssr.js``. Match the SSR build output to that location
or supply the worker command explicitly. A static-only renderer can omit
``clientEntry``; island requests require it.

In development, configure permitted component roots and the browser entry URL:

.. docs-example: skip
.. code-block:: typescript

   litestar({
     input: ["resources/main.ts", "resources/islands.ts"],
     devSsr: {
       componentRoots: ["resources/components"],
       clientEntry: "/resources/islands.ts",
     },
   })

Component roots are relative to the Vite project root. Configure ``clientEntry``
as the browser-accessible module URL, including your Vite base path when needed.
Only configured server components should be exposed to rendering requests.

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

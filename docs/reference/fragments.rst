============================
Component Fragment Rendering
============================

The ``litestar_vite.fragments`` package provides server-side rendering of isolated UI components (React, Vue, Svelte, Astro) into HTML fragments for HTMX partial swaps and Jinja2 templates.

Fragment Engine & APIs
----------------------

.. automodule:: litestar_vite.fragments
    :members:
    :show-inheritance:
    :inherited-members:

Handler Usage
-------------

Return a :class:`ComponentResponse` directly from any Litestar route handler:

.. code-block:: python

    from litestar import get
    from litestar_vite import ComponentResponse

    @get("/profile/{user_id:int}")
    async def get_profile(user_id: int) -> ComponentResponse:
        """Render a Vue user profile component into an HTML fragment."""
        return ComponentResponse(
            component="components/UserProfile.vue",
            props={"userId": user_id},
            mode="static",
        )

Jinja Template Callable
-----------------------

Render component fragments directly in Jinja templates using :func:`vite_fragment`:

.. docs-example: skip
.. code-block:: html+jinja

    <div class="user-container">
      {{ vite_fragment("components/UserProfile.vue", user=current_user, mode="static") }}
    </div>

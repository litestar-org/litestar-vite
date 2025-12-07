=========
Redirects
=========

Server-side redirects for Inertia applications.

.. seealso::
   Official Inertia.js docs: `Redirects <https://inertiajs.com/redirects>`_

InertiaRedirect
---------------

Redirect within your application (same-origin):

.. code-block:: python

   from litestar import post
   from litestar.request import Request
   from litestar_vite.inertia import InertiaRedirect

   @post("/logout")
   async def logout(request: Request) -> InertiaRedirect:
       request.session.clear()
       return InertiaRedirect(request, "/login")

   @post("/users")
   async def create_user(request: Request, data: UserCreate) -> InertiaRedirect:
       user = await User.create(**data.dict())
       return InertiaRedirect(request, f"/users/{user.id}")

InertiaRedirect validates that the URL is same-origin to prevent open
redirect attacks.

InertiaBack
-----------

Redirect to the previous page using the Referer header:

.. code-block:: python

   from litestar_vite.inertia import InertiaBack

   @post("/cancel")
   async def cancel(request: Request) -> InertiaBack:
       return InertiaBack(request)

InertiaBack validates the Referer header is same-origin. If invalid or
missing, it falls back to the application's base URL.

InertiaExternalRedirect
-----------------------

Redirect to external URLs (OAuth callbacks, payment pages, etc.):

.. code-block:: python

   from litestar_vite.inertia import InertiaExternalRedirect

   @get("/oauth/google")
   async def google_oauth(request: Request) -> InertiaExternalRedirect:
       return InertiaExternalRedirect(
           request,
           "https://accounts.google.com/oauth/authorize?...",
       )

External redirects return ``409 Conflict`` with ``X-Inertia-Location``
header, triggering a hard browser redirect.

.. warning::
   External redirects intentionally skip same-origin validation.
   Only use for trusted external URLs.

HTTP Status Codes
-----------------

Inertia redirects use appropriate status codes:

- **GET requests**: ``307 Temporary Redirect``
- **POST/PUT/DELETE**: ``303 See Other``
- **External redirects**: ``409 Conflict``

POST-Redirect-GET Pattern
-------------------------

Always redirect after form submissions to prevent duplicate submissions:

.. code-block:: python

   from litestar_vite.inertia import flash, InertiaRedirect

   @post("/posts")
   async def create_post(request: Request, data: PostCreate) -> InertiaRedirect:
       post = await Post.create(**data.dict())
       flash(request, "Post created successfully!", "success")
       return InertiaRedirect(request, f"/posts/{post.id}")

See Also
--------

- :doc:`forms` - Form handling
- `Inertia.js Redirects <https://inertiajs.com/redirects>`_ - Official docs

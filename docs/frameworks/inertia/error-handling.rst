==============
Error Handling
==============

Handle errors gracefully in Inertia applications.

.. seealso::
   Official Inertia.js docs: `Error Handling <https://inertiajs.com/error-handling>`_

Validation Errors
-----------------

The ``error()`` Helper
~~~~~~~~~~~~~~~~~~~~~~

Set validation errors manually using the ``error()`` helper:

.. code-block:: python

   from litestar_vite.inertia import error, InertiaBack

   @post("/users")
   async def create_user(request: Request) -> InertiaBack:
       data = await request.json()

       # Manual validation
       if not data.get("email"):
           error(request, "email", "Email is required")
           return InertiaBack(request)

       if await User.email_exists(data["email"]):
           error(request, "email", "Email already exists")
           return InertiaBack(request)

       await User.create(**data)
       return InertiaRedirect(request, "/users")

The ``error()`` helper sets errors in the session, which are then included
in the ``errors`` prop of the next Inertia response. Errors are automatically
cleared after being displayed (pop semantics).

Frontend Usage
~~~~~~~~~~~~~~

Errors are available in the ``errors`` prop:

.. code-block:: tsx

   interface Props {
     errors: {
       email?: string;
       name?: string;
     };
   }

   export default function CreateUser({ errors }: Props) {
     return (
       <form>
         <input name="email" />
         {errors.email && <span className="error">{errors.email}</span>}
       </form>
     );
   }

Pydantic Validation
-------------------

Litestar automatically converts Pydantic validation errors to the
``errors`` prop format:

.. code-block:: python

   from pydantic import BaseModel, EmailStr

   class UserCreate(BaseModel):
       email: EmailStr
       name: str

   @post("/users")
   async def create_user(data: UserCreate) -> InertiaRedirect:
       # Pydantic validation errors are automatically caught
       user = await User.create(**data.dict())
       return InertiaRedirect(request, f"/users/{user.id}")

Error Bags
----------

The Inertia protocol supports error bags to scope validation errors:

.. code-block:: python

   # Errors are scoped by the X-Inertia-Error-Bag header sent by the client
   # The error() helper automatically respects the error bag from the request

   @post("/profile")
   async def update_profile(request: Request) -> InertiaBack:
       data = await request.json()

       # Error bag is extracted from X-Inertia-Error-Bag header
       error_bag = request.headers.get("X-Inertia-Error-Bag")

       if not data.get("email"):
           error(request, "email", "Email is required")
           return InertiaBack(request)

       # Errors are scoped to the error bag on the frontend
       return InertiaRedirect(request, "/profile")

On the frontend, errors are scoped by bag:

.. code-block:: tsx

   interface Props {
     errors: {
       // Scoped to specific error bag (if X-Inertia-Error-Bag header sent)
       createUser?: { email?: string; name?: string };
       // Or unscoped errors
       email?: string;
     };
   }

Flash Messages
--------------

Use flash messages for success/info notifications:

.. code-block:: python

   from litestar_vite.inertia import flash

   @post("/users")
   async def create_user(request: Request, data: UserCreate) -> InertiaRedirect:
       user = await User.create(**data.dict())
       flash(request, "User created successfully!", "success")
       return InertiaRedirect(request, f"/users/{user.id}")

Access in components:

.. code-block:: tsx

   interface Props {
     flash: {
       success?: string[];
       error?: string[];
       warning?: string[];
       info?: string[];
     };
   }

   function Flash({ flash }: Props) {
     return (
       <>
         {flash.success?.map((msg, i) => (
           <div key={i} className="alert-success">{msg}</div>
         ))}
         {flash.error?.map((msg, i) => (
           <div key={i} className="alert-error">{msg}</div>
         ))}
       </>
     );
   }

Exception Handlers
------------------

Configure redirects for common exceptions:

.. code-block:: python

   InertiaConfig(
       redirect_unauthorized_to="/login",  # 401/403 errors
       redirect_404="/not-found",          # 404 errors
   )

Custom Error Pages
------------------

Create custom error components:

.. code-block:: python

   from litestar.exceptions import HTTPException

   @app.exception_handler(HTTPException)
   async def http_exception_handler(request: Request, exc: HTTPException):
       if request.inertia_enabled:
           return InertiaResponse(
               content={
                   "status": exc.status_code,
                   "message": exc.detail,
               },
               component=f"Errors/{exc.status_code}",
               status_code=exc.status_code,
           )
       raise exc

Frontend error page:

.. code-block:: tsx
   :caption: pages/Errors/404.tsx

   interface Props {
     status: number;
     message: string;
   }

   export default function NotFound({ message }: Props) {
     return (
       <div className="error-page">
         <h1>404</h1>
         <p>{message || "Page not found"}</p>
         <Link href="/">Go Home</Link>
       </div>
     );
   }

Server Errors
-------------

For 500 errors, Inertia shows a modal by default. Customize this:

.. code-block:: tsx

   createInertiaApp({
     resolve: (name) => pages[`./pages/${name}.tsx`],
     setup({ el, App, props }) {
       createRoot(el).render(
         <ErrorBoundary fallback={<ErrorPage />}>
           <App {...props} />
         </ErrorBoundary>
       );
     },
   });

Error Boundaries
----------------

Use React error boundaries for component errors:

.. code-block:: tsx

   import { ErrorBoundary } from "react-error-boundary";

   function ErrorFallback({ error, resetErrorBoundary }) {
     return (
       <div>
         <h2>Something went wrong</h2>
         <pre>{error.message}</pre>
         <button onClick={resetErrorBoundary}>Try again</button>
       </div>
     );
   }

   export default function App() {
     return (
       <ErrorBoundary FallbackComponent={ErrorFallback}>
         <Routes />
       </ErrorBoundary>
     );
   }

See Also
--------

- :doc:`forms` - Form validation
- :doc:`redirects` - Redirect patterns

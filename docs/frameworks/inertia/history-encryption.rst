==================
History Encryption
==================

Protect sensitive data in browser history with encryption.

.. seealso::
   Official Inertia.js docs: `History Encryption <https://inertiajs.com/history-encryption>`_

Overview
--------

Inertia v2 supports encrypting page data stored in browser history.
This prevents sensitive data from being visible after a user logs out.

How It Works
------------

1. When ``encryptHistory: true``, Inertia encrypts page data using the
   browser's Web Crypto API before storing in history
2. A session-specific encryption key is generated client-side
3. When navigating back, data is decrypted automatically
4. Calling ``clearHistory`` regenerates the key, invalidating old entries

Enabling Encryption
-------------------

**Per-response**:

.. code-block:: python

   from litestar_vite.inertia import InertiaResponse

   @get("/account", component="Account")
   async def account() -> InertiaResponse:
       return InertiaResponse(
           content={"ssn": "123-45-6789", "salary": 100000},
           encrypt_history=True,
       )

**Globally**:

.. code-block:: python

   from litestar_vite.inertia import InertiaConfig

   InertiaConfig(
       encrypt_history=True,  # All pages encrypted by default
   )

Clearing History
----------------

Clear encrypted history during logout to invalidate old entries:

**Using the response parameter**:

.. code-block:: python

   @get("/logout", component="Logout")
   async def logout() -> InertiaResponse:
       return InertiaResponse(
           content={},
           clear_history=True,  # Regenerates encryption key
       )

**Using the helper function**:

.. code-block:: python

   from litestar_vite.inertia import clear_history, InertiaRedirect

   @post("/logout")
   async def logout(request: Request) -> InertiaRedirect:
       request.session.clear()
       clear_history(request)  # Sets flag for next response
       return InertiaRedirect(request, "/login")

The ``clear_history()`` helper sets a session flag that's consumed by
the next InertiaResponse.

Logout Flow
-----------

Recommended logout pattern:

.. code-block:: python

   from litestar_vite.inertia import clear_history, InertiaRedirect

   @post("/logout")
   async def logout(request: Request) -> InertiaRedirect:
       # 1. Clear server-side session
       request.session.clear()

       # 2. Mark history for clearing
       clear_history(request)

       # 3. Redirect to login
       return InertiaRedirect(request, "/login")

Protocol Response
-----------------

When history encryption is enabled:

.. code-block:: json

   {
     "component": "Account",
     "props": {"ssn": "***"},
     "encryptHistory": true
   }

When clearing history:

.. code-block:: json

   {
     "component": "Login",
     "props": {},
     "clearHistory": true
   }

Browser Requirements
--------------------

History encryption requires:

- HTTPS in production (Web Crypto API requirement)
- Modern browser with Web Crypto support

.. note::
   In development (HTTP), encryption may be degraded or disabled.
   Always test with HTTPS for accurate behavior.

Security Considerations
-----------------------

- Encryption happens client-side using browser APIs
- Server never sees the encryption key
- Keys are per-session and stored in memory
- Closing the browser clears the key
- ``clearHistory`` forces key regeneration

Best Practices
--------------

1. Enable globally for applications with sensitive data
2. Always call ``clear_history()`` on logout
3. Use HTTPS in production
4. Don't rely solely on encryption - also minimize sensitive data in props

See Also
--------

- :doc:`redirects` - Redirect patterns
- `Web Crypto API <https://developer.mozilla.org/en-US/docs/Web/API/Web_Crypto_API>`_

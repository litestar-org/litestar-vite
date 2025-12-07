==============
SPA Handler
==============

The ViteSPAHandler manages serving Single Page Applications in both development
and production modes.

Features
--------

- Development mode: Proxies requests to Vite dev server for HMR
- Production mode: Serves built index.html with caching
- CSRF token injection
- Page data injection for Inertia.js
- Async and sync initialization support
- HTML transformation utilities

.. automodule:: litestar_vite.spa
    :members:
    :show-inheritance:
    :inherited-members:

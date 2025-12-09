=========================
Inertia Exception Handler
=========================

Exception handling utilities for Inertia.js requests.

These utilities ensure that exceptions are handled correctly for both
standard HTTP requests and Inertia.js requests, with proper error
message formatting and response codes.

Available Functions
-------------------

create_inertia_exception_response
    Create an appropriate Inertia response for exceptions based on request type.

exception_to_http_response
    Convert various exception types to HTTP responses with proper status codes.

.. automodule:: litestar_vite.inertia.exception_handler
    :members:
    :show-inheritance:

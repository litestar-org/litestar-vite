==============
Inertia Types
==============

Type definitions and utilities for Inertia.js protocol support.

This module provides the core type definitions used for Inertia.js page rendering,
including page props, headers, and configuration for v2 features like deferred
props, merge strategies, and infinite scroll.

Available Types
---------------

PageProps
    Generic type representing the complete page object sent to Inertia client.
    Includes support for v2 features like history encryption, merge props,
    deferred loading, and infinite scroll.

InertiaProps
    Wrapper type for Inertia props.

InertiaHeaderType
    TypedDict for Inertia request/response headers.

MergeStrategy
    Literal type for merge strategies: "append", "prepend", "deep".

DeferredPropsConfig
    Configuration for lazy-loaded props (v2 feature).

ScrollPropsConfig
    Configuration for infinite scroll pagination (v2 feature).

Available Functions
-------------------

to_camel_case
    Convert snake_case strings to camelCase for JavaScript compatibility.

to_inertia_dict
    Convert Python dataclasses to dicts with camelCase keys for Inertia.js protocol.

.. automodule:: litestar_vite.inertia.types
    :members:
    :show-inheritance:

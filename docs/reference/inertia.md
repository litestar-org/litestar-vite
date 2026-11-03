# Inertia.js Reference

API reference for the Inertia.js plugin, request/response primitives, deferred/merged prop wrappers, session state helpers, and Laravel Precognition support.

---

## Plugin, Middleware & Request Primitives

::: litestar_vite.inertia.InertiaPlugin
    options:
      heading_level: 4
      members:
        - on_app_init

::: litestar_vite.inertia.InertiaMiddleware
    options:
      heading_level: 4
      members: false

::: litestar_vite.inertia.InertiaRequest
    options:
      heading_level: 4
      members:
        - is_inertia
        - is_partial_render
        - partial_keys
        - partial_except_keys
        - reset_keys

::: litestar_vite.inertia.InertiaDetails
    options:
      heading_level: 4
      members: false

::: litestar_vite.inertia.InertiaHeaders
    options:
      heading_level: 4
      members: false

::: litestar_vite.inertia.types.PageProps
    options:
      heading_level: 4
      members: false

::: litestar_vite.inertia.types.InertiaHeaderType
    options:
      heading_level: 4
      members: false

---

## Responses & Redirects

::: litestar_vite.inertia.InertiaResponse
    options:
      heading_level: 4
      members: false

::: litestar_vite.inertia.InertiaRedirect
    options:
      heading_level: 4
      members: false

::: litestar_vite.inertia.InertiaBack
    options:
      heading_level: 4
      members: false

::: litestar_vite.inertia.InertiaExternalRedirect
    options:
      heading_level: 4
      members: false

---

## Prop Evaluation & Partial Reload Wrappers

::: litestar_vite.inertia.defer
    options:
      heading_level: 4

::: litestar_vite.inertia.once
    options:
      heading_level: 4

::: litestar_vite.inertia.optional
    options:
      heading_level: 4

::: litestar_vite.inertia.lazy
    options:
      heading_level: 4

::: litestar_vite.inertia.always
    options:
      heading_level: 4

::: litestar_vite.inertia.merge
    options:
      heading_level: 4

::: litestar_vite.inertia.scroll_props
    options:
      heading_level: 4

::: litestar_vite.inertia.only
    options:
      heading_level: 4

::: litestar_vite.inertia.except_
    options:
      heading_level: 4

---

## Prop Wrapper Classes & Extractors

::: litestar_vite.inertia.helpers.DeferredProp
    options:
      heading_level: 4
      members: false

::: litestar_vite.inertia.helpers.MergeProp
    options:
      heading_level: 4
      members: false

::: litestar_vite.inertia.OnceProp
    options:
      heading_level: 4
      members: false

::: litestar_vite.inertia.OptionalProp
    options:
      heading_level: 4
      members: false

::: litestar_vite.inertia.AlwaysProp
    options:
      heading_level: 4
      members: false

::: litestar_vite.inertia.helpers.StaticProp
    options:
      heading_level: 4
      members: false

::: litestar_vite.inertia.PropFilter
    options:
      heading_level: 4
      members: false

::: litestar_vite.inertia.types.ScrollPropsConfig
    options:
      heading_level: 4
      members: false

::: litestar_vite.inertia.extract_deferred_props
    options:
      heading_level: 4
      show_source: false

::: litestar_vite.inertia.extract_merge_props
    options:
      heading_level: 4
      show_source: false

::: litestar_vite.inertia.extract_once_props
    options:
      heading_level: 4
      show_source: false

::: litestar_vite.inertia.helpers.should_render
    options:
      heading_level: 4
      show_source: false

---

## Shared Props, Flash Messages & History State

::: litestar_vite.inertia.share
    options:
      heading_level: 4
      show_source: false

::: litestar_vite.inertia.get_shared_props
    options:
      heading_level: 4
      show_source: false

::: litestar_vite.inertia.flash
    options:
      heading_level: 4
      show_source: false

::: litestar_vite.inertia.error
    options:
      heading_level: 4
      show_source: false

::: litestar_vite.inertia.clear_history
    options:
      heading_level: 4
      show_source: false

---

## Laravel Precognition & Exception Handling

::: litestar_vite.inertia.precognition.precognition
    options:
      heading_level: 4
      show_source: false

::: litestar_vite.inertia.PrecognitionResponse
    options:
      heading_level: 4
      members: false
      show_source: false

::: litestar_vite.inertia.create_precognition_exception_handler
    options:
      heading_level: 4
      show_source: false

::: litestar_vite.inertia.normalize_validation_errors
    options:
      heading_level: 4
      show_source: false

::: litestar_vite.inertia.create_inertia_exception_response
    options:
      heading_level: 4
      show_source: false

::: litestar_vite.inertia.exception_to_http_response
    options:
      heading_level: 4
      show_source: false

"""Precognition support for real-time form validation.

Precognition is a Laravel protocol for running server-side validation without
executing handler side effects. This module provides Litestar integration.

Usage:
    1. Enable in config: ``InertiaConfig(precognition=True)``
    2. Add ``@precognition`` decorator to route handlers

The plugin automatically handles validation failures (422 responses).
The decorator prevents handler execution on successful validation (204 responses).

See: https://laravel.com/docs/precognition

Note on Rate Limiting:
    Real-time validation can result in many requests. Laravel has no official
    rate limiting solution for Precognition. Consider:
    - Throttling Precognition requests separately from normal requests
    - Using debounce on the frontend (laravel-precognition libraries do this)
    - Implementing custom rate limiting that checks for Precognition header
"""

from functools import wraps
from typing import TYPE_CHECKING, Any

from litestar import MediaType, Response
from litestar.exceptions import ValidationException
from litestar.status_codes import HTTP_204_NO_CONTENT, HTTP_422_UNPROCESSABLE_ENTITY

from litestar_vite.inertia._utils import InertiaHeaders

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar import Request

__all__ = (
    "PrecognitionResponse",
    "create_precognition_exception_handler",
    "normalize_validation_errors",
    "precognition",
)


def normalize_validation_errors(exc: ValidationException, validate_only: "set[str] | None" = None) -> "dict[str, Any]":
    """Normalize Litestar validation errors to Laravel format.

    Laravel's Precognition protocol expects errors in this format:
    ```json
    {
        "message": "The given data was invalid.",
        "errors": {
            "email": ["The email field is required."],
            "password": ["The password must be at least 8 characters."]
        }
    }
    ```

    Args:
        exc: The ValidationException from Litestar.
        validate_only: If provided, only include errors for these fields.
            Used for partial field validation as the user types.

    Returns:
        A dict in Laravel's validation error format.
    """
    errors: "dict[str, list[str]]" = {}

    # Litestar's ValidationException.detail can be:
    # - A string message
    # - A list of error dicts with 'key', 'message', and 'source'
    # - Other structured data
    detail = exc.detail

    if isinstance(detail, list):
        for error in detail:  # pyright: ignore[reportUnknownVariableType]
            if isinstance(error, dict):
                key: str = str(error.get("key", ""))  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
                message: str = str(error.get("message", str(error)))  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
                source: str = str(error.get("source", ""))  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]

                # Build field name from source and key
                if source and key:
                    field_name = f"{source}.{key}" if source != "body" else key
                elif key:
                    field_name = key
                else:
                    field_name = "_root"

                # Filter by validate_only if specified
                if validate_only and field_name not in validate_only:
                    continue

                if field_name not in errors:
                    errors[field_name] = []
                errors[field_name].append(message)
    elif isinstance(detail, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        errors["_root"] = [detail]

    return {"message": "The given data was invalid.", "errors": errors}


class PrecognitionResponse(Response[Any]):
    """Response for successful Precognition validation.

    Returns 204 No Content with Precognition-Success header.
    """

    def __init__(self) -> None:
        super().__init__(
            content=None, status_code=HTTP_204_NO_CONTENT, headers={InertiaHeaders.PRECOGNITION_SUCCESS.value: "true"}
        )


def create_precognition_exception_handler(
    *, fallback_handler: "Callable[[Request[Any, Any, Any], ValidationException], Response[Any]] | None" = None
) -> "Callable[[Request[Any, Any, Any], ValidationException], Response[Any]]":
    """Create an exception handler for ValidationException that supports Precognition.

    This handler checks if the request is a Precognition request and returns
    errors in Laravel's format. For non-Precognition requests, it either uses
    the fallback handler or returns Litestar's default format.

    Args:
        fallback_handler: Optional handler for non-Precognition requests.
            If not provided, returns a standard JSON error response.

    Returns:
        An exception handler function suitable for Litestar's exception_handlers.
    """

    def handler(request: "Request[Any, Any, Any]", exc: ValidationException) -> "Response[Any]":
        # Check if this is a Precognition request
        precognition_header = request.headers.get(InertiaHeaders.PRECOGNITION.value.lower())
        is_precognition = precognition_header == "true"

        if is_precognition:
            # Get validate_only fields for partial validation
            validate_only_header = request.headers.get(InertiaHeaders.PRECOGNITION_VALIDATE_ONLY.value.lower())
            validate_only = (
                {field.strip() for field in validate_only_header.split(",") if field.strip()}
                if validate_only_header
                else None
            )

            # Normalize errors to Laravel format
            error_data = normalize_validation_errors(exc, validate_only)

            # If filtering removed all errors, return success (204)
            if validate_only and not error_data["errors"]:
                return PrecognitionResponse()

            return Response(
                content=error_data,
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                media_type=MediaType.JSON,
                headers={InertiaHeaders.PRECOGNITION.value: "true"},
            )

        # Non-Precognition request - use fallback or default
        if fallback_handler is not None:
            return fallback_handler(request, exc)

        # Default Litestar-style error response
        return Response(
            content={
                "status_code": HTTP_422_UNPROCESSABLE_ENTITY,
                "detail": "Validation failed",
                "extra": exc.detail or [],
            },
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            media_type=MediaType.JSON,
        )

    return handler


def precognition(fn: "Callable[..., Any]") -> "Callable[..., Any]":
    """Decorator to enable Precognition on a route handler.

    When a Precognition request passes DTO validation, this decorator
    returns a 204 No Content response instead of executing the handler body.
    This prevents side effects (database writes, emails, etc.) during validation.

    Args:
        fn: The route handler function to wrap.

    Returns:
        A wrapped handler that short-circuits on valid Precognition requests.

    Example:
        ```python
        from litestar import post
        from litestar_vite.inertia import precognition, InertiaRedirect

        @post("/users")
        @precognition
        async def create_user(data: UserDTO) -> InertiaRedirect:
            # This only runs for actual form submissions
            # Precognition validation requests return 204 automatically
            user = await User.create(**data.dict())
            return InertiaRedirect(request, f"/users/{user.id}")
        ```

    Note:
        - Validation errors are handled by the exception handler (automatic)
        - This decorator handles the success case (prevents handler execution)
        - The decorator checks for Precognition header AFTER DTO validation
    """
    import asyncio

    @wraps(fn)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        # Find the request object in args or kwargs
        request = _find_request(args, kwargs)  # pyright: ignore[reportUnknownVariableType]

        if request is not None:
            # Check for Precognition header
            precognition_header = request.headers.get(InertiaHeaders.PRECOGNITION.value.lower())
            if precognition_header == "true":
                # Validation passed (we got here), return success
                return PrecognitionResponse()

        # Not a Precognition request, run handler normally
        return fn(*args, **kwargs)

    @wraps(fn)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        # Find the request object in args or kwargs
        request = _find_request(args, kwargs)  # pyright: ignore[reportUnknownVariableType]

        if request is not None:
            # Check for Precognition header
            precognition_header = request.headers.get(InertiaHeaders.PRECOGNITION.value.lower())
            if precognition_header == "true":
                # Validation passed (we got here), return success
                return PrecognitionResponse()

        # Not a Precognition request, run handler normally
        result = fn(*args, **kwargs)
        if asyncio.iscoroutine(result):
            return await result
        return result

    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(fn):
        return async_wrapper
    return sync_wrapper


def _find_request(args: tuple[Any, ...], kwargs: "dict[str, Any]") -> "Request[Any, Any, Any] | None":  # pyright: ignore[reportUnknownParameterType]
    """Find Request object in function arguments.

    Args:
        args: Positional arguments to the handler.
        kwargs: Keyword arguments to the handler.

    Returns:
        The Request object if found, otherwise None.
    """
    from litestar import Request

    # Check kwargs first (named 'request' parameter)
    if "request" in kwargs:
        req = kwargs["request"]
        if isinstance(req, Request):  # pyright: ignore[reportUnknownVariableType]
            return req  # pyright: ignore[reportUnknownVariableType]

    # Check positional args
    for arg in args:
        if isinstance(arg, Request):  # pyright: ignore[reportUnknownVariableType]
            return arg  # pyright: ignore[reportUnknownVariableType]

    return None

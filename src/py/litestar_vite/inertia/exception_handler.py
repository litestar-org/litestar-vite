import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import quote, urlparse, urlunparse

from litestar import MediaType
from litestar.connection import Request
from litestar.connection.base import AuthT, StateT, UserT
from litestar.exceptions import (
    HTTPException,
    InternalServerException,
    NotAuthorizedException,
    NotFoundException,
    PermissionDeniedException,
)
from litestar.exceptions.responses import (
    create_debug_response,  # pyright: ignore[reportUnknownVariableType]
    create_exception_response,  # pyright: ignore[reportUnknownVariableType]
)
from litestar.response import Response
from litestar.status_codes import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from litestar_vite.inertia.helpers import error, flash
from litestar_vite.inertia.request import InertiaRequest
from litestar_vite.inertia.response import InertiaBack, InertiaRedirect, InertiaResponse

if TYPE_CHECKING:
    from litestar.connection.base import AuthT, StateT, UserT

    from litestar_vite.inertia.plugin import InertiaPlugin


FIELD_ERR_RE = re.compile(r"field `(.+)`$")
ExceptionHandler = Callable[[Request[Any, Any, Any], Exception], Response[Any]]


def exception_to_http_response(request: "Request[UserT, AuthT, StateT]", exc: "Exception") -> "Response[Any]":
    """Handler for all exceptions subclassed from HTTPException.

    Inertia detection:

    - For InertiaRequest instances, uses the request's derived flags (route component + headers).
    - For plain Request instances (e.g., before routing/when middleware didn't run), falls back
      to checking the ``X-Inertia`` header.

    Args:
        request: The request object.
        exc: The exception to handle.

    Returns:
        The response object.
    """
    is_inertia_header = request.headers.get("x-inertia", "").lower() == "true"
    if isinstance(request, InertiaRequest):
        inertia_enabled = request.inertia_enabled or request.is_inertia or is_inertia_header
    else:
        inertia_enabled = is_inertia_header

    if not inertia_enabled:
        if isinstance(exc, HTTPException):
            return cast("Response[Any]", create_exception_response(request, exc))
        if request.app.debug:
            return cast("Response[Any]", create_debug_response(request, exc))
        detail = str(exc.__cause__) if exc.__cause__ is not None else str(exc)
        return cast("Response[Any]", create_exception_response(request, InternalServerException(detail=detail)))
    return create_inertia_exception_response(request, exc)


def create_inertia_exception_response(request: "Request[UserT, AuthT, StateT]", exc: "Exception") -> "Response[Any]":
    """Create the inertia exception response.

    This function handles exceptions for Inertia-enabled routes, returning appropriate
    responses based on the exception type and status code.

    Note:
        This function uses defensive programming techniques to handle edge cases:
        - Type-safe handling of exception ``extra`` attribute (may be string, list, dict, or None)
        - Graceful handling when InertiaPlugin is not registered
        - Broad exception handling for flash() calls (non-critical operation)

    Args:
        request: The request object.
        exc: The exception to handle.

    Returns:
        The response object, either an InertiaResponse, InertiaRedirect, or InertiaBack.
    """
    is_inertia_header = request.headers.get("x-inertia", "").lower() == "true"
    is_inertia = request.is_inertia if isinstance(request, InertiaRequest) else is_inertia_header

    status_code = exc.status_code if isinstance(exc, HTTPException) else HTTP_500_INTERNAL_SERVER_ERROR
    preferred_type = MediaType.HTML if not is_inertia else MediaType.JSON
    detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
    extras: Any = None
    if isinstance(exc, HTTPException):
        try:
            extras = exc.extra  # pyright: ignore[reportUnknownMemberType]
        except AttributeError:
            extras = None
    content: dict[str, Any] = {"status_code": status_code, "message": detail}

    inertia_plugin: "InertiaPlugin | None"
    try:
        inertia_plugin = request.app.plugins.get("InertiaPlugin")
    except KeyError:
        inertia_plugin = None

    if extras:
        content.update({"extra": extras})

    flash_succeeded = False
    if detail:
        flash_succeeded = flash(request, detail, category="error")

    if extras and isinstance(extras, (list, tuple)) and len(extras) >= 1:  # pyright: ignore[reportUnknownArgumentType]
        first_extra = extras[0]  # pyright: ignore[reportUnknownVariableType]
        if isinstance(first_extra, dict):
            message: dict[str, str] = cast("dict[str, str]", first_extra)
            key_value = message.get("key")
            default_field = f"root.{key_value}" if key_value is not None else "root"
            error_detail = str(message.get("message", detail) or detail)
            match = FIELD_ERR_RE.search(error_detail)
            field = match.group(1) if match else default_field
            error(request, field, error_detail or detail)

    if status_code in {HTTP_422_UNPROCESSABLE_ENTITY, HTTP_400_BAD_REQUEST} or isinstance(
        exc, PermissionDeniedException
    ):
        return InertiaBack(request)

    if inertia_plugin is None:
        return InertiaResponse[Any](media_type=preferred_type, content=content, status_code=status_code)

    is_unauthorized = status_code == HTTP_401_UNAUTHORIZED or isinstance(exc, NotAuthorizedException)
    redirect_to_login = inertia_plugin.config.redirect_unauthorized_to
    if is_unauthorized and redirect_to_login is not None:
        if request.url.path != redirect_to_login:
            # If flash failed (no session), pass error message via query param
            if not flash_succeeded and detail:
                parsed = urlparse(redirect_to_login)
                error_param = f"error={quote(detail, safe='')}"
                query = f"{parsed.query}&{error_param}" if parsed.query else error_param
                redirect_to_login = urlunparse(parsed._replace(query=query))
            return InertiaRedirect(request, redirect_to=redirect_to_login)
        # Already on login page - redirect back so Inertia processes flash messages
        # (Inertia.js shows 4xx responses in a modal instead of updating page state)
        return InertiaBack(request)

    if status_code in {HTTP_404_NOT_FOUND, HTTP_405_METHOD_NOT_ALLOWED} and (
        inertia_plugin.config.redirect_404 is not None and request.url.path != inertia_plugin.config.redirect_404
    ):
        return InertiaRedirect(request, redirect_to=inertia_plugin.config.redirect_404)

    return InertiaResponse[Any](media_type=preferred_type, content=content, status_code=status_code)


def _register_exception_handlers(  # pyright: ignore[reportUnusedFunction]
    exception_handlers: dict[type[Exception] | int, Any], default_handler: ExceptionHandler
) -> None:
    from litestar_vite._typing import (
        ADVANCED_ALCHEMY_INSTALLED,
        SQLSPEC_INSTALLED,
        AdvancedAlchemyDuplicateKeyError,
        AdvancedAlchemyForeignKeyError,
        AdvancedAlchemyIntegrityError,
        AdvancedAlchemyNotFoundError,
        AdvancedAlchemyRepositoryError,
        SQLSpecCheckViolationError,
        SQLSpecForeignKeyViolationError,
        SQLSpecIntegrityError,
        SQLSpecNotFoundError,
        SQLSpecNotNullViolationError,
        SQLSpecRepositoryError,
        SQLSpecUniqueViolationError,
    )

    if ADVANCED_ALCHEMY_INSTALLED:
        exception_handlers[AdvancedAlchemyRepositoryError] = _make_exception_handler(
            not_found_exceptions=(AdvancedAlchemyNotFoundError,),
            conflict_exceptions=(
                AdvancedAlchemyIntegrityError,
                AdvancedAlchemyDuplicateKeyError,
                AdvancedAlchemyForeignKeyError,
            ),
            default_handler=default_handler,
        )

    if SQLSPEC_INSTALLED:
        exception_handlers[SQLSpecRepositoryError] = _make_exception_handler(
            not_found_exceptions=(SQLSpecNotFoundError,),
            conflict_exceptions=(
                SQLSpecIntegrityError,
                SQLSpecUniqueViolationError,
                SQLSpecForeignKeyViolationError,
                SQLSpecCheckViolationError,
                SQLSpecNotNullViolationError,
            ),
            default_handler=default_handler,
        )


def _make_exception_handler(
    *,
    not_found_exceptions: tuple[type[Exception], ...],
    conflict_exceptions: tuple[type[Exception], ...],
    default_handler: ExceptionHandler,
) -> ExceptionHandler:
    def exception_handler(request: Request[Any, Any, Any], exc: Exception) -> Response[Any]:
        detail = _exception_detail(exc)
        if isinstance(exc, not_found_exceptions):
            http_exc: HTTPException = NotFoundException(detail=detail or "Not Found")
        elif isinstance(exc, conflict_exceptions):
            http_exc = HTTPException(detail=detail, status_code=HTTP_409_CONFLICT)
        else:
            http_exc = InternalServerException(detail=detail)
        return default_handler(request, http_exc)

    return exception_handler


def _exception_detail(exc: Exception) -> str:
    detail = getattr(exc, "detail", None)
    if detail:
        return str(detail)
    if exc.__cause__ is not None:
        return str(exc.__cause__)
    return str(exc)

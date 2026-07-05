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
        # Production (non-debug, non-HTTPException): never embed raw exception text.
        # Debug rendering is already returned above by create_debug_response.
        return cast("Response[Any]", create_exception_response(request, InternalServerException()))
    return create_inertia_exception_response(request, exc)


def _exception_detail_for_response(request: "Request[Any, Any, Any]", exc: Exception) -> Any:
    if isinstance(exc, HTTPException):
        return exc.detail
    if request.app.debug:
        return str(exc)
    return "Internal Server Error"


def _exception_extra(exc: Exception) -> Any:
    if not isinstance(exc, HTTPException):
        return None
    try:
        return exc.extra  # pyright: ignore[reportUnknownMemberType]
    except AttributeError:
        return None


def _get_inertia_plugin(request: "Request[Any, Any, Any]") -> "InertiaPlugin | None":
    try:
        return request.app.plugins.get("InertiaPlugin")
    except KeyError:
        return None


def _store_field_errors(request: "Request[Any, Any, Any]", extras: Any, detail: Any) -> None:
    if not extras or not isinstance(extras, (list, tuple)) or len(extras) < 1:  # pyright: ignore[reportUnknownArgumentType]
        return
    first_extra = extras[0]  # pyright: ignore[reportUnknownVariableType]
    if not isinstance(first_extra, dict):
        return
    message: dict[str, str] = cast("dict[str, str]", first_extra)
    key_value = message.get("key")
    default_field = f"root.{key_value}" if key_value is not None else "root"
    error_detail = str(message.get("message", detail) or detail)
    match = FIELD_ERR_RE.search(error_detail)
    field = match.group(1) if match else default_field
    error(request, field, error_detail or str(detail))


def _create_exception_page_response(
    *,
    content: dict[str, Any],
    preferred_type: MediaType,
    route_component: str | None,
    is_inertia: bool,
    status_code: int,
) -> "Response[Any]":
    if is_inertia and route_component is None:
        return Response[Any](content=content, media_type=MediaType.JSON, status_code=status_code)
    return InertiaResponse[Any](media_type=preferred_type, content=content, status_code=status_code)


def _append_error_query(redirect_to: str, detail: Any) -> str:
    parsed = urlparse(redirect_to)
    error_param = f"error={quote(str(detail), safe='')}"
    query = f"{parsed.query}&{error_param}" if parsed.query else error_param
    return urlunparse(parsed._replace(query=query))


def _create_unauthorized_response(
    request: "Request[Any, Any, Any]",
    *,
    detail: Any,
    flash_succeeded: bool,
    inertia_plugin: "InertiaPlugin",
    status_code: int,
    exc: Exception,
) -> "Response[Any] | None":
    is_unauthorized = status_code == HTTP_401_UNAUTHORIZED or isinstance(exc, NotAuthorizedException)
    redirect_to_login = inertia_plugin.config.redirect_unauthorized_to
    if not is_unauthorized or redirect_to_login is None:
        return None
    if request.url.path != redirect_to_login:
        if not flash_succeeded and detail:
            redirect_to_login = _append_error_query(redirect_to_login, detail)
        return InertiaRedirect(request, redirect_to=redirect_to_login)
    return InertiaBack(request)


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
    route_component = request.inertia.route_component if isinstance(request, InertiaRequest) else None

    status_code = exc.status_code if isinstance(exc, HTTPException) else HTTP_500_INTERNAL_SERVER_ERROR
    preferred_type = MediaType.HTML if not is_inertia else MediaType.JSON
    detail = _exception_detail_for_response(request, exc)
    extras = _exception_extra(exc)
    content: dict[str, Any] = {"status_code": status_code, "message": detail}
    inertia_plugin = _get_inertia_plugin(request)

    if extras:
        content.update({"extra": extras})

    flash_succeeded = False
    if detail:
        flash_succeeded = flash(request, detail, category="error")

    _store_field_errors(request, extras, detail)

    if status_code in {HTTP_422_UNPROCESSABLE_ENTITY, HTTP_400_BAD_REQUEST} or isinstance(
        exc, PermissionDeniedException
    ):
        return InertiaBack(request)

    if inertia_plugin is None:
        return _create_exception_page_response(
            content=content,
            preferred_type=preferred_type,
            route_component=route_component,
            is_inertia=is_inertia,
            status_code=status_code,
        )

    unauthorized_response = _create_unauthorized_response(
        request,
        detail=detail,
        flash_succeeded=flash_succeeded,
        inertia_plugin=inertia_plugin,
        status_code=status_code,
        exc=exc,
    )
    if unauthorized_response is not None:
        return unauthorized_response

    if status_code in {HTTP_404_NOT_FOUND, HTTP_405_METHOD_NOT_ALLOWED} and (
        inertia_plugin.config.redirect_404 is not None and request.url.path != inertia_plugin.config.redirect_404
    ):
        return InertiaRedirect(request, redirect_to=inertia_plugin.config.redirect_404)

    return _create_exception_page_response(
        content=content,
        preferred_type=preferred_type,
        route_component=route_component,
        is_inertia=is_inertia,
        status_code=status_code,
    )


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

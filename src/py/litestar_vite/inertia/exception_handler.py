"""Exception handlers that convert Litestar HTTP and validation exceptions into Inertia responses."""

import logging
import re
import types
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Annotated, Any, Union, cast, get_args, get_origin
from urllib.parse import quote, urlparse, urlunparse

from litestar import MediaType
from litestar.connection import Request
from litestar.connection.base import AuthT, StateT, UserT
from litestar.exceptions import (
    HTTPException,
    InternalServerException,
    LitestarException,
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
from litestar_vite.inertia.request import InertiaDetails, InertiaRequest
from litestar_vite.inertia.response import InertiaBack, InertiaExternalRedirect, InertiaRedirect, InertiaResponse
from litestar_vite.inertia.state import has_redirect_state_transport

if TYPE_CHECKING:
    from litestar.connection.base import AuthT, StateT, UserT

    from litestar_vite.inertia.plugin import InertiaPlugin


logger = logging.getLogger("litestar_vite.inertia")
FIELD_ERR_RE = re.compile(r"field `(.+)`$")
ExceptionHandler = Callable[[Request[Any, Any, Any], Exception], Response[Any]]
_INERTIA_OPT_KEYS: tuple[str, ...] = ("component", "page", "inertia")
_INERTIA_RETURN_TYPES: tuple[type[Any], ...] = (InertiaResponse, InertiaRedirect, InertiaBack, InertiaExternalRedirect)
_UNION_ORIGINS: tuple[Any, ...] = (Union, types.UnionType)


def _is_inertia_class(candidate: Any) -> bool:
    if not isinstance(candidate, type):
        return False
    try:
        return issubclass(candidate, _INERTIA_RETURN_TYPES)
    except TypeError:
        return False


def _is_inertia_return_type(candidate: Any) -> bool:
    """Return whether a return type annotation or FieldDefinition denotes an Inertia response."""
    if candidate is None or candidate is Any:
        return False
    if not isinstance(candidate, type) and hasattr(candidate, "annotation"):
        origin: Any = getattr(candidate, "origin", None)
        if origin in _UNION_ORIGINS or getattr(candidate, "is_union", False):
            inner_types: tuple[Any, ...] = tuple(getattr(candidate, "inner_types", ()))
            return any(_is_inertia_return_type(inner) for inner in inner_types)
        next_candidate: Any = origin if origin is not None else candidate.annotation
        return next_candidate is not candidate and _is_inertia_return_type(next_candidate)
    origin = get_origin(candidate)
    if origin in _UNION_ORIGINS:
        return any(_is_inertia_return_type(arg) for arg in get_args(candidate))
    if origin is Annotated:
        args = get_args(candidate)
        return bool(args) and _is_inertia_return_type(args[0])
    return _is_inertia_return_type(origin) if origin is not None else _is_inertia_class(candidate)


def _route_handler_uses_inertia(route_handler: Any) -> bool:
    """Return whether a matched route handler explicitly participates in Inertia.

    Inspects handler ``opt`` markers (``component``, ``page``, ``inertia``) and unwraps
    the handler's parsed return type signature for Inertia response and redirect classes.

    Args:
        route_handler: The matched route handler from ASGI scope.

    Returns:
        ``True`` when the handler declares Inertia options or returns an Inertia response type.
    """
    if route_handler is None:
        return False
    opt: Any = getattr(route_handler, "opt", None)
    if isinstance(opt, Mapping):
        opt_map = cast("Mapping[str, Any]", opt)
        if any(bool(opt_map.get(key)) for key in _INERTIA_OPT_KEYS):
            return True
    try:
        parsed_signature: Any = getattr(route_handler, "parsed_fn_signature", None)
    except (AttributeError, LitestarException, NameError, TypeError):
        return False
    return_type: Any = getattr(parsed_signature, "return_type", None)
    return _is_inertia_return_type(return_type)


def exception_to_http_response(request: "Request[UserT, AuthT, StateT]", exc: "Exception") -> "Response[Any]":
    """Handler for all exceptions subclassed from HTTPException.

    Inertia detection:

    - When routing matched a handler, uses Inertia handling only when the route declares
      a component or when the request carries ``X-Inertia: true`` and the handler opts
      into Inertia via options or an Inertia return type annotation.
    - When routing did not match a handler (such as unmatched 404 or 405 paths), falls
      back to checking the ``X-Inertia`` header so ``redirect_404`` keeps working.

    Server errors (status code 500 or above) are logged server-side and masked to
    ``"Internal Server Error"`` whenever ``app.debug`` is ``False``.

    Args:
        request: The request object.
        exc: The exception to handle.

    Returns:
        The response object.
    """
    scope = cast("Mapping[str, Any]", request.scope)
    route_handler: Any = scope.get("route_handler")
    has_route_component = (
        request.inertia_enabled
        if isinstance(request, InertiaRequest)
        else InertiaDetails(request).route_component is not None
    )
    is_inertia_header = request.headers.get("x-inertia", "").lower() == "true"
    has_inertia_header = (
        (request.is_inertia or is_inertia_header) if isinstance(request, InertiaRequest) else is_inertia_header
    )
    inertia_enabled = (
        has_route_component or (has_inertia_header and _route_handler_uses_inertia(route_handler))
        if route_handler is not None
        else has_inertia_header
    )

    if not inertia_enabled:
        is_debug = bool(getattr(request.app, "debug", False))
        if isinstance(exc, HTTPException):
            if exc.status_code >= HTTP_500_INTERNAL_SERVER_ERROR and not is_debug:
                logger.error("Unhandled server exception (%s)", exc.status_code, exc_info=exc.__cause__ or exc)
                return cast(
                    "Response[Any]",
                    create_exception_response(
                        request, HTTPException(status_code=exc.status_code, detail="Internal Server Error")
                    ),
                )
            return cast("Response[Any]", create_exception_response(request, exc))
        if is_debug:
            return cast("Response[Any]", create_debug_response(request, exc))
        logger.error("Unhandled server exception", exc_info=exc.__cause__ or exc)
        return cast("Response[Any]", create_exception_response(request, InternalServerException()))
    return create_inertia_exception_response(request, exc)


def _exception_detail_for_response(request: "Request[Any, Any, Any]", exc: Exception) -> Any:
    is_debug = bool(getattr(request.app, "debug", False))
    if isinstance(exc, HTTPException):
        if exc.status_code >= HTTP_500_INTERNAL_SERVER_ERROR and not is_debug:
            logger.error("Unhandled server exception (%s)", exc.status_code, exc_info=exc.__cause__ or exc)
            return "Internal Server Error"
        return exc.detail
    if is_debug:
        return str(exc)
    logger.error("Unhandled server exception", exc_info=exc.__cause__ or exc)
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
    """Store field validation errors into request flash state.

    Iterates over each entry in the exception's extra sequence and stages one
    flashed error per valid dictionary entry. For each entry, field name derivation
    prefers regex matching via FIELD_ERR_RE on the error message, falling back
    to 'root.<key>' or 'root'. If multiple entries target the same field name,
    the last write wins. Non-dictionary entries and empty sequences are ignored.

    Args:
        request: The request object.
        extras: The extras sequence from the exception, typically a list or tuple of error dicts.
        detail: The fallback error detail string or object.
    """
    if not extras or not isinstance(extras, (list, tuple)):  # pyright: ignore[reportUnknownArgumentType]
        return
    for item in extras:  # pyright: ignore[reportUnknownVariableType]
        if not isinstance(item, dict):
            continue
        message: dict[str, str] = cast("dict[str, str]", item)
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
    request: "Request[Any, Any, Any]", *, inertia_plugin: "InertiaPlugin", status_code: int, exc: Exception
) -> "Response[Any] | None":
    is_unauthorized = status_code == HTTP_401_UNAUTHORIZED or isinstance(exc, NotAuthorizedException)
    redirect_to_login = inertia_plugin.config.redirect_unauthorized_to
    if not is_unauthorized or redirect_to_login is None:
        return None
    if request.url.path != redirect_to_login:
        return InertiaRedirect(request, redirect_to=redirect_to_login)
    return InertiaBack(request)


def _create_sessionless_unauthorized_response(
    request: "Request[Any, Any, Any]", *, detail: Any, inertia_plugin: "InertiaPlugin", status_code: int, exc: Exception
) -> "Response[Any] | None":
    """Return the query-string fallback before staging redirect-bound state."""
    is_unauthorized = status_code == HTTP_401_UNAUTHORIZED or isinstance(exc, NotAuthorizedException)
    redirect_to_login = inertia_plugin.config.redirect_unauthorized_to
    if (
        not is_unauthorized
        or redirect_to_login is None
        or request.url.path == redirect_to_login
        or has_redirect_state_transport(request)
    ):
        return None
    if detail:
        redirect_to_login = _append_error_query(redirect_to_login, detail)
    return InertiaRedirect(request, redirect_to=redirect_to_login)


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
    is_inertia = (request.is_inertia or is_inertia_header) if isinstance(request, InertiaRequest) else is_inertia_header
    route_component = (
        request.inertia.route_component
        if isinstance(request, InertiaRequest)
        else InertiaDetails(request).route_component
    )

    status_code = exc.status_code if isinstance(exc, HTTPException) else HTTP_500_INTERNAL_SERVER_ERROR
    is_debug = bool(getattr(request.app, "debug", False))
    preferred_type = MediaType.HTML if not is_inertia else MediaType.JSON
    detail = _exception_detail_for_response(request, exc)
    extras = None if status_code >= HTTP_500_INTERNAL_SERVER_ERROR and not is_debug else _exception_extra(exc)
    content: dict[str, Any] = {"status_code": status_code, "message": detail}
    inertia_plugin = _get_inertia_plugin(request)

    if extras:
        content.update({"extra": extras})

    if inertia_plugin is not None:
        unauthorized_response = _create_sessionless_unauthorized_response(
            request, detail=detail, inertia_plugin=inertia_plugin, status_code=status_code, exc=exc
        )
        if unauthorized_response is not None:
            return unauthorized_response

    if detail:
        flash(request, detail, category="error")

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
        request, inertia_plugin=inertia_plugin, status_code=status_code, exc=exc
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
    from litestar_vite.typing import (
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
            is_debug = bool(getattr(request.app, "debug", False))
            http_exc = InternalServerException(detail=detail if is_debug else "Internal Server Error")
            http_exc.__cause__ = exc
        return default_handler(request, http_exc)

    return exception_handler


def _exception_detail(exc: Exception) -> str:
    detail = getattr(exc, "detail", None)
    if detail:
        return str(detail)
    if exc.__cause__ is not None:
        return str(exc.__cause__)
    return str(exc)

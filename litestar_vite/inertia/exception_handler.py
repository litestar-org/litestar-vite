from typing import Any

from litestar import MediaType, Request, Response
from litestar.connection.base import AuthT, StateT, UserT
from litestar.response import Redirect
from litestar.status_codes import (
    HTTP_303_SEE_OTHER,
    HTTP_307_TEMPORARY_REDIRECT,
    HTTP_400_BAD_REQUEST,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from litestar_vite.inertia.response import InertiaResponse, error


def default_httpexception_handler(request: Request[UserT, AuthT, StateT], exc: Exception) -> Response[Any]:
    """Handler for all exceptions subclassed from HTTPException."""
    status_code = getattr(exc, "status_code", HTTP_500_INTERNAL_SERVER_ERROR)
    inertia_enabled = getattr(request, "inertia_enabled", False)
    is_inertia = getattr(request, "is_inertia", False)
    _error_bag = request.headers.get("X-Inertia-Error-Bag", None)
    preferred_type = MediaType.HTML if inertia_enabled and not is_inertia else MediaType.JSON
    content = {"status_code": status_code, "detail": getattr(exc, "detail", "")}
    extra = getattr(exc, "extra", "")
    if extra:
        content.update({"extra": extra})

    if is_inertia:
        detail = getattr(exc, "detail", "")  # litestar exceptions
        extras = getattr(exc, "extra", "")  # msgspec exceptions
        if extras and len(extras) >= 1:
            message = extras[0]
            if isinstance(message, dict):
                error(
                    request,
                    message.get("key", ""),  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
                    message.get("message", detail),  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
                    **{"error_bag": _error_bag} if _error_bag else {},
                )
        if status_code in {HTTP_422_UNPROCESSABLE_ENTITY, HTTP_400_BAD_REQUEST}:
            # redirect to the original page and flash the errors
            return Redirect(
                path=request.headers["Referer"],
                status_code=HTTP_307_TEMPORARY_REDIRECT if request.method == "GET" else HTTP_303_SEE_OTHER,
                cookies=request.cookies,
            )

    return InertiaResponse[Any](
        media_type=preferred_type,
        content=content,
        status_code=status_code,
    )

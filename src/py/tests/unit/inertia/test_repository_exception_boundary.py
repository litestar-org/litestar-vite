"""Repository exception boundary tests."""

import importlib
import sys
import warnings
from types import ModuleType
from typing import Any, cast

import pytest
from litestar import Request, get
from litestar.exceptions import HTTPException
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.response import Response
from litestar.status_codes import HTTP_404_NOT_FOUND, HTTP_409_CONFLICT, HTTP_500_INTERNAL_SERVER_ERROR
from litestar.stores.memory import MemoryStore
from litestar.testing import create_test_client
from litestar.utils.deprecation import LitestarDeprecationWarning

from litestar_vite.config import InertiaConfig, ViteConfig


class _RepositoryException(Exception):
    def __init__(self, detail: str = "") -> None:
        self.detail = detail
        super().__init__(detail)


def _repository_error(name: str, base: type[Exception] = Exception) -> type[Exception]:
    return cast("type[Exception]", type(name, (base,), {}))


def _install_advanced_alchemy_exceptions(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    exceptions = ModuleType("advanced_alchemy.exceptions")

    repository_error = _repository_error("RepositoryError", _RepositoryException)
    integrity_error = _repository_error("IntegrityError", repository_error)
    exceptions.RepositoryError = repository_error
    exceptions.NotFoundError = _repository_error("NotFoundError", repository_error)
    exceptions.IntegrityError = integrity_error
    exceptions.DuplicateKeyError = _repository_error("DuplicateKeyError", integrity_error)
    exceptions.ForeignKeyError = _repository_error("ForeignKeyError", integrity_error)

    import litestar_vite._typing as lv_typing

    monkeypatch.setattr(lv_typing, "ADVANCED_ALCHEMY_INSTALLED", True)
    monkeypatch.setattr(lv_typing, "AdvancedAlchemyRepositoryError", exceptions.RepositoryError)
    monkeypatch.setattr(lv_typing, "AdvancedAlchemyNotFoundError", exceptions.NotFoundError)
    monkeypatch.setattr(lv_typing, "AdvancedAlchemyIntegrityError", exceptions.IntegrityError)
    monkeypatch.setattr(lv_typing, "AdvancedAlchemyDuplicateKeyError", exceptions.DuplicateKeyError)
    monkeypatch.setattr(lv_typing, "AdvancedAlchemyForeignKeyError", exceptions.ForeignKeyError)
    return exceptions


def _install_sqlspec_exceptions(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    exceptions = ModuleType("sqlspec.exceptions")

    repository_error = _repository_error("RepositoryError", _RepositoryException)
    integrity_error = _repository_error("IntegrityError", repository_error)
    exceptions.RepositoryError = repository_error
    exceptions.NotFoundError = _repository_error("NotFoundError", repository_error)
    exceptions.IntegrityError = integrity_error
    exceptions.UniqueViolationError = _repository_error("UniqueViolationError", integrity_error)
    exceptions.ForeignKeyViolationError = _repository_error("ForeignKeyViolationError", integrity_error)
    exceptions.CheckViolationError = _repository_error("CheckViolationError", integrity_error)
    exceptions.NotNullViolationError = _repository_error("NotNullViolationError", integrity_error)

    import litestar_vite._typing as lv_typing

    monkeypatch.setattr(lv_typing, "SQLSPEC_INSTALLED", True)
    monkeypatch.setattr(lv_typing, "SQLSpecRepositoryError", exceptions.RepositoryError)
    monkeypatch.setattr(lv_typing, "SQLSpecNotFoundError", exceptions.NotFoundError)
    monkeypatch.setattr(lv_typing, "SQLSpecIntegrityError", exceptions.IntegrityError)
    monkeypatch.setattr(lv_typing, "SQLSpecUniqueViolationError", exceptions.UniqueViolationError)
    monkeypatch.setattr(lv_typing, "SQLSpecForeignKeyViolationError", exceptions.ForeignKeyViolationError)
    monkeypatch.setattr(lv_typing, "SQLSpecCheckViolationError", exceptions.CheckViolationError)
    monkeypatch.setattr(lv_typing, "SQLSpecNotNullViolationError", exceptions.NotNullViolationError)
    return exceptions


def test_importing_exception_handler_emits_no_litestar_deprecation_warnings() -> None:
    """Importing the exception handler must not touch deprecated Litestar repository modules."""

    sys.modules.pop("litestar_vite.inertia.exception_handler", None)
    with warnings.catch_warnings():
        warnings.simplefilter("error", LitestarDeprecationWarning)
        importlib.import_module("litestar_vite.inertia.exception_handler")


def test_typing_facade_import_emits_no_litestar_deprecation_warnings() -> None:
    """Importing the optional dependency facade must not import deprecated Litestar modules."""

    with warnings.catch_warnings():
        warnings.simplefilter("error", LitestarDeprecationWarning)
        typing_module = importlib.import_module("litestar_vite.typing")

    private_typing = importlib.import_module("litestar_vite._typing")
    assert typing_module.SQLSPEC_INSTALLED is private_typing.SQLSPEC_INSTALLED
    assert typing_module.ADVANCED_ALCHEMY_INSTALLED is private_typing.ADVANCED_ALCHEMY_INSTALLED
    assert issubclass(typing_module.SQLSpecRepositoryError, Exception)
    assert issubclass(typing_module.AdvancedAlchemyRepositoryError, Exception)


def test_repository_exception_handlers_are_not_registered_without_supported_libraries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Optional repository handlers are skipped when supported libraries are absent."""

    import litestar_vite._typing as lv_typing
    from litestar_vite.inertia import InertiaHeaders
    from litestar_vite.plugin import VitePlugin

    monkeypatch.setattr(lv_typing, "ADVANCED_ALCHEMY_INSTALLED", False)
    monkeypatch.setattr(lv_typing, "SQLSPEC_INSTALLED", False)

    @get("/repository", component="Repository", sync_to_thread=False)
    def handler() -> dict[str, str]:
        raise lv_typing.SQLSpecNotFoundError("repository failure")

    with create_test_client(
        [handler],
        middleware=[ServerSideSessionConfig().middleware],
        plugins=[VitePlugin(config=ViteConfig(mode="template", inertia=InertiaConfig()))],
        raise_server_exceptions=False,
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/repository", headers={InertiaHeaders.ENABLED.value: "true"})

    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["props"]["status_code"] == HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.parametrize(
    ("package_name", "exception_name", "expected_status"),
    [
        ("advanced_alchemy", "NotFoundError", HTTP_404_NOT_FOUND),
        ("advanced_alchemy", "IntegrityError", HTTP_409_CONFLICT),
        ("advanced_alchemy", "DuplicateKeyError", HTTP_409_CONFLICT),
        ("advanced_alchemy", "ForeignKeyError", HTTP_409_CONFLICT),
        ("advanced_alchemy", "RepositoryError", HTTP_500_INTERNAL_SERVER_ERROR),
        ("sqlspec", "NotFoundError", HTTP_404_NOT_FOUND),
        ("sqlspec", "IntegrityError", HTTP_409_CONFLICT),
        ("sqlspec", "UniqueViolationError", HTTP_409_CONFLICT),
        ("sqlspec", "ForeignKeyViolationError", HTTP_409_CONFLICT),
        ("sqlspec", "CheckViolationError", HTTP_409_CONFLICT),
        ("sqlspec", "NotNullViolationError", HTTP_409_CONFLICT),
        ("sqlspec", "RepositoryError", HTTP_500_INTERNAL_SERVER_ERROR),
    ],
)
def test_litestar_org_repository_exception_handlers_delegate_to_inertia_response(
    monkeypatch: pytest.MonkeyPatch, package_name: str, exception_name: str, expected_status: int
) -> None:
    """Supported repository exceptions are converted by plugin-registered handlers."""

    from litestar_vite.inertia import InertiaHeaders
    from litestar_vite.plugin import VitePlugin

    advanced_alchemy_exceptions = _install_advanced_alchemy_exceptions(monkeypatch)
    sqlspec_exceptions = _install_sqlspec_exceptions(monkeypatch)
    exception_module = advanced_alchemy_exceptions if package_name == "advanced_alchemy" else sqlspec_exceptions
    exception_type = getattr(exception_module, exception_name)

    @get("/repository", component="Repository", sync_to_thread=False)
    def handler() -> dict[str, str]:
        raise exception_type("repository failure")

    with create_test_client(
        [handler],
        middleware=[ServerSideSessionConfig().middleware],
        plugins=[VitePlugin(config=ViteConfig(mode="template", inertia=InertiaConfig()))],
        raise_server_exceptions=False,
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/repository", headers={InertiaHeaders.ENABLED.value: "true"})

    assert response.status_code == expected_status
    assert response.json()["props"]["status_code"] == expected_status
    assert response.json()["props"]["message"] == "repository failure"


def test_user_repository_exception_handler_can_delegate_to_inertia_response() -> None:
    """End-user repository exceptions still work with direct app-level handlers."""

    from litestar_vite.inertia import InertiaHeaders
    from litestar_vite.inertia.exception_handler import exception_to_http_response
    from litestar_vite.plugin import VitePlugin

    class RepositoryLikeError(Exception):
        pass

    def repository_exception_handler(request: Request[Any, Any, Any], exc: RepositoryLikeError) -> Response[Any]:
        http_exc = HTTPException(detail=str(exc), status_code=HTTP_409_CONFLICT)
        return exception_to_http_response(request, http_exc)

    @get("/repository", component="Repository", sync_to_thread=False)
    def handler() -> dict[str, str]:
        raise RepositoryLikeError("repository failure")

    with create_test_client(
        [handler],
        exception_handlers={RepositoryLikeError: repository_exception_handler},
        middleware=[ServerSideSessionConfig().middleware],
        plugins=[VitePlugin(config=ViteConfig(mode="template", inertia=InertiaConfig()))],
        raise_server_exceptions=False,
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/repository", headers={InertiaHeaders.ENABLED.value: "true"})

    assert response.status_code == HTTP_409_CONFLICT
    assert response.json()["props"]["status_code"] == HTTP_409_CONFLICT
    assert response.json()["props"]["message"] == "repository failure"

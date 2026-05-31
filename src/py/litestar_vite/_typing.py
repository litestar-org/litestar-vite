"""Type and optional-dependency shims used across litestar-vite."""

from importlib import import_module
from importlib.util import find_spec
from typing import Any

__all__ = (
    "ADVANCED_ALCHEMY_INSTALLED",
    "FSSPEC_INSTALLED",
    "JINJA_INSTALLED",
    "SQLSPEC_INSTALLED",
    "AdvancedAlchemyDuplicateKeyError",
    "AdvancedAlchemyForeignKeyError",
    "AdvancedAlchemyIntegrityError",
    "AdvancedAlchemyNotFoundError",
    "AdvancedAlchemyRepositoryError",
    "SQLSpecCheckViolationError",
    "SQLSpecForeignKeyViolationError",
    "SQLSpecIntegrityError",
    "SQLSpecNotFoundError",
    "SQLSpecNotNullViolationError",
    "SQLSpecRepositoryError",
    "SQLSpecUniqueViolationError",
)


def _module_installed(module_name: str) -> bool:
    try:
        return find_spec(module_name) is not None
    except (ImportError, ValueError):
        return False


def _get_exception_type(exception_module: Any, name: str) -> type[Exception] | None:
    exception_type = getattr(exception_module, name, None)
    if isinstance(exception_type, type) and issubclass(exception_type, Exception):
        return exception_type
    return None


def _load_exception_types(module_name: str, names: tuple[str, ...]) -> tuple[type[Exception], ...] | None:
    if not _module_installed(module_name):
        return None
    try:
        exception_module = import_module(module_name)
    except ImportError:
        return None

    exception_types = tuple(
        exception_type for name in names if (exception_type := _get_exception_type(exception_module, name))
    )
    return exception_types if len(exception_types) == len(names) else None


def _placeholder_exception_type(name: str, base: type[Exception] = Exception) -> type[Exception]:
    return type(name, (base,), {"__module__": __name__})


JINJA_INSTALLED = _module_installed("jinja2")
FSSPEC_INSTALLED = _module_installed("fsspec")


AdvancedAlchemyRepositoryError = _placeholder_exception_type("AdvancedAlchemyRepositoryError")
AdvancedAlchemyNotFoundError = _placeholder_exception_type(
    "AdvancedAlchemyNotFoundError", AdvancedAlchemyRepositoryError
)
AdvancedAlchemyIntegrityError = _placeholder_exception_type(
    "AdvancedAlchemyIntegrityError", AdvancedAlchemyRepositoryError
)
AdvancedAlchemyDuplicateKeyError = _placeholder_exception_type(
    "AdvancedAlchemyDuplicateKeyError", AdvancedAlchemyIntegrityError
)
AdvancedAlchemyForeignKeyError = _placeholder_exception_type(
    "AdvancedAlchemyForeignKeyError", AdvancedAlchemyIntegrityError
)


_advanced_alchemy_exception_types = _load_exception_types(
    "advanced_alchemy.exceptions",
    ("RepositoryError", "NotFoundError", "IntegrityError", "DuplicateKeyError", "ForeignKeyError"),
)
ADVANCED_ALCHEMY_INSTALLED = _advanced_alchemy_exception_types is not None
if _advanced_alchemy_exception_types is not None:
    AdvancedAlchemyRepositoryError = _advanced_alchemy_exception_types[0]
    AdvancedAlchemyNotFoundError = _advanced_alchemy_exception_types[1]
    AdvancedAlchemyIntegrityError = _advanced_alchemy_exception_types[2]
    AdvancedAlchemyDuplicateKeyError = _advanced_alchemy_exception_types[3]
    AdvancedAlchemyForeignKeyError = _advanced_alchemy_exception_types[4]


SQLSpecRepositoryError = _placeholder_exception_type("SQLSpecRepositoryError")
SQLSpecNotFoundError = _placeholder_exception_type("SQLSpecNotFoundError", SQLSpecRepositoryError)
SQLSpecIntegrityError = _placeholder_exception_type("SQLSpecIntegrityError", SQLSpecRepositoryError)
SQLSpecUniqueViolationError = _placeholder_exception_type("SQLSpecUniqueViolationError", SQLSpecIntegrityError)
SQLSpecForeignKeyViolationError = _placeholder_exception_type("SQLSpecForeignKeyViolationError", SQLSpecIntegrityError)
SQLSpecCheckViolationError = _placeholder_exception_type("SQLSpecCheckViolationError", SQLSpecIntegrityError)
SQLSpecNotNullViolationError = _placeholder_exception_type("SQLSpecNotNullViolationError", SQLSpecIntegrityError)


_sqlspec_exception_types = _load_exception_types(
    "sqlspec.exceptions",
    (
        "RepositoryError",
        "NotFoundError",
        "IntegrityError",
        "UniqueViolationError",
        "ForeignKeyViolationError",
        "CheckViolationError",
        "NotNullViolationError",
    ),
)
SQLSPEC_INSTALLED = _sqlspec_exception_types is not None
if _sqlspec_exception_types is not None:
    SQLSpecRepositoryError = _sqlspec_exception_types[0]
    SQLSpecNotFoundError = _sqlspec_exception_types[1]
    SQLSpecIntegrityError = _sqlspec_exception_types[2]
    SQLSpecUniqueViolationError = _sqlspec_exception_types[3]
    SQLSpecForeignKeyViolationError = _sqlspec_exception_types[4]
    SQLSpecCheckViolationError = _sqlspec_exception_types[5]
    SQLSpecNotNullViolationError = _sqlspec_exception_types[6]

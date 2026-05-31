# ruff: noqa: A005
"""Public typing and optional-dependency shims."""

from litestar_vite._typing import (
    ADVANCED_ALCHEMY_INSTALLED,
    FSSPEC_INSTALLED,
    JINJA_INSTALLED,
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

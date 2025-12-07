===========
Exceptions
===========

Exception classes for litestar-vite error handling.

All exceptions inherit from the base LitestarViteError class for easy
catching of library-specific errors.

Available Exceptions
--------------------

LitestarViteError
    Base exception for all litestar-vite errors.

MissingDependencyError
    Raised when a required package is not installed (e.g., fsspec for deployment).

ViteExecutableNotFoundError
    Raised when the Vite executable cannot be found.

ViteExecutionError
    Raised when Vite command execution fails.

ViteProcessError
    Raised when the Vite dev server process fails to start or stop.

ManifestNotFoundError
    Raised when the Vite manifest file is not found at the expected location.

AssetNotFoundError
    Raised when a requested asset is not found in the manifest.

.. automodule:: litestar_vite.exceptions
    :members:
    :show-inheritance:

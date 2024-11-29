"""Metadata for the Project."""
from __future__ import annotations

import importlib.metadata

__all__ = ["__version__", "__project__"]

__version__ = importlib.metadata.version("litestar_vite")
"""Version of the project."""
__project__ = importlib.metadata.metadata("litestar_vite")["Name"]
"""Name of the project."""

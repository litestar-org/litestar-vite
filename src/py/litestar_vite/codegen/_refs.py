"""Shared OpenAPI reference resolution helpers."""

from typing import Any

_COMPONENTS_SCHEMAS_PREFIX = "#/components/schemas/"


def extract_schema_ref_name(ref: str) -> "str | None":
    """Return the schema name from a components-schemas reference.

    Returns:
        The trailing schema name, or ``None`` for another reference type.
    """
    if ref.startswith(_COMPONENTS_SCHEMAS_PREFIX):
        return ref[len(_COMPONENTS_SCHEMAS_PREFIX) :]
    return None


def resolve_component_schema_name(name: str, components_schemas: "dict[str, Any]") -> "str | None":
    """Resolve a mangled schema name to a key in ``components.schemas``.

    Returns:
        The resolved key, or ``None`` when no schema matches.
    """
    if name in components_schemas:
        return name
    if "_" not in name:
        return None
    parts = name.split("_")
    for index in range(len(parts)):
        candidate = "_".join(parts[index:])
        if candidate in components_schemas:
            return candidate
    return None

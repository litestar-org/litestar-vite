"""TypeScript conversion helpers for code generation."""

import re
from pathlib import PurePosixPath
from typing import Any, cast

_PATH_PARAM_TYPE_PATTERN = re.compile(r"\{([^:}]+):[^}]+\}")


def normalize_path(path: str) -> str:
    """Normalize route path to use {param} syntax."""
    if not path or path == "/":
        return path
    return _PATH_PARAM_TYPE_PATTERN.sub(r"{\1}", str(PurePosixPath(path)))


def ts_type_from_openapi(schema_dict: dict[str, Any]) -> str:
    """Convert an OpenAPI schema dict to a TypeScript type string.

    This function is intentionally lightweight and mirrors the historical
    behavior used in this project's unit tests (OpenAPI 3.1 union types,
    oneOf nullable patterns, etc.). It is not a full OpenAPI-to-TypeScript
    compiler.
    """
    if not schema_dict:
        return "any"

    ref = schema_dict.get("$ref")
    if isinstance(ref, str) and ref:
        return ref.split("/")[-1]

    # anyOf is treated as "any" (matches Litestar behavior used by tests).
    if "anyOf" in schema_dict:
        return "any"

    const = schema_dict.get("const")
    if const is not None:
        # Preserve the historical "const=False -> any" behavior.
        if const is False:
            return "any"
        return _ts_literal(const)

    enum = schema_dict.get("enum")
    if isinstance(enum, list) and enum:
        enum_values = cast("list[Any]", enum)
        return " | ".join(_ts_literal(v) for v in enum_values)

    one_of = schema_dict.get("oneOf")
    if isinstance(one_of, list) and one_of:
        schemas = cast("list[Any]", one_of)
        union = {_ts_type_from_subschema(s) for s in schemas}
        return _join_union(union)

    all_of = schema_dict.get("allOf")
    if isinstance(all_of, list) and all_of:
        schemas = cast("list[Any]", all_of)
        parts = [_ts_type_from_subschema(s) for s in schemas]
        parts = [p for p in parts if p and p != "any"]
        return " & ".join(parts) if parts else "any"

    schema_type = schema_dict.get("type")
    if isinstance(schema_type, list):
        type_entries = cast("list[Any]", schema_type)
        parts = [_ts_type_from_openapi_type_entry(t, schema_dict) for t in type_entries if isinstance(t, str)]
        return _join_union(set(parts)) if parts else "any"

    if isinstance(schema_type, str):
        return _ts_type_from_openapi_type_entry(schema_type, schema_dict)

    return "any"


def python_type_to_typescript(py_type: str, *, fallback: str = "unknown") -> tuple[str, bool]:
    """Convert a Python typing string representation into a TS type and optionality flag."""
    if not py_type:
        return fallback, False

    normalized = py_type.replace("typing.", "").replace("types.", "")
    optional = "None" in normalized or "NoneType" in normalized or "Optional[" in normalized

    normalized = normalized.replace("NoneType", "None").replace("None", "null")

    mapping: dict[str, str] = {
        "str": "string",
        "int": "number",
        "float": "number",
        "bool": "boolean",
        "dict": "Record<string, unknown>",
        "Dict": "Record<string, unknown>",
        "list": f"{fallback}[]",
        "List": f"{fallback}[]",
        "tuple": f"{fallback}[]",
        "Tuple": f"{fallback}[]",
        "set": f"{fallback}[]",
        "Set": f"{fallback}[]",
        "Any": fallback,
        "unknown": "unknown",
        "null": "null",
    }

    for k, v in mapping.items():
        if normalized == k:
            return v, optional

    return normalized, optional


def collect_ref_names(schema_dict: Any) -> set[str]:
    """Collect referenced component names from an OpenAPI schema dict."""
    refs: set[str] = set()
    if isinstance(schema_dict, dict):
        schema_dict_t = cast("dict[str, Any]", schema_dict)
        ref_any = schema_dict_t.get("$ref")
        if isinstance(ref_any, str) and ref_any.startswith("#/components/schemas/"):
            refs.add(ref_any.split("/")[-1])
        for v in schema_dict_t.values():
            refs.update(collect_ref_names(v))
    elif isinstance(schema_dict, list):
        for item in cast("list[Any]", schema_dict):
            refs.update(collect_ref_names(item))
    return refs


def _ts_type_from_subschema(schema: Any) -> str:
    if isinstance(schema, dict):
        return ts_type_from_openapi(cast("dict[str, Any]", schema))
    return "any"


def _ts_type_from_openapi_type_entry(type_name: str, schema_dict: dict[str, Any]) -> str:
    match type_name:
        case "string":
            return "string"
        case "integer" | "number":
            return "number"
        case "boolean":
            return "boolean"
        case "null":
            return "null"
        case "array":
            items = schema_dict.get("items")
            item_type = _ts_type_from_subschema(items) if isinstance(items, dict) else "unknown"
            return f"{item_type}[]"
        case "object":
            properties = schema_dict.get("properties")
            if not isinstance(properties, dict) or not properties:
                return "{}"

            required_list = schema_dict.get("required")
            required: set[str] = set()
            if isinstance(required_list, list):
                required = {v for v in cast("list[Any]", required_list) if isinstance(v, str)}

            lines: list[str] = ["{"]
            for name, prop_schema in cast("dict[str, Any]", properties).items():
                ts_type = _ts_type_from_subschema(prop_schema)
                optional = "" if name in required else "?"
                lines.append(f"  {name}{optional}: {ts_type};")
            lines.append("}")
            return "\n".join(lines)
        case _:
            return "any"


def _join_union(types: set[str]) -> str:
    if not types:
        return "any"
    if len(types) == 1:
        return next(iter(types))
    return " | ".join(sorted(types))


def _ts_literal(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\\\", "\\\\\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return "any"

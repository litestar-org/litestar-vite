"""TypeScript conversion helpers for code generation."""

import re
from pathlib import PurePosixPath
from typing import Any, cast

_PATH_PARAM_TYPE_PATTERN = re.compile(r"\{([^:}]+):[^}]+\}")

_OPENAPI_STRING_FORMAT_TO_TS_ALIAS: dict[str, str] = {
    "uuid": "UUID",
    "date-time": "DateTime",
    "date": "DateOnly",
    "time": "TimeOnly",
    "duration": "Duration",
    "email": "Email",
    "idn-email": "Email",
    "uri": "URI",
    "url": "URI",
    "iri": "URI",
    "iri-reference": "URI",
    "uri-reference": "URI",
    "uri-template": "URI",
    "ipv4": "IPv4",
    "ipv6": "IPv6",
}


def normalize_path(path: str) -> str:
    """Normalize route path to use {param} syntax.

    Returns:
        Normalized path string.
    """
    if not path or path == "/":
        return path
    return _PATH_PARAM_TYPE_PATTERN.sub(r"{\1}", str(PurePosixPath(path)))


def ts_type_from_openapi(schema_dict: dict[str, Any]) -> str:
    """Convert an OpenAPI schema dict to a TypeScript type string.

    This function is intentionally lightweight and mirrors the historical
    behavior used in this project's unit tests (OpenAPI 3.1 union types,
    oneOf nullable patterns, etc.). It is not a full OpenAPI-to-TypeScript
    compiler.

    Returns:
        A TypeScript type expression string.
    """
    if not schema_dict:
        return "any"

    ref = schema_dict.get("$ref")
    if isinstance(ref, str) and ref:
        return ref.split("/")[-1]

    if "anyOf" in schema_dict and isinstance(schema_dict["anyOf"], list) and schema_dict["anyOf"]:
        schemas = cast("list[Any]", schema_dict["anyOf"])
        union = {ts_type_from_subschema(s) for s in schemas}
        return join_union(union)

    result = "any"
    match schema_dict:
        case {"const": const} if const is not None:
            result = "any" if const is False else ts_literal(const)
        case {"enum": enum} if isinstance(enum, list) and enum:
            enum_values = cast("list[Any]", enum)
            result = " | ".join(ts_literal(v) for v in enum_values)
        case {"oneOf": one_of} if isinstance(one_of, list) and one_of:
            schemas = cast("list[Any]", one_of)
            union = {ts_type_from_subschema(s) for s in schemas}
            result = join_union(union)
        case {"allOf": all_of} if isinstance(all_of, list) and all_of:
            schemas = cast("list[Any]", all_of)
            parts = [wrap_union_for_intersection(ts_type_from_subschema(s)) for s in schemas]
            parts = [p for p in parts if p and p != "any"]
            result = " & ".join(parts) if parts else "any"
        case {"type": list()}:
            type_entries_list: list[Any] = schema_dict["type"]
            parts = [ts_type_from_openapi_type_entry(t, schema_dict) for t in type_entries_list if isinstance(t, str)]
            result = join_union(set(parts)) if parts else "any"
        case {"type": str() as schema_type}:
            result = ts_type_from_openapi_type_entry(schema_type, schema_dict)
        case _:
            pass

    return result


def python_type_to_typescript(py_type: str, *, fallback: str = "unknown") -> tuple[str, bool]:
    """Convert a Python typing string representation into a TS type and optionality flag.

    Returns:
        A tuple of the TypeScript type string and a boolean indicating if the type is optional.
    """
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
    """Collect referenced component names from an OpenAPI schema dict.

    Returns:
        A set of referenced component names.
    """
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


def ts_type_from_subschema(schema: Any) -> str:
    if isinstance(schema, dict):
        return ts_type_from_openapi(cast("dict[str, Any]", schema))
    return "any"


def ts_type_from_openapi_type_entry(type_name: str, schema_dict: dict[str, Any]) -> str:
    primitive_types: dict[str, str] = {
        "string": "string",
        "integer": "number",
        "number": "number",
        "boolean": "boolean",
        "null": "null",
    }

    result = primitive_types.get(type_name, "any")
    if type_name == "string":
        fmt = schema_dict.get("format")
        if isinstance(fmt, str) and fmt:
            result = _OPENAPI_STRING_FORMAT_TO_TS_ALIAS.get(fmt, result)
    if type_name == "array":
        items = schema_dict.get("items")
        item_type = ts_type_from_subschema(items) if isinstance(items, dict) else "unknown"
        result = f"{wrap_for_array(item_type)}[]"
    elif type_name == "object":
        properties = schema_dict.get("properties")
        if not isinstance(properties, dict) or not properties:
            result = "{}"
        else:
            required_list = schema_dict.get("required")
            required: set[str] = set()
            if isinstance(required_list, list):
                required = {v for v in cast("list[Any]", required_list) if isinstance(v, str)}

            lines: list[str] = ["{"]
            for name, prop_schema in cast("dict[str, Any]", properties).items():
                ts_type = ts_type_from_subschema(prop_schema)
                optional = "" if name in required else "?"
                lines.append(f"  {name}{optional}: {ts_type};")
            lines.append("}")
            result = "\n".join(lines)

    return result


def wrap_for_array(type_expr: str) -> str:
    expr = type_expr.strip()
    if not expr:
        return "unknown"
    if expr.startswith("(") and expr.endswith(")"):
        return expr
    # Parenthesize unions/intersections so `(A | B)[]` / `(A & B)[]` is emitted correctly.
    if " | " in expr or (" & " in expr and not expr.startswith("{")):
        return f"({expr})"
    return expr


def wrap_union_for_intersection(type_expr: str) -> str:
    expr = type_expr.strip()
    if not expr:
        return "any"
    if expr.startswith("(") and expr.endswith(")"):
        return expr
    if " | " in expr:
        return f"({expr})"
    return expr


def join_union(types: set[str]) -> str:
    if not types:
        return "any"
    if len(types) == 1:
        return next(iter(types))
    return " | ".join(sorted(types))


def ts_literal(value: Any) -> str:
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

"""OpenAPI integration helpers for code generation.

This module centralizes Litestar private OpenAPI API usage so that the rest of
the codegen logic can remain stable and easier to reason about.
"""

import contextlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from litestar._openapi.datastructures import (  # pyright: ignore[reportPrivateUsage]
    OpenAPIContext,
)
from litestar._openapi.schema_generation import SchemaCreator  # pyright: ignore[reportPrivateUsage]
from litestar.handlers import HTTPRouteHandler
from litestar.openapi.spec import Reference, Schema
from litestar.response import Response as LitestarResponse
from litestar.response import Template
from litestar.response.base import ASGIResponse
from litestar.types.builtin_types import NoneType
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.dto import AbstractDTO


@dataclass(slots=True)
class OpenAPISupport:
    """Best-effort access to Litestar OpenAPI internals.

    Attributes:
        openapi_schema: Exported OpenAPI schema dict (optional).
        context: Litestar OpenAPIContext (optional).
        schema_creator: Litestar SchemaCreator (optional).
    """

    openapi_schema: dict[str, Any] | None
    context: OpenAPIContext | None
    schema_creator: SchemaCreator | None

    @classmethod
    def from_app(cls, app: "Litestar", openapi_schema: dict[str, Any] | None) -> "OpenAPISupport":
        """Create OpenAPISupport from a Litestar application.

        Args:
            app: Litestar application instance.
            openapi_schema: Optional OpenAPI schema dict exported by Litestar.

        Returns:
            OpenAPISupport instance.
        """
        context, creator = try_create_openapi_context(app)
        return cls(openapi_schema=openapi_schema, context=context, schema_creator=creator)

    @property
    def enabled(self) -> bool:
        """Whether OpenAPI support is available."""
        return self.context is not None and self.schema_creator is not None


def try_create_openapi_context(app: "Litestar") -> tuple[OpenAPIContext | None, SchemaCreator | None]:
    """Create OpenAPIContext and SchemaCreator if available.

    This mirrors Litestar's internal OpenAPI setup but is tolerant of missing
    configuration or internal API changes.

    Args:
        app: Litestar application instance.

    Returns:
        Tuple of (OpenAPIContext or None, SchemaCreator or None).
    """
    openapi_config = getattr(app, "openapi_config", None)
    if openapi_config is None:
        return None, None

    with contextlib.suppress(AttributeError, TypeError, ValueError):
        openapi_context = OpenAPIContext(
            openapi_config=openapi_config,  # pyright: ignore[reportUnknownMemberType]
            plugins=app.plugins.openapi,  # pyright: ignore[reportUnknownMemberType]
        )
        return openapi_context, SchemaCreator.from_openapi_context(openapi_context)

    return None, None


def openapi_components_schemas(openapi_schema: dict[str, Any] | None) -> dict[str, Any]:
    """Extract OpenAPI components.schemas dict as a concrete mapping."""
    if not isinstance(openapi_schema, dict):
        return {}
    components = openapi_schema.get("components")
    if not isinstance(components, dict):
        return {}
    schemas = cast("dict[str, Any]", components).get("schemas")
    if not isinstance(schemas, dict):
        return {}
    return cast("dict[str, Any]", schemas)


def merge_generated_components_into_openapi(openapi_schema: dict[str, Any], generated_components: dict[str, Schema]) -> None:
    """Merge generated component schemas into an OpenAPI document."""
    components_any = openapi_schema.get("components")
    if not isinstance(components_any, dict):
        openapi_schema["components"] = {}
        components_any = openapi_schema["components"]

    components_dict = cast("dict[str, Any]", components_any)
    schemas_any = components_dict.get("schemas")
    if not isinstance(schemas_any, dict):
        components_dict["schemas"] = {}
        schemas_any = components_dict["schemas"]

    schemas_dict = cast("dict[str, Any]", schemas_any)
    for component_name, schema in generated_components.items():
        if component_name not in schemas_dict:
            schemas_dict[component_name] = schema.to_schema()


def build_schema_name_map(schema_registry: Any) -> dict[tuple[str, ...], str]:
    """Build a mapping of schema registry keys to final component names.

    Uses the same shortening and de-duplication logic as
    ``SchemaRegistry.generate_components_schemas()``.

    Args:
        schema_registry: Litestar schema registry.

    Returns:
        Mapping of schema keys to component names.
    """
    name_map: dict[tuple[str, ...], str] = {}
    model_name_groups = getattr(schema_registry, "_model_name_groups", {})

    for name, group in model_name_groups.items():
        if len(group) == 1:
            name_map[group[0].key] = name
            continue

        full_keys = [registered_schema.key for registered_schema in group]
        names = ["_".join(k) for k in schema_registry.remove_common_prefix(full_keys)]
        for name_, registered_schema in zip(names, group, strict=False):
            name_map[registered_schema.key] = name_

    return name_map


def schema_name_from_ref(ref: str) -> str:
    """Return the OpenAPI component name from a schema $ref string."""
    return ref.split("/")[-1]


def resolve_page_props_field_definition(
    handler: HTTPRouteHandler,
    schema_creator: SchemaCreator,
) -> tuple[FieldDefinition | None, Schema | Reference | None]:
    """Resolve FieldDefinition and schema result for a handler's response.

    Mirrors Litestar's response schema generation to ensure consistent schema registration.

    Args:
        handler: HTTP route handler.
        schema_creator: Litestar SchemaCreator.

    Returns:
        Tuple of (FieldDefinition or None, Schema/Reference or None).
    """
    field_definition = handler.parsed_fn_signature.return_type

    if field_definition.is_subclass_of((NoneType, ASGIResponse)):
        return None, None

    handler_any = cast("Any", handler)
    resolve_return_dto = cast("Any", getattr(handler_any, "resolve_return_dto", None))
    dto = resolve_return_dto() if callable(resolve_return_dto) else None
    if dto is not None:
        dto_t = cast("type[AbstractDTO[Any]]", dto)
        result = dto_t.create_openapi_schema(
            field_definition=field_definition,
            handler_id=handler.handler_id,
            schema_creator=schema_creator,
        )
        return field_definition, result

    if field_definition.is_subclass_of(Template):
        resolved_field = FieldDefinition.from_annotation(str)
    elif field_definition.is_subclass_of(LitestarResponse):
        resolved_field = (
            field_definition.inner_types[0] if field_definition.inner_types else FieldDefinition.from_annotation(Any)
        )
    else:
        resolved_field = field_definition

    return resolved_field, schema_creator.for_field_definition(resolved_field)


def to_root_path(root_dir: Path, path: Path) -> Path:
    """Resolve a path relative to ``root_dir`` when it is not absolute."""
    return path if path.is_absolute() else (root_dir / path)

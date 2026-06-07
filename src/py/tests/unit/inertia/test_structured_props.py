"""Regression tests for structured handler return types in Inertia mode (issue #272).

A handler returning a ``msgspec.Struct``, dataclass, or pydantic model represents
a bag of page props, exactly like a returned ``dict``. On an initial (non-Inertia)
visit the response must be an HTML bootstrap, and on an Inertia visit the fields
must be spread as top-level props.
"""

from dataclasses import dataclass
from typing import Any

import msgspec
import pydantic
from litestar import get
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.memory import MemoryStore
from litestar.template.config import TemplateConfig
from litestar.testing import create_test_client

from litestar_vite.inertia import InertiaHeaders, InertiaPlugin
from litestar_vite.plugin import VitePlugin


class StructResp(msgspec.Struct):
    name: str


@dataclass
class DataclassResp:
    name: str


class PydanticResp(pydantic.BaseModel):
    name: str


@get("/struct", component="Home", sync_to_thread=False)
def struct_route() -> StructResp:
    return StructResp(name="x")


@get("/dataclass", component="Home", sync_to_thread=False)
def dataclass_route() -> DataclassResp:
    return DataclassResp(name="x")


@get("/pydantic", component="Home", sync_to_thread=False)
def pydantic_route() -> PydanticResp:
    return PydanticResp(name="x")


@get("/dict", component="Home", sync_to_thread=False)
def dict_route() -> dict[str, Any]:
    return {"name": "x"}


# ===== Initial (non-Inertia) visit: HTML bootstrap =====


def test_struct_route_initial_visit_returns_html(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: "TemplateConfig[Any]"
) -> None:
    """A ``msgspec.Struct`` return must bootstrap as HTML on an initial visit."""
    with create_test_client(
        route_handlers=[struct_route, dataclass_route, pydantic_route, dict_route],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        for path in ("/struct", "/dataclass", "/pydantic", "/dict"):
            response = client.get(path)
            assert response.status_code == 200, path
            assert response.headers["content-type"].startswith("text/html"), path


# ===== Inertia visit: fields spread as top-level props =====


def test_struct_route_inertia_visit_spreads_props(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: "TemplateConfig[Any]"
) -> None:
    """Struct/dataclass/pydantic fields must become top-level props, matching ``dict``."""
    with create_test_client(
        route_handlers=[struct_route, dataclass_route, pydantic_route, dict_route],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        for path in ("/struct", "/dataclass", "/pydantic", "/dict"):
            response = client.get(path, headers={InertiaHeaders.ENABLED.value: "true"})
            assert response.status_code == 200, path
            assert response.headers["content-type"].startswith("application/json"), path
            props = response.json()["props"]
            assert props.get("name") == "x", path
            assert "content" not in props, path

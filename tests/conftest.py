from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from litestar_vite.commands import VITE_INIT_TEMPLATES_PATH

if TYPE_CHECKING:
    pass


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def vite_template_env() -> Environment:
    return Environment(
        loader=FileSystemLoader([VITE_INIT_TEMPLATES_PATH]),
        autoescape=select_autoescape(),
    )

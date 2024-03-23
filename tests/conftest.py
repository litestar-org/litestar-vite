from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

pytestmark = pytest.mark.anyio
here = Path(__file__).parent


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def vite_template_env() -> Environment:
    return Environment(
        loader=FileSystemLoader([Path(here.parent / "litestar_vite" / "templates")]),
        autoescape=select_autoescape(),
    )

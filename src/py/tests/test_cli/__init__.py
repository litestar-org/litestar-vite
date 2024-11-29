from __future__ import annotations

APP_DEFAULT_CONFIG_FILE_CONTENT = """
from litestar import Litestar

from litestar_vite import VitePlugin

app = Litestar(plugins=[VitePlugin()])
"""


APP_BASIC_NO_ROUTES_FILE_CONTENT = """
from litestar import Litestar

from litestar_vite import ViteConfig, VitePlugin

vite = VitePlugin(config=ViteConfig(template_dir="{template_dir!s}"))

app = Litestar(plugins=[vite])
"""

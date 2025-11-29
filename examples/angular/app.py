"""Angular SPA example - serves static index.html via Vite.

Demonstrates the Vite proxy integration where Litestar serves the
index.html and Vite handles asset bundling with HMR in development.
"""

from litestar import Litestar

from litestar_vite import ViteConfig, VitePlugin

vite = VitePlugin(config=ViteConfig())

app = Litestar(
    plugins=[vite],
    debug=True,
)

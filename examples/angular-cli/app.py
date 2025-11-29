"""Angular CLI example - standard Angular tooling with Litestar backend.

Angular CLI serves the frontend during development (`npm start`), and the
built assets under ``dist/browser`` are served by Litestar in production.
"""

from pathlib import Path

from litestar import Litestar
from litestar.static_files.config import StaticFilesConfig

here = Path(__file__).parent

app = Litestar(
    static_files_config=[
        StaticFilesConfig(
            path="/",  # serve at root
            directories=[here / "dist" / "browser", here / "public"],
            html_mode=True,  # SPA fallback to index.html
        )
    ],
    debug=True,
)

import os
import sys
from pathlib import Path
from typing import Any

from litestar_vite.__metadata__ import __project__, __version__

current_path = Path(__file__).parent.parent.resolve()
sys.path.append(str(current_path))
# -- Environmental Data ------------------------------------------------------


# -- Project information -----------------------------------------------------
project = __project__
version = __version__
copyright = "2025, Litestar-Org"
author = "Litestar-Org"
release = os.getenv("_LITESTAR_VITE_DOCS_BUILD_VERSION", version.rsplit(".")[0])

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.githubpages",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "auto_pytabs.sphinx_ext",
    "tools.sphinx_ext",
    "sphinx_copybutton",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx_click",
    "sphinx_design",
    "sphinxcontrib.mermaid",
    "sphinx_paramlinks",
    "sphinx_togglebutton",
    "shibuya",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "msgspec": ("https://jcristharif.com/msgspec/", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
    "alembic": ("https://alembic.sqlalchemy.org/en/latest/", None),
    "click": ("https://click.palletsprojects.com/en/stable/", None),
    "anyio": ("https://anyio.readthedocs.io/en/stable/", None),
    "multidict": ("https://multidict.aio-libs.org/en/stable/", None),
    "cryptography": ("https://cryptography.io/en/latest/", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
    "sanic": ("https://sanic.readthedocs.io/en/latest/", None),
    "flask": ("https://flask.palletsprojects.com/en/stable/", None),
    "typing_extensions": ("https://typing-extensions.readthedocs.io/en/stable/", None),
    "jinja2": ("https://jinja.palletsprojects.com/en/stable/", None),
    "litestar": ("https://docs.litestar.dev/latest/", None),
    "structlog": ("https://www.structlog.org/en/stable/", None),
    "markupsafe": ("https://markupsafe.palletsprojects.com/en/latest/", None),
}
PY_CLASS = "py:class"
PY_RE = r"py:.*"
PY_METH = "py:meth"
PY_ATTR = "py:attr"
PY_OBJ = "py:obj"
PY_EXC = "py:exc"

nitpicky = True
nitpick_ignore = [
    # external library / undocumented external
    (PY_CLASS, "ExternalType"),
    (PY_CLASS, "TypeEngine"),
    (PY_CLASS, "UserDefinedType"),
    (PY_METH, "type_engine"),
    # type vars and aliases / intentionally undocumented
    (PY_CLASS, "CollectionT"),
    (PY_CLASS, "EmptyType"),
    (PY_CLASS, "ModelT"),
    (PY_CLASS, "T"),
    (PY_CLASS, "litestar.contrib.jinja.T"),
    (PY_CLASS, "config.app.AppConfig"),
    (PY_OBJ, "litestar.template.config.EngineType"),
    (PY_CLASS, "litestar.template.config.EngineType"),
    # Litestar base types
    (PY_CLASS, "ASGIConnection"),
    (PY_CLASS, "BaseRouteHandler"),
    (PY_CLASS, "UserT"),
    (PY_CLASS, "AuthT"),
    (PY_CLASS, "StateT"),
    (PY_CLASS, "HandlerT"),
    (PY_CLASS, "HTTPScope"),
    (PY_CLASS, "Method"),
    (PY_CLASS, "Logger"),
    (PY_CLASS, "DataContainerType"),
    (PY_CLASS, "middleware.session.base.SessionMiddleware"),
    (PY_CLASS, "background_tasks.BackgroundTask"),
    (PY_CLASS, "background_tasks.BackgroundTasks"),
    (PY_CLASS, "datastructures.Cookie"),
    (PY_CLASS, "enums.MediaType"),
    (PY_CLASS, "connection.Request"),
    (PY_CLASS, "app.Litestar"),
    # Internal types
    (PY_OBJ, "litestar_vite.inertia.helpers.PropKeyT"),
    (PY_OBJ, "litestar_vite.inertia.helpers.StaticT"),
    (PY_CLASS, "litestar_vite.inertia.helpers.PropKeyT"),
    (PY_CLASS, "litestar_vite.inertia.helpers.StaticT"),
    (PY_CLASS, "litestar.connection.base.UserT"),
    (PY_CLASS, "litestar.connection.base.AuthT"),
    (PY_CLASS, "litestar.connection.base.StateT"),
    (PY_CLASS, "litestar.connection.base.HandlerT"),
    (PY_CLASS, "litestar.types.Method"),
    (PY_CLASS, "TypeAliasForwardRef"),
    (PY_OBJ, "litestar.connection.base.UserT"),
    (PY_OBJ, "litestar.connection.base.AuthT"),
    (PY_OBJ, "litestar.connection.base.StateT"),
    (PY_EXC, "ImproperlyConfiguredException"),
    (PY_EXC, "NoRouteMatchFoundException"),
    (PY_EXC, "MissingDependencyError"),
    (PY_CLASS, "Environment"),
    (PY_CLASS, "Template"),
    # litestar-vite config types (not in intersphinx inventory)
    (PY_CLASS, "litestar_vite.config.DeployConfig"),
    (PY_CLASS, "litestar_vite.config.ExternalDevServer"),
    (PY_CLASS, "litestar_vite.config.PathConfig"),
    (PY_CLASS, "litestar_vite.config.RuntimeConfig"),
    (PY_CLASS, "litestar_vite.config.TypeGenConfig"),
    (PY_CLASS, "litestar_vite.config.InertiaConfig"),
    (PY_CLASS, "litestar_vite.config.SPAConfig"),
    (PY_CLASS, "litestar_vite.config.ViteConfig"),
    (PY_CLASS, "TypeGenConfig"),
    (PY_CLASS, "InertiaConfig"),
    (PY_CLASS, "SPAConfig"),
    (PY_CLASS, "DeployConfig"),
    (PY_CLASS, "Get proxy mode. Note"),
    # Inertia types
    (PY_CLASS, "litestar_vite.config.InertiaTypeGenConfig"),
    (PY_CLASS, "InertiaTypeGenConfig"),
    (PY_CLASS, "ScrollPropsConfig"),
    (PY_CLASS, "litestar_vite.inertia.types.ScrollPropsConfig"),
    # Logging and markup types
    (PY_CLASS, "LoggingConfig"),
    (PY_CLASS, "litestar_vite.config.LoggingConfig"),
    (PY_CLASS, "Markup"),
    # External dependencies
    (PY_CLASS, "httpx.AsyncClient"),
    # Codegen internal types (use public module path - remapping handles private paths)
    (PY_CLASS, "litestar_vite.codegen.OpenAPISupport"),
    # Internal async mixin (private module, not in public API)
    (PY_CLASS, "litestar_vite.inertia._async_mixin.AsyncRenderMixin"),
    # External anyio types (intersphinx mapping exists but BlockingPortal not in inventory)
    (PY_CLASS, "BlockingPortal"),
    (PY_CLASS, "anyio.from_thread.BlockingPortal"),
]
nitpick_ignore_regex = [
    (PY_RE, r"litestar_vite.*\.T"),
    (PY_RE, r"litestar\.template\.*\.T"),
    (PY_RE, r"litestar\.contrib\.*\.T"),
    (PY_RE, r"config\.app\.AppConfig"),
]

napoleon_google_docstring = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False
napoleon_attr_annotations = True

autoclass_content = "class"
autodoc_class_signature = "separated"
autodoc_default_options = {"special-members": "__init__", "show-inheritance": True, "members": True}
autodoc_member_order = "bysource"
autodoc_typehints_format = "short"
autodoc_type_aliases: dict[str, str] = {"Path": "pathlib.Path"}

autosectionlabel_prefix_document = True

todo_include_todos = True

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Style configuration -----------------------------------------------------
html_theme = "shibuya"
html_short_title = "Litestar Vite"
html_static_path = ["_static"]
html_css_files = ["theme.css", "layout.css", "code.css"]
html_js_files = ["theme.js"]
html_show_sourcelink = True
html_copy_source = True
html_title = "Litestar Vite"
html_baseurl = "https://litestar-org.github.io/litestar-vite/latest/"
html_favicon = "_static/favicon.svg"
html_context = {
    "source_type": "github",
    "source_user": "litestar-org",
    "source_repo": project.replace("_", "-"),
    "source_version": "main",
    "source_docs_path": "docs/",
    "current_version": "latest",
    "version": release,
}
html_sidebars = {"**": []}

html_theme_options: dict[str, Any] = {
    "logo_target": "/litestar-vite/latest/",
    "light_logo": "_static/logo-light.svg",
    "dark_logo": "_static/logo-dark.svg",
    "accent_color": "amber",
    "page_layout": "default",
    "globaltoc_expand_depth": 0,
    "toctree_titles_only": True,
    "github_url": "https://github.com/litestar-org/litestar-vite",
    "discussion_url": "https://github.com/litestar-org/litestar-vite/discussions",
    "discord_url": "https://discord.gg/X3FJqy8d2j",
    "show_ai_links": True,
    "open_in_chatgpt": True,
    "open_in_claude": True,
    "open_in_perplexity": True,
    "nav_links": [
        {
            "title": "Docs",
            "children": [
                {
                    "title": "Get Started",
                    "url": "usage/index",
                    "summary": "Install litestar-vite and wire it into a Litestar app.",
                },
                {
                    "title": "Frameworks",
                    "url": "frameworks/index",
                    "summary": "React, Vue, Svelte, HTMX, Angular, and SSR framework guides.",
                },
                {
                    "title": "Demos",
                    "url": "demos",
                    "summary": "Scaffolding, HMR, type generation, and production build flows in motion.",
                },
                {
                    "title": "Inertia",
                    "url": "inertia/index",
                    "summary": "Server-driven SPA patterns, protocol details, and SSR notes.",
                },
                {
                    "title": "API Reference",
                    "url": "reference/index",
                    "summary": "Configuration, CLI, plugin, loader, and codegen reference.",
                },
            ],
        },
        {
            "title": "Developers",
            "children": [
                {"title": "Changelog", "url": "changelog", "summary": "Track notable changes and migration points."},
                {
                    "title": "Contribution Guide",
                    "url": "contribution-guide",
                    "summary": "Run docs locally and contribute to the project safely.",
                },
                {
                    "title": "GitHub",
                    "url": "https://github.com/litestar-org/litestar-vite",
                    "summary": "Repository, issues, discussions, and release history.",
                },
            ],
        },
    ],
}

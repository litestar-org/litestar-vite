from __future__ import annotations

from typing import TYPE_CHECKING, Mapping

from tools.sphinx_ext import changelog, missing_references

if TYPE_CHECKING:
    from sphinx.application import Sphinx


def setup(app: Sphinx) -> Mapping[str, bool]:
    ext_config: Mapping[str, bool] = {}
    ext_config.update(missing_references.setup(app))
    ext_config.update(*changelog.setup(app))

    return ext_config

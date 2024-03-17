from __future__ import annotations

from jinja2 import Environment

from litestar_vite.commands import VITE_INIT_TEMPLATES, get_template


def test_get_template(vite_template_env: Environment) -> None:
    init_templates = {
        template_name: get_template(environment=vite_template_env, name=template_name)
        for template_name in VITE_INIT_TEMPLATES
    }
    assert len(init_templates.keys()) > 0

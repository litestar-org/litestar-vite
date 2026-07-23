"""Regression tests for scaffolded package manifests."""

import itertools
import json
from pathlib import Path
from typing import Any

import pytest

from litestar_vite.scaffolding.generator import TemplateContext, get_template_dir, render_template
from litestar_vite.scaffolding.templates import CURRENT_NPM_VERSION_RANGES, FRAMEWORK_TEMPLATES, FrameworkType

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    for key, _ in pairs:
        if key in seen:
            msg = f"duplicate key {key!r}"
            raise ValueError(msg)
        seen.add(key)
    return dict(pairs)


def _render_package_json(framework: FrameworkType, flags: dict[str, bool]) -> str:
    context = TemplateContext(
        project_name="demo",
        framework=FRAMEWORK_TEMPLATES[framework],
        use_tailwind=flags["use_tailwind"],
        enable_ssr=flags["enable_ssr"],
        enable_types=flags["enable_types"],
        generate_zod=flags["generate_zod"],
        generate_client=flags["generate_client"],
    )
    template_dir = get_template_dir()
    framework_package = template_dir / framework.value / "package.json.j2"
    package_template = framework_package if framework_package.exists() else template_dir / "base" / "package.json.j2"
    return render_template(package_template, context.to_dict())


_PACKAGE_FLAG_NAMES = ("use_tailwind", "enable_ssr", "enable_types", "generate_zod", "generate_client")
_PACKAGE_FLAG_COMBOS = [
    dict(zip(_PACKAGE_FLAG_NAMES, combo, strict=True)) for combo in itertools.product([False, True], repeat=5)
]


@pytest.mark.parametrize("framework", list(FrameworkType))
def test_scaffold_manifest_render_has_no_duplicate_keys(framework: FrameworkType) -> None:
    for flags in _PACKAGE_FLAG_COMBOS:
        text = _render_package_json(framework, flags)
        json.loads(text, object_pairs_hook=_reject_duplicate_keys)


def test_scaffold_react_tanstack_issue_303_repro_has_no_duplicate_keys() -> None:
    text = _render_package_json(
        FrameworkType.REACT_TANSTACK,
        {
            "use_tailwind": True,
            "enable_ssr": False,
            "enable_types": True,
            "generate_zod": True,
            "generate_client": True,
        },
    )

    json.loads(text, object_pairs_hook=_reject_duplicate_keys)


@pytest.mark.parametrize("framework", list(FrameworkType))
def test_scaffold_manifest_dependency_versions_are_unique_and_preserved(framework: FrameworkType) -> None:
    for flags in _PACKAGE_FLAG_COMBOS:
        text = _render_package_json(framework, flags)
        parsed = json.loads(text)
        rejecting = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
        assert parsed == rejecting, f"{framework.value}: deduped content changed for flags={flags}"


@pytest.mark.parametrize("framework", list(FrameworkType))
def test_scaffold_manifest_typegen_dependencies_use_compatible_pins(framework: FrameworkType) -> None:
    text = _render_package_json(
        framework,
        {
            "use_tailwind": False,
            "enable_ssr": True,
            "enable_types": True,
            "generate_zod": True,
            "generate_client": True,
        },
    )
    dev_dependencies = json.loads(text).get("devDependencies", {})

    if "@hey-api/openapi-ts" in dev_dependencies:
        assert dev_dependencies["@hey-api/openapi-ts"] == CURRENT_NPM_VERSION_RANGES["@hey-api/openapi-ts"]
        assert dev_dependencies["typescript"] == CURRENT_NPM_VERSION_RANGES["typescript"]


def test_typegen_fallback_pins_match_scaffold_registry() -> None:
    constants_source = (REPOSITORY_ROOT / "src/js/src/shared/constants.ts").read_text()

    assert (
        f'HEY_API_PINNED_SPEC = "@hey-api/openapi-ts@{CURRENT_NPM_VERSION_RANGES["@hey-api/openapi-ts"]}"'
        in constants_source
    )
    assert f'TYPESCRIPT_PINNED_SPEC = "typescript@{CURRENT_NPM_VERSION_RANGES["typescript"]}"' in constants_source

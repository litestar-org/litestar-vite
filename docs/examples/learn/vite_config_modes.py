"""Comparison of the four ViteConfig operating modes in Litestar Vite."""

from __future__ import annotations

from pathlib import Path

from litestar_vite import InertiaConfig, PathConfig, RuntimeConfig, TypeGenConfig, ViteConfig


def build_spa_config() -> ViteConfig:
    """Configure Single-Page Application (SPA) mode with automatic OpenAPI SDK generation."""
    return ViteConfig(
        mode="spa",
        dev_mode=True,
        paths=PathConfig(resource_dir=Path("src"), bundle_dir=Path("dist")),
        runtime=RuntimeConfig(start_dev_server=False),
        types=TypeGenConfig(generate_sdk=True, generate_routes=True),
    )


def build_hybrid_config() -> ViteConfig:
    """Configure Inertia.js v2 Hybrid mode with root HTML shell transformation."""
    return ViteConfig(
        mode="hybrid",
        dev_mode=True,
        paths=PathConfig(resource_dir=Path("resources"), bundle_dir=Path("public/build")),
        inertia=InertiaConfig(root_template="index.html"),
        runtime=RuntimeConfig(start_dev_server=False),
    )


def build_template_config() -> ViteConfig:
    """Configure server-driven Jinja2 Template mode with Vite asset helpers."""
    return ViteConfig(
        mode="template",
        dev_mode=True,
        paths=PathConfig(resource_dir=Path("resources"), bundle_dir=Path("public/build")),
        runtime=RuntimeConfig(start_dev_server=False),
    )


def build_framework_config() -> ViteConfig:
    """Configure Meta-Framework mode for Astro, Nuxt, or SvelteKit."""
    return ViteConfig(
        mode="framework",
        dev_mode=True,
        runtime=RuntimeConfig(port=4321, start_dev_server=False),
        types=TypeGenConfig(generate_sdk=True, generate_routes=True),
    )


def main() -> None:
    """Validate all four operating mode configurations."""
    assert build_spa_config().mode == "spa"
    assert build_hybrid_config().mode == "hybrid"
    assert build_template_config().mode == "template"
    assert build_framework_config().mode == "framework"


__all__ = ("build_framework_config", "build_hybrid_config", "build_spa_config", "build_template_config", "main")

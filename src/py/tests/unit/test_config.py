from pathlib import Path, PosixPath

from litestar_vite.config import (
    BunViteConfig,
    DenoViteConfig,
    NPMViteConfig,
    PathConfig,
    PnpmViteConfig,
    RuntimeConfig,
    ViteConfig,
    YarnViteConfig,
)
from litestar_vite.executor import (
    BunExecutor,
    DenoExecutor,
    NodeenvExecutor,
    NodeExecutor,
    PnpmExecutor,
    YarnExecutor,
)


def test_default_vite_config() -> None:
    config = ViteConfig()
    assert isinstance(config.bundle_dir, Path)
    assert isinstance(config.public_dir, Path)
    assert config.ssr_output_dir is None
    assert isinstance(config.resource_dir, Path)
    assert isinstance(config.root_dir, (Path, PosixPath))
    # Default root is current working directory
    assert config.root_dir == Path.cwd()


def test_bun_vite_config() -> None:
    config = BunViteConfig()
    assert isinstance(config.executor, BunExecutor)
    assert config.run_command == ["bun", "run", "dev"]
    assert config.detect_nodeenv is False


def test_deno_vite_config() -> None:
    config = DenoViteConfig()
    assert isinstance(config.executor, DenoExecutor)
    assert config.run_command == ["deno", "task", "dev"]
    assert config.detect_nodeenv is False


def test_npm_vite_config() -> None:
    config = NPMViteConfig()
    assert isinstance(config.executor, NodeExecutor)
    assert config.detect_nodeenv is False


def test_yarn_vite_config() -> None:
    config = YarnViteConfig()
    assert isinstance(config.executor, YarnExecutor)
    assert config.run_command == ["yarn", "dev"]
    assert config.detect_nodeenv is False


def test_pnpm_vite_config() -> None:
    config = PnpmViteConfig()
    assert isinstance(config.executor, PnpmExecutor)
    assert config.run_command == ["pnpm", "dev"]
    assert config.detect_nodeenv is False


def test_default_executor_nodeenv() -> None:
    config = ViteConfig(runtime=RuntimeConfig(detect_nodeenv=True))
    assert isinstance(config.executor, NodeenvExecutor)


def test_default_executor_node() -> None:
    config = ViteConfig(runtime=RuntimeConfig(detect_nodeenv=False))
    assert isinstance(config.executor, NodeExecutor)


def test_config_health_check_defaults() -> None:
    config = ViteConfig()
    assert config.health_check is False
    assert config.base_url is None


def test_config_custom_health_check() -> None:
    config = ViteConfig(
        runtime=RuntimeConfig(health_check=True),
        base_url="https://cdn.example.com/",
    )
    assert config.health_check is True
    assert config.base_url == "https://cdn.example.com/"


def test_new_config_structure() -> None:
    """Test the new nested config structure."""
    config = ViteConfig(
        mode="spa",
        paths=PathConfig(
            bundle_dir=Path("/app/dist"),
            resource_dir=Path("/app/src"),
        ),
        runtime=RuntimeConfig(
            dev_mode=True,
            hot_reload=True,
            executor="bun",
        ),
        types=True,  # Shorthand for TypeGenConfig(enabled=True)
    )
    assert config.mode == "spa"
    assert config.bundle_dir == Path("/app/dist")
    assert config.resource_dir == Path("/app/src")
    assert config.is_dev_mode is True
    assert config.hot_reload is True
    assert config.types.enabled is True  # type: ignore
    assert isinstance(config.executor, BunExecutor)


def test_dev_mode_shortcut() -> None:
    """Test the dev_mode shortcut on root config."""
    config = ViteConfig(dev_mode=True)
    assert config.runtime.dev_mode is True
    assert config.is_dev_mode is True

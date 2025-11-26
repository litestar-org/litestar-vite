from pathlib import Path, PosixPath

from litestar_vite.config import (
    BunViteConfig,
    DenoViteConfig,
    NPMViteConfig,
    PnpmViteConfig,
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
    assert config.root_dir == PosixPath(".")


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
    config = ViteConfig(detect_nodeenv=True)
    assert isinstance(config.executor, NodeenvExecutor)


def test_default_executor_node() -> None:
    config = ViteConfig(detect_nodeenv=False)
    assert isinstance(config.executor, NodeExecutor)
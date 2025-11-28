from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from litestar_vite.config import TypeGenConfig, ViteConfig
from litestar_vite.doctor import ViteDoctor

if TYPE_CHECKING:
    pass


@pytest.fixture
def vite_config() -> ViteConfig:
    return ViteConfig(
        paths=MagicMock(
            root=Path("/app"),
            bundle_dir=Path("public"),
            hot_file="hot",
            asset_url="/static/",
        ),
        types=TypeGenConfig(
            enabled=True,
            output=Path("src/generated"),
            openapi_path=Path("src/generated/openapi.json"),
            routes_path=Path("src/generated/routes.json"),
            generate_zod=True,
            generate_sdk=False,
        ),
    )


@pytest.fixture
def doctor(vite_config: ViteConfig) -> ViteDoctor:
    return ViteDoctor(config=vite_config)


def test_doctor_detect_base_mismatch(doctor: ViteDoctor, tmp_path: Path) -> None:
    doctor.config.paths.root = tmp_path
    (tmp_path / "vite.config.ts").write_text("""
    export default defineConfig({
        base: '/wrong/',
        plugins: [...litestar({
            assetUrl: '/wrong/',
        })]
    })
    """)

    doctor.run(fix=False)

    assert any(
        i.check == "Asset URL Mismatch" and "Python asset_url '/static/' != JS assetUrl '/wrong/'" in i.message
        for i in doctor.issues
    )


def test_doctor_detect_missing_hotfile(doctor: ViteDoctor, tmp_path: Path) -> None:
    doctor.config.paths.root = tmp_path
    (tmp_path / "vite.config.ts").write_text("""
    export default defineConfig({
        plugins: [...litestar({
            hotFile: 'wrong/hot',
        })]
    })
    """)

    doctor.run(fix=False)

    # Expected default hotFile is public/hot
    expected = "public/hot"
    assert any(
        i.check == "Hot File Mismatch"
        and f"JS hotFile 'wrong/hot' differs from Python default '{expected}'" in i.message
        for i in doctor.issues
    )


def test_doctor_detect_typegen_mismatch(doctor: ViteDoctor, tmp_path: Path) -> None:
    doctor.config.paths.root = tmp_path
    (tmp_path / "vite.config.ts").write_text("""
    export default defineConfig({
        plugins: [...litestar({
            types: {
                enabled: true,
                openapiPath: 'wrong/path.json',
                routesPath: 'wrong/routes.json',
            }
        })]
    })
    """)

    doctor.run(fix=False)

    assert any(i.check == "TypeGen OpenAPI Path Mismatch" for i in doctor.issues)
    assert any(i.check == "TypeGen Routes Path Mismatch" for i in doctor.issues)


def test_doctor_detect_plugin_spread_missing(doctor: ViteDoctor, tmp_path: Path) -> None:
    doctor.config.paths.root = tmp_path
    (tmp_path / "vite.config.ts").write_text("""
    export default defineConfig({
        plugins: [
            litestar({
                input: ['src/main.ts']
            })
        ]
    })
    """)

    doctor.run(fix=False)

    assert any(i.check == "Plugin Spread Missing" for i in doctor.issues)


def test_doctor_detect_typegen_flags_mismatch(doctor: ViteDoctor, tmp_path: Path) -> None:
    doctor.config.paths.root = tmp_path
    # Python config: generate_zod=True, generate_sdk=False
    (tmp_path / "vite.config.ts").write_text("""
    export default defineConfig({
        plugins: [...litestar({
            types: {
                enabled: true,
                generateZod: false,
                generateSdk: true,
            }
        })]
    })
    """)

    doctor.run(fix=False)

    assert any(i.check == "TypeGen generateZod Mismatch" for i in doctor.issues)
    assert any(i.check == "TypeGen generateSdk Mismatch" for i in doctor.issues)


def test_doctor_no_issues(doctor: ViteDoctor, tmp_path: Path) -> None:
    doctor.config.paths.root = tmp_path
    (tmp_path / "vite.config.ts").write_text("""
    export default defineConfig({
        plugins: [...litestar({
            assetUrl: '/static/',
            bundleDirectory: 'public',
            hotFile: 'public/hot',
            types: {
                enabled: true,
                output: 'src/generated',
                openapiPath: 'src/generated/openapi.json',
                routesPath: 'src/generated/routes.json',
                generateZod: true,
                generateSdk: false,
            }
        })]
    })
    """)

    # Mock dist file and node_modules checks since we don't have node_modules in tmp_path
    with patch.object(doctor, "_check_dist_files"), patch.object(doctor, "_check_node_modules"):
        result = doctor.run(fix=False)

    assert result is True
    assert not doctor.issues

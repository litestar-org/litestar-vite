from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from litestar_vite.config import PathConfig, RuntimeConfig, TypeGenConfig, ViteConfig
from litestar_vite.doctor import ViteDoctor, _extract_braced_block, _format_ts_literal, _rel_to_root

if TYPE_CHECKING:
    pass


def _prepare_frontend_dirs(root: Path) -> None:
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "public").mkdir(parents=True, exist_ok=True)


def _prepare_node_modules(root: Path) -> None:
    dist_dir = root / "node_modules" / "@litestar" / "vite-plugin" / "dist" / "js"
    dist_dir.mkdir(parents=True, exist_ok=True)
    for name in ("index.js", "install-hint.js", "litestar-meta.js"):
        (dist_dir / name).write_text("// stub")


@pytest.fixture
def vite_config() -> ViteConfig:
    return ViteConfig(
        mode="spa",
        runtime=RuntimeConfig(dev_mode=False, set_environment=False, proxy_mode="vite", host="127.0.0.1", port=5173),
        paths=PathConfig(
            root=Path("/app"),
            bundle_dir=Path("public"),
            resource_dir=Path("src"),
            static_dir=Path("public"),
            asset_url="/static/",
            hot_file="hot",
        ),
        types=TypeGenConfig(
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
    if isinstance(doctor.config.types, TypeGenConfig):
        doctor.config.types.output = tmp_path / "src" / "generated"
        doctor.config.types.openapi_path = tmp_path / "src" / "generated" / "openapi.json"
        doctor.config.types.routes_path = tmp_path / "src" / "generated" / "routes.json"
    _prepare_frontend_dirs(tmp_path)
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
    _prepare_frontend_dirs(tmp_path)
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
    _prepare_frontend_dirs(tmp_path)
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


def test_doctor_detect_typegen_flags_mismatch(doctor: ViteDoctor, tmp_path: Path) -> None:
    doctor.config.paths.root = tmp_path
    _prepare_frontend_dirs(tmp_path)
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
    if isinstance(doctor.config.types, TypeGenConfig):
        doctor.config.types.output = tmp_path / "src" / "generated"
        doctor.config.types.openapi_path = tmp_path / "src" / "generated" / "openapi.json"
        doctor.config.types.routes_path = tmp_path / "src" / "generated" / "routes.json"
    _prepare_frontend_dirs(tmp_path)
    _prepare_node_modules(tmp_path)
    (tmp_path / "public").mkdir(parents=True, exist_ok=True)
    (tmp_path / "public" / "manifest.json").write_text("{}")
    (tmp_path / "src" / "generated").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "generated" / "openapi.json").write_text("{}")
    (tmp_path / "src" / "generated" / "routes.json").write_text("{}")
    (tmp_path / "vite.config.ts").write_text("""
    export default defineConfig({
        plugins: [litestar({
            assetUrl: '/static/',
            bundleDir: 'public',
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

    with patch.object(doctor, "_check_env_alignment"), patch.object(doctor, "_check_vite_server_reachable"):
        result = doctor.run(fix=False)

    assert result is True
    assert not doctor.issues


def test_doctor_type_paths_mismatch(doctor: ViteDoctor, tmp_path: Path) -> None:
    doctor.config.paths.root = tmp_path
    _prepare_frontend_dirs(tmp_path)
    (tmp_path / "vite.config.ts").write_text("""
    export default defineConfig({
        plugins: [litestar({
            types: {
                enabled: true,
                output: 'src/generated',
                openapiPath: 'src/generated/other-openapi.json',
            }
        })]
    })
    """)

    with (
        patch.object(doctor, "_check_dist_files"),
        patch.object(doctor, "_check_node_modules"),
        patch.object(doctor, "_check_manifest_presence"),
        patch.object(doctor, "_check_typegen_artifacts"),
        patch.object(doctor, "_check_env_alignment"),
        patch.object(doctor, "_check_vite_server_reachable"),
    ):
        doctor.run(fix=False)

    assert any(i.check == "TypeGen OpenAPI Path Mismatch" for i in doctor.issues)


def test_doctor_manifest_missing(doctor: ViteDoctor, tmp_path: Path) -> None:
    doctor.config.paths.root = tmp_path
    _prepare_frontend_dirs(tmp_path)
    doctor.config.paths.bundle_dir = Path(tmp_path / "public")
    doctor.config.runtime.dev_mode = False
    (tmp_path / "vite.config.ts").write_text("""
    export default defineConfig({
        plugins: [...litestar({
            bundleDir: 'REPLACE_ME',
        })]
    })
    """)

    # Replace placeholder with absolute path so Python/JS match
    cfg_path = tmp_path / "vite.config.ts"
    cfg_path.write_text(cfg_path.read_text().replace("REPLACE_ME", str(tmp_path / "public")))

    with patch.object(doctor, "_check_dist_files"), patch.object(doctor, "_check_node_modules"):
        doctor.run(fix=False)

    assert any(i.check == "Manifest Missing" for i in doctor.issues)


def test_doctor_hotfile_missing(doctor: ViteDoctor, tmp_path: Path) -> None:
    doctor.config.paths.root = tmp_path
    _prepare_frontend_dirs(tmp_path)
    doctor.config.paths.bundle_dir = Path(tmp_path / "public")
    doctor.config.runtime.dev_mode = True
    doctor.config.runtime.proxy_mode = "proxy"
    (tmp_path / "public").mkdir(parents=True, exist_ok=True)
    (tmp_path / "vite.config.ts").write_text("""
    export default defineConfig({
        plugins: [...litestar({
            bundleDir: 'REPLACE_ME',
        })]
    })
    """)

    cfg_path = tmp_path / "vite.config.ts"
    cfg_path.write_text(cfg_path.read_text().replace("REPLACE_ME", str(tmp_path / "public")))

    with (
        patch.object(doctor, "_check_dist_files"),
        patch.object(doctor, "_check_node_modules"),
        patch.object(doctor, "_check_vite_server_reachable"),
    ):
        doctor.run(fix=False, runtime_checks=True)

    assert any(i.check == "Hotfile Missing" for i in doctor.issues)


def test_doctor_env_mismatch(doctor: ViteDoctor, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    doctor.config.paths.root = tmp_path
    _prepare_frontend_dirs(tmp_path)
    doctor.config.runtime.port = 5174
    monkeypatch.setenv("VITE_PORT", "9999")
    (tmp_path / "vite.config.ts").write_text("""
    export default defineConfig({
        plugins: [...litestar({
            bundleDir: 'public',
        })]
    })
    """)

    with (
        patch.object(doctor, "_check_dist_files"),
        patch.object(doctor, "_check_node_modules"),
        patch.object(doctor, "_check_manifest_presence"),
        patch.object(doctor, "_check_typegen_artifacts"),
        patch.object(doctor, "_check_vite_server_reachable"),
    ):
        doctor.run(fix=False)

    assert any(i.check == "Env / Config Mismatch" for i in doctor.issues)


def test_doctor_can_write_bridge_file(tmp_path: Path) -> None:
    config = ViteConfig(
        mode="spa",
        runtime=RuntimeConfig(dev_mode=False, set_environment=True, proxy_mode="vite", host="127.0.0.1", port=5173),
        paths=PathConfig(
            root=tmp_path,
            bundle_dir=Path("public"),
            resource_dir=Path("src"),
            static_dir=Path("public"),
            asset_url="/static/",
            hot_file="hot",
        ),
        types=False,
    )
    doctor = ViteDoctor(config=config)
    _prepare_frontend_dirs(tmp_path)
    (tmp_path / "src" / "main.ts").write_text("export {}")
    (tmp_path / "vite.config.ts").write_text("""
    export default defineConfig({
        plugins: [litestar({ input: ['src/main.ts'] })]
    })
    """)

    with (
        patch.object(doctor, "_check_dist_files"),
        patch.object(doctor, "_check_node_modules"),
        patch.object(doctor, "_check_manifest_presence"),
        patch.object(doctor, "_check_typegen_artifacts"),
        patch.object(doctor, "_check_env_alignment"),
        patch.object(doctor, "_check_vite_server_reachable"),
    ):
        ok = doctor.run(fix=True, no_prompt=True)

    assert ok is True
    assert (tmp_path / ".litestar.json").exists()


def test_doctor_helpers_format_and_extract(tmp_path: Path) -> None:
    assert _format_ts_literal(True) == "true"
    assert _format_ts_literal(10) == "10"
    assert _format_ts_literal("hello") == "'hello'"

    source = "export default defineConfig({ plugins: [litestar({ assetUrl: '/static/' })] })"
    open_idx = source.find("{", source.find("litestar"))
    extracted = _extract_braced_block(source, open_idx)
    assert extracted is not None
    block, _, _ = extracted
    assert "assetUrl" in block

    root = tmp_path
    path = tmp_path / "src" / "main.ts"
    assert _rel_to_root(path, root).endswith("src/main.ts")


def test_doctor_apply_vite_key_fix(tmp_path: Path) -> None:
    config = ViteConfig(
        mode="spa",
        runtime=RuntimeConfig(dev_mode=False, set_environment=False, proxy_mode="vite", host="127.0.0.1", port=5173),
        paths=PathConfig(
            root=tmp_path,
            bundle_dir=Path("public"),
            resource_dir=Path("src"),
            static_dir=Path("public"),
            asset_url="/static/",
            hot_file="hot",
        ),
        types=False,
    )
    doctor = ViteDoctor(config=config)
    _prepare_frontend_dirs(tmp_path)
    (tmp_path / "vite.config.ts").write_text("""
    export default defineConfig({
        plugins: [litestar({
            assetUrl: '/wrong/',
        })]
    })
    """)

    with (
        patch.object(doctor, "_check_dist_files"),
        patch.object(doctor, "_check_node_modules"),
        patch.object(doctor, "_check_manifest_presence"),
        patch.object(doctor, "_check_typegen_artifacts"),
        patch.object(doctor, "_check_env_alignment"),
        patch.object(doctor, "_check_vite_server_reachable"),
    ):
        ok = doctor.run(fix=True, no_prompt=True)

    assert ok is True
    content = (tmp_path / "vite.config.ts").read_text()
    assert "assetUrl: '/static/'" in content

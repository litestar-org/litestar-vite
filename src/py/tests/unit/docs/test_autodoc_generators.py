"""Unit tests for the Click CLI and TypeScript 18-subpath auto-documentation generators."""

from pathlib import Path

from litestar.serialization import decode_json
from tools.docs.generate_cli_docs import render_cli_reference
from tools.docs.generate_ts_docs import collect_subpath_docs, render_ts_reference_pages

from litestar_vite.cli import vite_group

REPO_ROOT = Path(__file__).resolve().parents[5]


def test_generate_cli_docs_covers_all_vite_group_commands() -> None:
    """Verify generate_cli_docs renders all 10 litestar assets commands without Rich or Sentinel leaks."""
    rendered = render_cli_reference()
    cli_md_path = REPO_ROOT / "docs" / "reference" / "cli.md"
    assert cli_md_path.exists()
    assert cli_md_path.read_text(encoding="utf-8") == rendered

    assert "Sentinel.UNSET" not in rendered
    assert "[bold" not in rendered
    assert "[/]" not in rendered

    for cmd_name in vite_group.commands:
        assert f"#### `litestar assets {cmd_name}`" in rendered


def test_generate_ts_docs_covers_all_18_package_exports_and_symbols() -> None:
    """Verify generate_ts_docs resolves all 18 package.json exports subpaths and matches on-disk pages."""
    package_json = decode_json((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    exports_map: dict[str, dict[str, str]] = package_json["exports"]
    assert len(exports_map) == 18

    subpaths = collect_subpath_docs(REPO_ROOT)
    assert len(subpaths) == 18
    resolved_keys = {item.subpath for item in subpaths}
    assert resolved_keys == set(exports_map.keys())
    for item in subpaths:
        assert item.source_path.exists(), f"Missing TS source for {item.subpath}: {item.source_path}"
        assert item.symbols, f"No exported symbols extracted for {item.subpath} ({item.source_path})"

    pages = render_ts_reference_pages(subpaths)
    expected_rel_paths = {
        "docs/reference/typescript/index.md",
        "docs/reference/typescript/helpers.md",
        "docs/reference/typescript/frameworks.md",
        "docs/reference/typescript/fragments.md",
    }
    assert set(pages.keys()) == expected_rel_paths

    combined = "\n".join(pages.values())
    for subpath in exports_map:
        import_spec = "litestar-vite-plugin" if subpath == "." else f"litestar-vite-plugin/{subpath.removeprefix('./')}"
        assert import_spec in combined

    for rel_path, content in pages.items():
        on_disk = REPO_ROOT / rel_path
        assert on_disk.exists(), f"Expected generated TS reference page {rel_path}"
        assert on_disk.read_text(encoding="utf-8") == content


def test_contracts_reference_documents_bridge_and_ipc_schemas() -> None:
    """Verify docs/reference/contracts.md documents .litestar.json, routes.json, and IPC envelopes."""
    contracts_path = REPO_ROOT / "docs" / "reference" / "contracts.md"
    assert contracts_path.exists()
    text = contracts_path.read_text(encoding="utf-8")
    for expected in (
        ".litestar.json",
        "routes.json",
        "openapi.json",
        "asyncapi.json",
        "virtual:litestar-static-props",
        "IPCRequest",
        "IPCResponse",
    ):
        assert expected in text

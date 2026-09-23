"""Unit tests for the documentation code example verification gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    """Return the absolute path to the repository root."""
    return Path(__file__).resolve().parent.parent.parent.parent.parent


def test_gate_fails_on_known_bad_fixture(repo_root: Path) -> None:
    """Verify that the gate fails on the seeded representative violation fixture.

    Ensures that the gate exits non-zero, outputs the docs-example prefix,
    identifies the fixture path, and emits diagnostics for each seeded error:
    missing onEvent in TypeScript, undefined websocket_listener in Python, and
    unaccepted enabled keyword argument on TypeGenConfig.
    """
    gate_script = repo_root / "tools" / "check_docs_examples.py"
    fixture_path = repo_root / "tools" / "docs_examples" / "fixtures" / "known_bad.rst"

    result = subprocess.run(
        [sys.executable, str(gate_script), "--paths", str(fixture_path)],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )

    combined_output = result.stdout + "\n" + result.stderr

    assert result.returncode != 0, f"Expected non-zero exit, got {result.returncode}.\nOutput:\n{combined_output}"
    assert "docs-example:" in combined_output
    assert "tools/docs_examples/fixtures/known_bad.rst" in combined_output
    assert "onEvent" in combined_output
    assert "websocket_listener" in combined_output
    assert "enabled" in combined_output


@pytest.mark.xfail(strict=False, reason="Blocked on feat-asyncapi:10.1")
def test_gate_passes_on_docs_tree(repo_root: Path) -> None:
    """Verify that the full documentation tree passes the verification gate.

    Marked as xfail pending completion of feat-asyncapi:10.1, which resolves the
    audit-identified defects in docs/realtime.
    """
    gate_script = repo_root / "tools" / "check_docs_examples.py"

    result = subprocess.run(
        [sys.executable, str(gate_script), "--paths", "docs"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        f"Expected docs tree to pass with 0 exit code, got {result.returncode}.\nOutput:\n{result.stdout}\n{result.stderr}"
    )


def test_skip_marker_is_honored(tmp_path: Path, repo_root: Path) -> None:
    """Verify that the .. docs-example: skip marker excludes intentionally partial snippets."""
    gate_script = repo_root / "tools" / "check_docs_examples.py"
    rst_file = tmp_path / "test_skip.rst"
    rst_file.write_text(
        "Test Document\n"
        "=============\n\n"
        ".. docs-example: skip\n"
        ".. code-block:: python\n\n"
        "   @websocket_listener('/ws')\n"
        "   def handle_ws() -> None:\n"
        "       pass\n\n"
        ".. docs-example: skip\n"
        ".. code-block:: typescript\n\n"
        "   import { createEventStream } from 'litestar-vite-plugin/helpers'\n"
        "   const stream = createEventStream({ url: '/x' })\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(gate_script), "--paths", str(rst_file)],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        f"Expected gate to pass on skipped blocks, got {result.returncode}.\nOutput:\n{result.stdout}\n{result.stderr}"
    )

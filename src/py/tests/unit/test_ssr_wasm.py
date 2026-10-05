"""Unit tests for WasmIPCTransport and SSR transport resolution."""

import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest
from litestar.serialization import decode_json, encode_json

from litestar_vite.config import InertiaConfig, PathConfig, RuntimeConfig, ViteConfig
from litestar_vite.fragments import FragmentEngine
from litestar_vite.ipc import (
    IPCError,
    IPCTimeoutError,
    IPCWorkerCrashError,
    StdioIPCTransport,
    WasmIPCTransport,
    is_wasm_available,
    resolve_ssr_transport,
)
from litestar_vite.plugin import VitePlugin

pytestmark = pytest.mark.anyio


class _FakeQuickJSContext:
    """In-memory QuickJS Context test double supporting sync and Promise-based SSR dispatch."""

    def __init__(self) -> None:
        self.globals: dict[str, Any] = {}
        self.pending_jobs: list[Any] = []
        self.evaluated_scripts: list[str] = []

    def eval(self, script: str) -> Any:
        self.evaluated_scripts.append(script)
        if "missing_dispatch" in script:
            return None
        if "typeof globalThis.__litestar_ssr_dispatch__ === 'function'" in script:
            return callable(self.globals.get("__litestar_ssr_dispatch__"))
        if "globalThis.__litestar_wasm_call__ =" in script:

            def wasm_call(line: str) -> str | None:
                dispatch = self.globals.get("__litestar_ssr_dispatch__")
                if not callable(dispatch):
                    msg = "SSR bundle did not register globalThis.__litestar_ssr_dispatch__"
                    raise RuntimeError(msg)
                self.globals["__litestar_wasm_settled__"] = False
                self.globals["__litestar_wasm_result__"] = ""
                self.globals["__litestar_wasm_error__"] = None
                out: Any = dispatch(line)
                if isinstance(out, str):
                    self.globals["__litestar_wasm_settled__"] = True
                    self.globals["__litestar_wasm_result__"] = out
                    return out

                def settle_job() -> None:
                    try:
                        val = out()
                        self.globals["__litestar_wasm_settled__"] = True
                        self.globals["__litestar_wasm_result__"] = val
                    except Exception as exc:
                        self.globals["__litestar_wasm_settled__"] = True
                        self.globals["__litestar_wasm_error__"] = str(exc)

                self.pending_jobs.append(settle_job)
                return None

            self.globals["__litestar_wasm_call__"] = wasm_call
            return None

        if "async_promise_bundle" in script:

            def async_dispatch(line: str) -> Any:
                req = decode_json(line)
                req_id = req.get("id")

                def deferred() -> str:
                    if req.get("method") == "fail":
                        msg = "async render failed"
                        raise RuntimeError(msg)
                    return encode_json({"id": req_id, "result": {"html": "<p>async-wasm</p>", "head": []}}).decode(
                        "utf-8"
                    )

                return deferred

            self.globals["__litestar_ssr_dispatch__"] = async_dispatch
            return None

        if "__litestar_ssr_dispatch__" not in script:
            return None

        def sync_dispatch(line: str) -> str:
            req = decode_json(line)
            req_id = req.get("id")
            method = req.get("method", "render")
            if method == "ping":
                return encode_json({"id": req_id, "result": {"status": "pong"}}).decode("utf-8")
            if method == "error_payload":
                return encode_json({"id": req_id, "error": "Component crashed"}).decode("utf-8")
            params = req.get("params") or {}
            component = params.get("component", "Default")
            return encode_json({"id": req_id, "result": {"html": f"<div>{component}</div>", "head": []}}).decode(
                "utf-8"
            )

        self.globals["__litestar_ssr_dispatch__"] = sync_dispatch
        return None

    def get(self, name: str) -> Any:
        return self.globals.get(name)

    def execute_pending_job(self) -> bool:
        if not self.pending_jobs:
            return False
        job = self.pending_jobs.pop(0)
        job()
        return True


def _install_fake_quickjs(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_mod = ModuleType("quickjs")
    setattr(fake_mod, "Context", _FakeQuickJSContext)
    monkeypatch.setitem(sys.modules, "quickjs", fake_mod)


async def test_wasm_ipc_transport_lifecycle_and_requests(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify WasmIPCTransport starts, dispatches requests on a worker thread, and closes cleanly."""
    _install_fake_quickjs(monkeypatch)
    bundle = tmp_path / "ssr.js"
    bundle.write_text("globalThis.__litestar_ssr_dispatch__ = function(line) {};", encoding="utf-8")

    transport = WasmIPCTransport(bundle_path=bundle)
    assert transport.is_running is False
    assert transport.bundle_path == bundle

    await transport.start()
    assert transport.is_running is True

    ping_res = await transport.send_request({"method": "ping"})
    assert ping_res["result"] == {"status": "pong"}

    frag_res = await transport.send_request({"method": "render_fragment", "params": {"component": "Card"}})
    assert frag_res["result"] == {"html": "<div>Card</div>", "head": []}

    await transport.close()
    assert transport.is_running is False


async def test_wasm_ipc_transport_drains_async_promise_jobs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify WasmIPCTransport drains QuickJS pending microtask jobs for async dispatch functions."""
    _install_fake_quickjs(monkeypatch)
    bundle = tmp_path / "ssr.js"
    bundle.write_text("/* async_promise_bundle */ globalThis.__litestar_ssr_dispatch__ = async () => {};")

    transport = WasmIPCTransport(bundle_path=bundle)
    res = await transport.send_request({"method": "render"})
    assert res["result"] == {"html": "<p>async-wasm</p>", "head": []}

    with pytest.raises(IPCError, match="async render failed"):
        await transport.send_request({"method": "fail"})

    await transport.close()


async def test_wasm_ipc_transport_raises_on_worker_error_and_missing_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify WasmIPCTransport raises IPCWorkerCrashError on missing bundle or missing dispatch symbol."""
    _install_fake_quickjs(monkeypatch)

    missing_transport = WasmIPCTransport(bundle_path=tmp_path / "missing-ssr.js")
    with pytest.raises(IPCWorkerCrashError, match="SSR bundle not found"):
        await missing_transport.start()

    invalid_bundle = tmp_path / "invalid-ssr.js"
    invalid_bundle.write_text("/* missing_dispatch */ const x = 1;", encoding="utf-8")
    invalid_transport = WasmIPCTransport(bundle_path=invalid_bundle)
    with pytest.raises(IPCWorkerCrashError, match="__litestar_ssr_dispatch__"):
        await invalid_transport.start()

    valid_bundle = tmp_path / "valid-ssr.js"
    valid_bundle.write_text("globalThis.__litestar_ssr_dispatch__ = () => {};", encoding="utf-8")
    valid_transport = WasmIPCTransport(bundle_path=valid_bundle)
    with pytest.raises(IPCError, match="Component crashed"):
        await valid_transport.send_request({"method": "error_payload"})
    await valid_transport.close()


async def test_wasm_ipc_transport_timeout_and_missing_extra(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify WasmIPCTransport enforces request timeouts and reports missing wasm extra cleanly."""
    bundle = tmp_path / "ssr.js"
    bundle.write_text("globalThis.__litestar_ssr_dispatch__ = () => {};", encoding="utf-8")

    def slow_engine(_line: str) -> str:
        time.sleep(0.2)
        return '{"id": 1, "result": {}}'

    slow_transport = WasmIPCTransport(bundle_path=bundle, engine=slow_engine)
    with pytest.raises(IPCTimeoutError, match="timed out"):
        await slow_transport.send_request({"method": "ping"}, timeout=0.02)
    await slow_transport.close()

    monkeypatch.setitem(sys.modules, "quickjs", None)
    monkeypatch.setattr("litestar_vite.ipc._wasm.find_spec", lambda _name: None)
    assert is_wasm_available() is False

    no_extra_transport = WasmIPCTransport(bundle_path=bundle)
    with pytest.raises(IPCError, match=r"litestar-vite\[wasm\]"):
        await no_extra_transport.start()


def test_resolve_ssr_transport_priority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify resolve_ssr_transport priority across explicit wasm, bundled binary, auto fallback, and stdio."""
    _install_fake_quickjs(monkeypatch)
    monkeypatch.setattr("litestar_vite.ipc._wasm.find_spec", lambda name: object() if name == "quickjs" else None)

    wasm_config = ViteConfig(
        mode="template",
        paths=PathConfig(root=tmp_path, resource_dir="resources"),
        runtime=RuntimeConfig(executor="node", dev_mode=False, ssr_transport="wasm"),
        inertia=InertiaConfig(ssr=True),
    )
    wasm_plugin = VitePlugin(config=wasm_config)
    assert isinstance(wasm_plugin.get_ipc_transport(), WasmIPCTransport)
    wasm_engine = FragmentEngine(config=wasm_config, asset_loader=cast("Any", object()))
    assert isinstance(wasm_engine._get_transport(), WasmIPCTransport)

    fake_bin_dir = tmp_path / "venv" / "bin"
    fake_bin_dir.mkdir(parents=True)
    fake_python = fake_bin_dir / "python3"
    fake_python.write_text("", encoding="utf-8")
    bundled_worker = fake_bin_dir / "litestar-ssr-worker"
    bundled_worker.write_text("#!/bin/sh\n", encoding="utf-8")
    bundled_worker.chmod(0o755)
    monkeypatch.setattr(sys, "executable", str(fake_python))

    auto_config = ViteConfig(
        mode="template",
        paths=PathConfig(root=tmp_path, resource_dir="resources"),
        runtime=RuntimeConfig(executor="node", dev_mode=False, ssr_transport="auto"),
        inertia=InertiaConfig(ssr=True),
    )
    bundled_transport = resolve_ssr_transport(auto_config)
    assert isinstance(bundled_transport, StdioIPCTransport)
    assert bundled_transport.command == [str(bundled_worker)]

    bundled_worker.unlink()
    monkeypatch.setattr("litestar_vite.executor.shutil.which", lambda _name: None)
    fallback_transport = resolve_ssr_transport(auto_config)
    assert isinstance(fallback_transport, WasmIPCTransport)

    venv_node = fake_bin_dir / "node"
    venv_node.write_text("#!/bin/sh\n", encoding="utf-8")
    venv_node.chmod(0o755)
    assert isinstance(resolve_ssr_transport(auto_config), StdioIPCTransport)
    system_config = ViteConfig(
        mode="template",
        paths=PathConfig(root=tmp_path, resource_dir="resources"),
        runtime=RuntimeConfig(executor="node", dev_mode=False, ssr_transport="auto", provisioning_mode="system"),
        inertia=InertiaConfig(ssr=True),
    )
    assert isinstance(resolve_ssr_transport(system_config), WasmIPCTransport)


_REAL_ESM_BUNDLE = """\
export const marker = "esm";
const encoded = new TextEncoder().encode("héllo");
const roundtrip = new TextDecoder().decode(encoded);
globalThis.__litestar_ssr_dispatch__ = (line) => {
  const req = JSON.parse(line);
  if (req.method === "spin") {
    for (;;) {}
  }
  if (req.method === "reschedule") {
    const tick = () => { setTimeout(tick, 0); };
    tick();
    return new Promise(() => {});
  }
  return new Promise((resolve) => {
    setTimeout(() => {
      queueMicrotask(() => {
        resolve(JSON.stringify({ id: req.id, result: { html: `<p>${roundtrip}</p>`, head: [] } }));
      });
    }, 0);
  });
};
"""


async def test_wasm_ipc_transport_runs_real_quickjs_esm_bundle_and_recovers_from_timeout(tmp_path: Path) -> None:
    """Real QuickJS engine: ESM bundle loads via Context.module, timers/microtasks drain, and timeouts reset the context."""
    pytest.importorskip("quickjs")
    bundle = tmp_path / "ssr.js"
    bundle.write_text(_REAL_ESM_BUNDLE, encoding="utf-8")

    transport = WasmIPCTransport(bundle_path=bundle)
    first = await transport.send_request({"method": "render", "params": {"component": "Home"}}, timeout=5.0)
    assert first["result"] == {"html": "<p>héllo</p>", "head": []}

    with pytest.raises(IPCTimeoutError):
        await transport.send_request({"method": "spin"}, timeout=0.2)
    assert transport.is_running is False

    second = await transport.send_request({"method": "render"}, timeout=5.0)
    assert second["result"]["html"] == "<p>héllo</p>"
    await transport.close()


@pytest.mark.timeout(10)
async def test_wasm_ipc_transport_drain_deadline_stops_rescheduling_timers(tmp_path: Path) -> None:
    """Real QuickJS engine: a bundle that reschedules timers forever is cut off by the drain deadline, not left spinning."""
    pytest.importorskip("quickjs")
    bundle = tmp_path / "ssr.js"
    bundle.write_text(_REAL_ESM_BUNDLE, encoding="utf-8")

    transport = WasmIPCTransport(bundle_path=bundle)
    await transport.start()
    started = time.monotonic()
    with pytest.raises(IPCTimeoutError, match="draining timers"):
        transport._dispatch_sync('{"id": 1, "method": "reschedule"}', time_limit=0.2)
    assert time.monotonic() - started < 5.0

    with pytest.raises(IPCTimeoutError):
        await transport.send_request({"method": "reschedule"}, timeout=0.2)
    assert transport.is_running is False

    recovered = await transport.send_request({"method": "render"}, timeout=5.0)
    assert recovered["result"]["html"] == "<p>héllo</p>"
    await transport.close()

"""Unit tests for WasmIPCTransport and SSR transport resolution."""

import asyncio
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest
from litestar.serialization import decode_json, encode_json

from litestar_vite.config import InertiaConfig, InertiaSSRConfig, PathConfig, RuntimeConfig, ViteConfig
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
from litestar_vite.ipc._wasm import DEFAULT_WASM_MAX_STACK_SIZE, DEFAULT_WASM_MEMORY_LIMIT, DEFAULT_WASM_TIME_LIMIT
from litestar_vite.plugin import VitePlugin

pytestmark = pytest.mark.anyio


class _FakeQuickJSContext:
    """In-memory QuickJS Context test double supporting sync and Promise-based SSR dispatch."""

    def __init__(self) -> None:
        self.globals: dict[str, Any] = {}
        self.pending_jobs: list[Any] = []
        self.evaluated_scripts: list[str] = []
        self.call_log: list[tuple[str, Any]] = []

    def set_memory_limit(self, limit: int) -> None:
        self.call_log.append(("set_memory_limit", limit))

    def set_max_stack_size(self, size: int) -> None:
        self.call_log.append(("set_max_stack_size", size))

    def set_time_limit(self, limit: float) -> None:
        self.call_log.append(("set_time_limit", limit))

    def eval(self, script: str) -> Any:
        self.call_log.append(("eval", script))
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


def _install_fake_quickjs(monkeypatch: pytest.MonkeyPatch) -> list[_FakeQuickJSContext]:
    created_contexts: list[_FakeQuickJSContext] = []

    def context_factory() -> _FakeQuickJSContext:
        ctx = _FakeQuickJSContext()
        created_contexts.append(ctx)
        return ctx

    fake_mod = ModuleType("quickjs")
    setattr(fake_mod, "Context", context_factory)
    monkeypatch.setitem(sys.modules, "quickjs", fake_mod)
    return created_contexts


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
    """Verify resolve_ssr_transport priority across explicit wasm, auto fallback, and stdio."""
    _install_fake_quickjs(monkeypatch)
    monkeypatch.setattr("litestar_vite.ipc._wasm.find_spec", lambda name: object() if name == "quickjs" else None)
    monkeypatch.setattr("litestar_vite.executor.find_spec", lambda _name: None)

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
    monkeypatch.setattr(sys, "executable", str(fake_python))

    auto_config = ViteConfig(
        mode="template",
        paths=PathConfig(root=tmp_path, resource_dir="resources"),
        runtime=RuntimeConfig(executor="node", dev_mode=False, ssr_transport="auto"),
        inertia=InertiaConfig(ssr=True),
    )
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
    assert transport._executor is not None
    started = time.monotonic()
    loop = asyncio.get_running_loop()
    with pytest.raises(IPCTimeoutError, match="draining timers"):
        await loop.run_in_executor(
            transport._executor, transport._dispatch_sync, '{"id": 1, "method": "reschedule"}', 0.2
        )
    assert time.monotonic() - started < 5.0

    with pytest.raises(IPCTimeoutError):
        await transport.send_request({"method": "reschedule"}, timeout=0.2)
    assert transport.is_running is False

    recovered = await transport.send_request({"method": "render"}, timeout=5.0)
    assert recovered["result"]["html"] == "<p>héllo</p>"
    await transport.close()


@pytest.mark.parametrize(
    ("init_kwargs", "expected_memory", "expected_stack", "expected_time"),
    [
        ({}, DEFAULT_WASM_MEMORY_LIMIT, DEFAULT_WASM_MAX_STACK_SIZE, DEFAULT_WASM_TIME_LIMIT),
        (
            {"memory_limit": 32 * 1024 * 1024, "max_stack_size": 256 * 1024, "time_limit": 3.5},
            32 * 1024 * 1024,
            256 * 1024,
            3.5,
        ),
        (
            {"memory_limit": 16 * 1024 * 1024, "max_stack_size": 128 * 1024, "time_limit": None},
            16 * 1024 * 1024,
            128 * 1024,
            None,
        ),
    ],
)
async def test_wasm_ipc_transport_configures_resource_limits_before_eval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    init_kwargs: dict[str, Any],
    expected_memory: int,
    expected_stack: int,
    expected_time: float | None,
) -> None:
    """WasmIPCTransport applies memory, stack, and time limits on the QuickJS context before any eval."""
    contexts = _install_fake_quickjs(monkeypatch)
    bundle = tmp_path / "ssr.js"
    bundle.write_text("globalThis.__litestar_ssr_dispatch__ = function(line) {};", encoding="utf-8")

    transport = WasmIPCTransport(bundle_path=bundle, **init_kwargs)
    assert transport.memory_limit == expected_memory
    assert transport.max_stack_size == expected_stack
    assert transport.time_limit == expected_time

    await transport.start()
    assert len(contexts) == 1
    call_log = contexts[0].call_log
    first_eval_idx = next(idx for idx, (name, _val) in enumerate(call_log) if name == "eval")
    pre_eval_calls = call_log[:first_eval_idx]

    expected_calls: list[tuple[str, Any]] = [
        ("set_memory_limit", expected_memory),
        ("set_max_stack_size", expected_stack),
    ]
    if expected_time is not None:
        expected_calls.append(("set_time_limit", expected_time))

    assert pre_eval_calls == expected_calls
    await transport.close()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"memory_limit": 0},
        {"memory_limit": -1},
        {"max_stack_size": 0},
        {"max_stack_size": -1},
        {"time_limit": 0.0},
        {"time_limit": -0.5},
    ],
)
def test_wasm_ipc_transport_rejects_non_positive_limits(tmp_path: Path, kwargs: dict[str, Any]) -> None:
    """WasmIPCTransport raises ValueError when configured with zero or negative resource limits."""
    with pytest.raises(ValueError, match="must be positive"):
        WasmIPCTransport(bundle_path=tmp_path / "ssr.js", **kwargs)


async def test_wasm_ipc_transport_send_request_clamps_timeout_to_time_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """send_request bounds per-dispatch QuickJS time limit to min(timeout, transport.time_limit)."""
    contexts = _install_fake_quickjs(monkeypatch)
    bundle = tmp_path / "ssr.js"
    bundle.write_text("globalThis.__litestar_ssr_dispatch__ = function(line) {};", encoding="utf-8")

    transport = WasmIPCTransport(bundle_path=bundle, time_limit=1.25)
    await transport.send_request({"method": "ping"}, timeout=10.0)

    dispatch_time_limits = [val for name, val in contexts[0].call_log if name == "set_time_limit"]
    assert dispatch_time_limits == [1.25, 1.25]

    await transport.send_request({"method": "ping"}, timeout=0.5)
    dispatch_time_limits = [val for name, val in contexts[0].call_log if name == "set_time_limit"]
    assert dispatch_time_limits == [1.25, 1.25, 0.5]
    await transport.close()


@pytest.mark.parametrize(
    (
        "use_config",
        "runtime_kwargs",
        "inertia_config",
        "explicit_ssr_config",
        "expected_memory",
        "expected_stack",
        "expected_time",
    ),
    [
        (
            True,
            {"ssr_transport": "wasm"},
            None,
            None,
            DEFAULT_WASM_MEMORY_LIMIT,
            DEFAULT_WASM_MAX_STACK_SIZE,
            DEFAULT_WASM_TIME_LIMIT,
        ),
        (
            True,
            {"ssr_transport": "wasm"},
            InertiaConfig(ssr=InertiaSSRConfig(timeout=2.5)),
            None,
            DEFAULT_WASM_MEMORY_LIMIT,
            DEFAULT_WASM_MAX_STACK_SIZE,
            2.5,
        ),
        (
            True,
            {
                "ssr_transport": "wasm",
                "wasm_memory_limit": 64 * 1024 * 1024,
                "wasm_max_stack_size": 512 * 1024,
                "wasm_time_limit": 1.5,
            },
            InertiaConfig(ssr=InertiaSSRConfig(timeout=4.0)),
            None,
            64 * 1024 * 1024,
            512 * 1024,
            1.5,
        ),
        (
            True,
            {"ssr_transport": "auto", "wasm_memory_limit": 32 * 1024 * 1024, "wasm_max_stack_size": 256 * 1024},
            None,
            InertiaSSRConfig(timeout=3.25),
            32 * 1024 * 1024,
            256 * 1024,
            3.25,
        ),
        (False, {}, None, InertiaSSRConfig(timeout=1.75), DEFAULT_WASM_MEMORY_LIMIT, DEFAULT_WASM_MAX_STACK_SIZE, 1.75),
    ],
)
def test_resolve_ssr_transport_propagates_wasm_resource_limits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    use_config: bool,
    runtime_kwargs: dict[str, Any],
    inertia_config: InertiaConfig | None,
    explicit_ssr_config: InertiaSSRConfig | None,
    expected_memory: int,
    expected_stack: int,
    expected_time: float,
) -> None:
    """resolve_ssr_transport passes configured memory, stack, and SSR-aligned time limits to WasmIPCTransport."""
    _install_fake_quickjs(monkeypatch)
    monkeypatch.setattr("litestar_vite.ipc._wasm.find_spec", lambda name: object() if name == "quickjs" else None)
    monkeypatch.setattr("litestar_vite.executor.find_spec", lambda _name: None)
    monkeypatch.setattr("litestar_vite.executor.shutil.which", lambda _name: None)

    fake_bin_dir = tmp_path / "venv" / "bin"
    fake_bin_dir.mkdir(parents=True)
    fake_python = fake_bin_dir / "python3"
    fake_python.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "executable", str(fake_python))

    config: ViteConfig | None = None
    if use_config:
        config = ViteConfig(
            mode="template",
            paths=PathConfig(root=tmp_path, resource_dir="resources"),
            runtime=RuntimeConfig(executor="node", dev_mode=False, **runtime_kwargs),
            inertia=inertia_config,
        )

    transport = resolve_ssr_transport(config, ssr_config=explicit_ssr_config)
    assert isinstance(transport, WasmIPCTransport)
    assert transport.memory_limit == expected_memory
    assert transport.max_stack_size == expected_stack
    assert transport.time_limit == expected_time


_REAL_SYNC_RESOURCE_LIMIT_BUNDLE = """\
globalThis.__litestar_ssr_dispatch__ = (line) => {
  const req = JSON.parse(line);
  if (req.method === "oom") {
    const chunks = [];
    for (let i = 0; i < 1000000; i++) {
      chunks.push("x".repeat(4096));
    }
  }
  if (req.method === "recurse") {
    const recurse = (n) => recurse(n + 1);
    recurse(0);
  }
  return JSON.stringify({ id: req.id, result: { html: "<p>ok-sync</p>", head: [] } });
};
"""

_REAL_ASYNC_RESOURCE_LIMIT_BUNDLE = """\
globalThis.__litestar_ssr_dispatch__ = async (line) => {
  const req = JSON.parse(line);
  await Promise.resolve();
  if (req.method === "oom") {
    const chunks = [];
    for (let i = 0; i < 1000000; i++) {
      chunks.push("x".repeat(4096));
    }
  }
  if (req.method === "recurse") {
    const recurse = (n) => recurse(n + 1);
    recurse(0);
  }
  return JSON.stringify({ id: req.id, result: { html: "<p>ok-async</p>", head: [] } });
};
"""


@pytest.mark.timeout(15)
@pytest.mark.parametrize(
    ("bundle_source", "expected_html"),
    [(_REAL_SYNC_RESOURCE_LIMIT_BUNDLE, "<p>ok-sync</p>"), (_REAL_ASYNC_RESOURCE_LIMIT_BUNDLE, "<p>ok-async</p>")],
)
@pytest.mark.parametrize("failure_method", ["oom", "recurse"])
async def test_wasm_ipc_transport_real_quickjs_resource_limits_and_recovery(
    tmp_path: Path, bundle_source: str, expected_html: str, failure_method: str
) -> None:
    """Real QuickJS engine: OOM and stack overflow raise IPCWorkerCrashError, reset the context, and recover."""
    pytest.importorskip("quickjs")
    bundle = tmp_path / "ssr.js"
    bundle.write_text(bundle_source, encoding="utf-8")

    transport = WasmIPCTransport(
        bundle_path=bundle, memory_limit=2 * 1024 * 1024, max_stack_size=64 * 1024, time_limit=5.0
    )
    initial = await transport.send_request({"method": "render"}, timeout=5.0)
    assert initial["result"] == {"html": expected_html, "head": []}
    assert transport.is_running is True

    with pytest.raises(IPCWorkerCrashError):
        await transport.send_request({"method": failure_method}, timeout=5.0)
    assert transport.is_running is False

    recovered = await transport.send_request({"method": "render"}, timeout=5.0)
    assert recovered["result"] == {"html": expected_html, "head": []}
    assert transport.is_running is True
    await transport.close()

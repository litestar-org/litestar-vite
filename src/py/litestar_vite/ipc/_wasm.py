"""In-process WebAssembly / embedded QuickJS IPC transport for SSR and Fragments."""

import asyncio
import importlib
import re
import sys
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from importlib.util import find_spec
from pathlib import Path
from typing import Any, cast

from litestar.exceptions import SerializationException
from litestar.serialization import decode_json, encode_json

from litestar_vite.config._inertia import InertiaConfig, InertiaSSRConfig
from litestar_vite.config._paths import PathConfig, resolve_ssr_bundle_path
from litestar_vite.config._vite import ViteConfig
from litestar_vite.executor import JSExecutor, find_bundled_ssr_worker, resolve_ssr_command
from litestar_vite.ipc._base import BaseIPCTransport, IPCError, IPCTimeoutError, IPCWorkerCrashError
from litestar_vite.ipc._stdio import StdioIPCTransport

__all__ = ("WasmIPCTransport", "is_wasm_available", "resolve_ssr_transport")

_ESM_SYNTAX_RE = re.compile(
    r"^\s*(?:import(?:\s+[\w$]|\s*[{*'\"])|export\s+(?:default|const|let|var|function|class|async|\{|\*))", re.MULTILINE
)

_QUICKJS_GLOBALS_SHIM = """\
globalThis.process = globalThis.process || { env: { NODE_ENV: 'production' } };
globalThis.console = globalThis.console || { log(){}, warn(){}, error(){}, info(){}, debug(){} };
globalThis.queueMicrotask = globalThis.queueMicrotask || function(cb) { Promise.resolve().then(cb); };
globalThis.__litestar_wasm_timers__ = [];
globalThis.__litestar_wasm_timer_seq__ = 0;
globalThis.setTimeout = globalThis.setTimeout || function(cb, delay) {
    const id = ++globalThis.__litestar_wasm_timer_seq__;
    const args = Array.prototype.slice.call(arguments, 2);
    globalThis.__litestar_wasm_timers__.push({ id: id, cb: cb, delay: Number(delay) || 0, args: args });
    return id;
};
globalThis.clearTimeout = globalThis.clearTimeout || function(id) {
    const timers = globalThis.__litestar_wasm_timers__;
    for (let i = 0; i < timers.length; i++) {
        if (timers[i].id === id) { timers.splice(i, 1); return; }
    }
};
globalThis.setInterval = globalThis.setInterval || globalThis.setTimeout;
globalThis.clearInterval = globalThis.clearInterval || globalThis.clearTimeout;
globalThis.setImmediate = globalThis.setImmediate || function(cb) {
    return globalThis.setTimeout.apply(null, [cb, 0].concat(Array.prototype.slice.call(arguments, 1)));
};
globalThis.clearImmediate = globalThis.clearImmediate || globalThis.clearTimeout;
globalThis.__litestar_wasm_run_timer__ = function() {
    const timers = globalThis.__litestar_wasm_timers__;
    if (timers.length === 0) { return false; }
    let idx = 0;
    for (let i = 1; i < timers.length; i++) { if (timers[i].delay < timers[idx].delay) { idx = i; } }
    const next = timers.splice(idx, 1)[0];
    try {
        next.cb.apply(null, next.args);
    } catch (err) {
        globalThis.__litestar_wasm_settled__ = true;
        globalThis.__litestar_wasm_error__ = err && err.message ? String(err.message) : String(err);
    }
    return true;
};
if (typeof globalThis.TextEncoder === 'undefined') {
    globalThis.TextEncoder = class TextEncoder {
        get encoding() { return 'utf-8'; }
        encode(input) {
            const str = String(input === undefined ? '' : input);
            const out = [];
            for (let i = 0; i < str.length; i++) {
                let cp = str.codePointAt(i);
                if (cp > 0xffff) { i++; }
                if (cp < 0x80) { out.push(cp); }
                else if (cp < 0x800) { out.push(0xc0 | (cp >> 6), 0x80 | (cp & 0x3f)); }
                else if (cp < 0x10000) { out.push(0xe0 | (cp >> 12), 0x80 | ((cp >> 6) & 0x3f), 0x80 | (cp & 0x3f)); }
                else { out.push(0xf0 | (cp >> 18), 0x80 | ((cp >> 12) & 0x3f), 0x80 | ((cp >> 6) & 0x3f), 0x80 | (cp & 0x3f)); }
            }
            return new Uint8Array(out);
        }
    };
}
if (typeof globalThis.TextDecoder === 'undefined') {
    globalThis.TextDecoder = class TextDecoder {
        constructor(label) { this._label = (label || 'utf-8').toLowerCase(); }
        get encoding() { return this._label; }
        decode(input) {
            if (input === undefined) { return ''; }
            const bytes = input instanceof Uint8Array ? input : new Uint8Array(input.buffer || input);
            let out = '';
            for (let i = 0; i < bytes.length;) {
                const b0 = bytes[i++];
                let cp;
                if (b0 < 0x80) { cp = b0; }
                else if (b0 < 0xe0) { cp = ((b0 & 0x1f) << 6) | (bytes[i++] & 0x3f); }
                else if (b0 < 0xf0) { cp = ((b0 & 0x0f) << 12) | ((bytes[i++] & 0x3f) << 6) | (bytes[i++] & 0x3f); }
                else { cp = ((b0 & 0x07) << 18) | ((bytes[i++] & 0x3f) << 12) | ((bytes[i++] & 0x3f) << 6) | (bytes[i++] & 0x3f); }
                out += String.fromCodePoint(cp);
            }
            return out;
        }
    };
}
"""

_QUICKJS_DISPATCH_WRAPPER = (
    "globalThis.__litestar_wasm_call__ = function(line) {\n"
    "    globalThis.__litestar_wasm_settled__ = false;\n"
    "    globalThis.__litestar_wasm_result__ = '';\n"
    "    globalThis.__litestar_wasm_error__ = null;\n"
    "    const out = globalThis.__litestar_ssr_dispatch__(line);\n"
    "    if (typeof out === 'string') {\n"
    "        globalThis.__litestar_wasm_settled__ = true;\n"
    "        globalThis.__litestar_wasm_result__ = out;\n"
    "        return out;\n"
    "    }\n"
    "    if (out && typeof out.then === 'function') {\n"
    "        out.then(\n"
    "            function(val) {\n"
    "                globalThis.__litestar_wasm_settled__ = true;\n"
    "                globalThis.__litestar_wasm_result__ = String(val);\n"
    "            },\n"
    "            function(err) {\n"
    "                globalThis.__litestar_wasm_settled__ = true;\n"
    "                globalThis.__litestar_wasm_error__ = err && err.message ? String(err.message) : String(err);\n"
    "            }\n"
    "        );\n"
    "        return null;\n"
    "    }\n"
    "    globalThis.__litestar_wasm_settled__ = true;\n"
    "    globalThis.__litestar_wasm_result__ = String(out ?? '');\n"
    "    return globalThis.__litestar_wasm_result__;\n"
    "};\n"
)


def is_wasm_available() -> bool:
    """Return True when the in-process QuickJS runtime (``litestar-vite[wasm]``) is importable."""
    if "quickjs" in sys.modules:
        return sys.modules.get("quickjs") is not None
    try:
        return find_spec("quickjs") is not None
    except (ImportError, ValueError):
        return False


class WasmIPCTransport(BaseIPCTransport):
    """In-process SSR transport executing self-contained SSR bundles via QuickJS."""

    __slots__ = ("_bundle_path", "_context", "_engine", "_executor", "_is_running", "_lock", "_request_id")

    def __init__(self, bundle_path: Path, *, engine: Callable[[str], str] | None = None) -> None:
        """Initialize the in-process WASM/QuickJS SSR transport.

        Args:
            bundle_path: Path to the self-contained SSR JavaScript bundle.
            engine: Optional synchronous callable ``(line: str) -> str`` override for testing.
        """
        self._bundle_path = bundle_path
        self._engine = engine
        self._context: Any = None
        self._executor: ThreadPoolExecutor | None = None
        self._is_running = False
        self._lock = asyncio.Lock()
        self._request_id = 0

    @property
    def bundle_path(self) -> Path:
        """Return the configured SSR bundle path."""
        return self._bundle_path

    @property
    def is_running(self) -> bool:
        """Return True if the in-process SSR context is initialized and ready."""
        return self._is_running

    def _init_context_sync(self) -> None:
        """Initialize the QuickJS context and evaluate the SSR bundle on the worker thread."""
        try:
            quickjs = importlib.import_module("quickjs")
        except ImportError as exc:
            msg = "WasmIPCTransport requires the 'wasm' extra. Install it with: pip install 'litestar-vite[wasm]'"
            raise IPCError(msg) from exc

        context_cls = getattr(quickjs, "Context", None)
        if not callable(context_cls):
            msg = "Installed 'quickjs' module does not provide a callable Context class."
            raise IPCError(msg)

        bundle_source = self._bundle_path.read_text(encoding="utf-8")
        ctx: Any = context_cls()
        try:
            ctx.eval(_QUICKJS_GLOBALS_SHIM)
            self._evaluate_bundle(ctx, bundle_source)
            has_dispatch = bool(ctx.eval("typeof globalThis.__litestar_ssr_dispatch__ === 'function'"))
        except Exception as exc:
            msg = f"Failed to evaluate SSR bundle at {self._bundle_path}: {exc}"
            raise IPCWorkerCrashError(msg) from exc

        if not has_dispatch:
            msg = f"SSR bundle at {self._bundle_path} did not register globalThis.__litestar_ssr_dispatch__"
            raise IPCWorkerCrashError(msg)

        ctx.eval(_QUICKJS_DISPATCH_WRAPPER)
        self._context = ctx

    @staticmethod
    def _evaluate_bundle(ctx: Any, source: str) -> None:
        """Evaluate the SSR bundle as an ES module when it uses ESM syntax, otherwise as a classic script.

        Vite emits ``ssr.js`` in ESM format by default; QuickJS rejects
        top-level ``import``/``export`` in script mode, so such bundles are
        loaded through ``Context.module`` when the engine exposes it.
        """
        module_eval = getattr(ctx, "module", None)
        if callable(module_eval) and _ESM_SYNTAX_RE.search(source) is not None:
            module_eval(source)
            return
        ctx.eval(source)

    @staticmethod
    def _is_interrupt_error(exc: BaseException) -> bool:
        """Return True when a QuickJS exception denotes the engine's time-limit interrupt."""
        return "interrupted" in str(exc).lower()

    def _drain_jobs(self, ctx: Any, deadline: float | None) -> None:
        """Run pending Promise jobs and shimmed timers until the dispatch settles or no work remains.

        Args:
            ctx: Active QuickJS context.
            deadline: ``time.monotonic()`` instant after which draining aborts. Each timer
                callback is a fresh Python-to-JS call, so the engine time limit alone cannot
                stop a bundle that keeps rescheduling timers.

        Raises:
            IPCTimeoutError: If ``deadline`` passes before the dispatch settles.
        """
        execute_job = getattr(ctx, "execute_pending_job", None)
        run_timer = ctx.get("__litestar_wasm_run_timer__")
        while True:
            if callable(execute_job):
                while execute_job():
                    pass
            if ctx.get("__litestar_wasm_settled__"):
                return
            if deadline is not None and time.monotonic() >= deadline:
                msg = "WASM SSR dispatch did not settle before the time limit while draining timers"
                raise IPCTimeoutError(msg)
            if not callable(run_timer) or not run_timer():
                return

    def _dispatch_sync(self, request_line: str, time_limit: float | None = None) -> str:
        """Dispatch a single NDJSON request line on the worker thread and drain Promise jobs.

        Args:
            request_line: Encoded NDJSON request.
            time_limit: CPU time budget in seconds enforced by the engine
                (``Context.set_time_limit``) so runaway JavaScript is interrupted
                instead of wedging the single worker thread.

        Raises:
            IPCTimeoutError: If the engine interrupted execution.
            IPCError: If the bundle reported an error or never settled.
            IPCWorkerCrashError: If the context or bridge is not initialized.
        """
        if self._engine is not None:
            return self._engine(request_line)

        if self._context is None:
            msg = "WASM SSR context is not initialized."
            raise IPCWorkerCrashError(msg)

        ctx = self._context
        wasm_call = ctx.get("__litestar_wasm_call__")
        if not callable(wasm_call):
            msg = "WASM SSR dispatch bridge is not initialized."
            raise IPCWorkerCrashError(msg)

        set_time_limit = getattr(ctx, "set_time_limit", None)
        if time_limit is not None and callable(set_time_limit):
            set_time_limit(time_limit)
        deadline = time.monotonic() + time_limit if time_limit is not None else None

        try:
            direct = wasm_call(request_line)
            if isinstance(direct, str):
                return direct
            self._drain_jobs(ctx, deadline)
        except IPCTimeoutError:
            raise
        except Exception as exc:
            if self._is_interrupt_error(exc):
                msg = f"WASM SSR execution exceeded the {time_limit}s time limit"
                raise IPCTimeoutError(msg) from exc
            raise

        error_val = ctx.get("__litestar_wasm_error__")
        if error_val:
            raise IPCError(str(error_val))

        settled = ctx.get("__litestar_wasm_settled__")
        if not settled:
            msg = "SSR Promise did not settle within synchronous microtask execution."
            raise IPCError(msg)

        result_val = ctx.get("__litestar_wasm_result__")
        return str(result_val or "")

    async def start(self) -> None:
        """Initialize the dedicated worker thread and evaluate the SSR bundle."""
        if self._is_running:
            return

        if self._engine is None:
            if not is_wasm_available():
                msg = "WasmIPCTransport requires the 'wasm' extra. Install it with: pip install 'litestar-vite[wasm]'"
                raise IPCError(msg)
            if not self._bundle_path.is_file():
                msg = f"SSR bundle not found at {self._bundle_path}"
                raise IPCWorkerCrashError(msg)

        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="litestar-vite-wasm-ssr")
        if self._engine is None:
            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(self._executor, self._init_context_sync)
            except Exception:
                self._executor.shutdown(wait=False, cancel_futures=True)
                self._executor = None
                raise

        self._is_running = True

    async def close(self) -> None:
        """Shut down the worker thread and release the QuickJS context."""
        self._is_running = False
        self._context = None
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None

    def _reset_after_timeout(self) -> None:
        """Discard the wedged context and executor so the next request rebuilds a fresh engine.

        A timed-out dispatch may still be executing on the worker thread until
        the engine's interrupt fires; abandoning the executor guarantees that
        subsequent requests never queue behind it.
        """
        self._is_running = False
        self._context = None
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None

    async def send_request(self, payload: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
        """Serialize a request, dispatch it to the in-process SSR worker, and decode the response.

        Args:
            payload: Outbound IPC request dictionary.
            timeout: Maximum duration in seconds to wait for a response.

        Returns:
            Decoded response dictionary from the SSR worker.
        """
        self._request_id += 1
        req_id = payload.get("id", self._request_id)
        outbound = {**payload, "id": req_id}
        request_line = encode_json(outbound).decode("utf-8")

        async def _execute_locked() -> str:
            async with self._lock:
                if not self._is_running:
                    await self.start()
                if self._executor is None:
                    msg = "WASM SSR executor is not running."
                    raise IPCWorkerCrashError(msg)
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(self._executor, self._dispatch_sync, request_line, timeout)

        try:
            raw_response = await asyncio.wait_for(_execute_locked(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            self._reset_after_timeout()
            msg = f"WASM SSR request {req_id} timed out after {timeout}s"
            raise IPCTimeoutError(msg) from exc
        except IPCTimeoutError:
            self._reset_after_timeout()
            raise
        except IPCError:
            raise
        except Exception as exc:
            msg = f"WASM SSR execution failed: {exc}"
            raise IPCWorkerCrashError(msg) from exc

        try:
            decoded = decode_json(raw_response)
        except SerializationException as exc:
            msg = f"Failed to decode WASM SSR response JSON: {exc}"
            raise IPCError(msg) from exc

        if not isinstance(decoded, dict):
            msg = "Invalid IPC response format from WASM SSR worker."
            raise IPCError(msg)

        response_dict = cast("dict[str, Any]", decoded)
        if response_dict.get("error"):
            raise IPCError(str(response_dict["error"]))

        return response_dict


def _resolve_ssr_runtime_binary_name(config: ViteConfig | None) -> str:
    """Return the bare binary name used by the configured executor for SSR execution."""
    executor_type = config.runtime.executor if config is not None else "node"
    if executor_type == "bun":
        return "bun"
    if executor_type == "deno":
        return "deno"
    return "node"


def resolve_ssr_transport(
    config: ViteConfig | None = None, ssr_config: InertiaSSRConfig | None = None
) -> BaseIPCTransport:
    """Resolve the production SSR IPC transport according to runtime configuration and host capabilities.

    Resolution order:
        1. ``runtime.ssr_transport == "wasm"`` -> ``WasmIPCTransport``.
        2. ``runtime.ssr_transport == "stdio"`` -> ``StdioIPCTransport`` using ``resolve_ssr_command``.
        3. ``runtime.ssr_transport == "auto"`` (default):
           a. Explicit ``ssr_config.command`` -> ``StdioIPCTransport``.
           b. Co-located ``litestar-ssr-worker`` binary next to ``sys.executable`` -> ``StdioIPCTransport``.
           c. Configured JS runtime binary available on ``PATH`` or venv -> ``StdioIPCTransport``.
           d. ``is_wasm_available()`` is ``True`` -> ``WasmIPCTransport`` fallback.
           e. Default to ``StdioIPCTransport`` using ``resolve_ssr_command``.

    Args:
        config: Optional active ``ViteConfig`` instance.
        ssr_config: Optional resolved ``InertiaSSRConfig`` instance.

    Returns:
        Configured ``BaseIPCTransport`` instance for production SSR.
    """
    if ssr_config is None and config is not None and isinstance(config.inertia, InertiaConfig):
        ssr_config = config.inertia.ssr_config

    cwd = (ssr_config.cwd if ssr_config is not None else None) or (
        config.root_dir if config is not None else Path.cwd()
    )
    if config is not None:
        bundle_path = resolve_ssr_bundle_path(config.paths)
        mode = config.runtime.ssr_transport
    else:
        fallback_config = ViteConfig(paths=PathConfig(root=cwd))
        bundle_path = resolve_ssr_bundle_path(fallback_config.paths)
        mode = "auto"

    if mode == "wasm":
        return WasmIPCTransport(bundle_path=bundle_path)

    has_explicit_or_bundled_worker = bool(ssr_config is not None and ssr_config.command) or (
        find_bundled_ssr_worker() is not None
    )
    provisioning_mode = config.runtime.provisioning_mode if config is not None else "auto"
    if (
        mode == "auto"
        and not has_explicit_or_bundled_worker
        and JSExecutor.which(_resolve_ssr_runtime_binary_name(config), provisioning_mode) is None
        and is_wasm_available()
    ):
        return WasmIPCTransport(bundle_path=bundle_path)

    return StdioIPCTransport(command=resolve_ssr_command(config, ssr_config), cwd=cwd)

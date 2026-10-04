"""In-process WebAssembly / embedded QuickJS IPC transport for SSR and Fragments."""

import asyncio
import importlib
import sys
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

_QUICKJS_GLOBALS_SHIM = (
    "globalThis.process = globalThis.process || { env: { NODE_ENV: 'production' } };\n"
    "globalThis.console = globalThis.console || { log(){}, warn(){}, error(){} };\n"
)

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

    __slots__ = ("_bundle_path", "_context", "_cwd", "_engine", "_executor", "_is_running", "_lock", "_request_id")

    def __init__(
        self, bundle_path: Path, cwd: Path | None = None, *, engine: Callable[[str], str] | None = None
    ) -> None:
        """Initialize the in-process WASM/QuickJS SSR transport.

        Args:
            bundle_path: Path to the self-contained SSR JavaScript bundle.
            cwd: Working directory for resolving relative bundle paths.
            engine: Optional synchronous callable ``(line: str) -> str`` override for testing.
        """
        self._bundle_path = bundle_path
        self._cwd = cwd or bundle_path.parent
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
    def cwd(self) -> Path:
        """Return the configured working directory."""
        return self._cwd

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
            ctx.eval(bundle_source)
            has_dispatch = bool(ctx.eval("typeof globalThis.__litestar_ssr_dispatch__ === 'function'"))
        except Exception as exc:
            msg = f"Failed to evaluate SSR bundle at {self._bundle_path}: {exc}"
            raise IPCWorkerCrashError(msg) from exc

        if not has_dispatch:
            msg = f"SSR bundle at {self._bundle_path} did not register globalThis.__litestar_ssr_dispatch__"
            raise IPCWorkerCrashError(msg)

        ctx.eval(_QUICKJS_DISPATCH_WRAPPER)
        self._context = ctx

    def _dispatch_sync(self, request_line: str) -> str:
        """Dispatch a single NDJSON request line on the worker thread and drain Promise jobs."""
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

        direct = wasm_call(request_line)
        if isinstance(direct, str):
            return direct

        execute_job = getattr(ctx, "execute_pending_job", None)
        if callable(execute_job):
            while execute_job():
                pass

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

    async def send_request(self, payload: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
        """Serialize a request, dispatch it to the in-process SSR worker, and decode the response.

        Args:
            payload: Outbound IPC request dictionary.
            timeout: Maximum duration in seconds to wait for a response.

        Returns:
            Decoded response dictionary from the SSR worker.
        """
        if not self._is_running:
            await self.start()

        self._request_id += 1
        req_id = payload.get("id", self._request_id)
        outbound = {**payload, "id": req_id}
        request_line = encode_json(outbound).decode("utf-8")

        async def _execute_locked() -> str:
            async with self._lock:
                if self._executor is None:
                    msg = "WASM SSR executor is not running."
                    raise IPCWorkerCrashError(msg)
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(self._executor, self._dispatch_sync, request_line)

        try:
            raw_response = await asyncio.wait_for(_execute_locked(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            msg = f"WASM SSR request {req_id} timed out after {timeout}s"
            raise IPCTimeoutError(msg) from exc
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
        return WasmIPCTransport(bundle_path=bundle_path, cwd=cwd)

    has_explicit_or_bundled_worker = bool(ssr_config is not None and ssr_config.command) or (
        find_bundled_ssr_worker() is not None
    )
    if (
        mode == "auto"
        and not has_explicit_or_bundled_worker
        and JSExecutor.which(_resolve_ssr_runtime_binary_name(config)) is None
        and is_wasm_available()
    ):
        return WasmIPCTransport(bundle_path=bundle_path, cwd=cwd)

    return StdioIPCTransport(command=resolve_ssr_command(config, ssr_config), cwd=cwd)

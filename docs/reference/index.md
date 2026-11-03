# API & Tooling Reference

Complete reference documentation for **`litestar-vite`** (Python package), **`litestar-vite-plugin`** (TypeScript 18-subpath Vite 7+ package), the **`litestar assets` CLI**, and the **Cross-Language Wire Contracts**.

---

## Python API Reference

| Reference Page | Modules & Symbols Covered |
| --- | --- |
| [**Plugin & Configuration**](plugin-and-config.md) | `VitePlugin`, `ViteConfig`, `PathConfig`, `RuntimeConfig`, `TypeGenConfig`, `InertiaConfig`, `InertiaSSRConfig`, `InertiaTypeGenConfig`, `SPAConfig`, `DeployConfig`, `LoggingConfig`, `ExternalDevServer`, `PaginationContainer`, `detect_runtime`, `detect_runtime_marker` |
| [**Inertia.js (`litestar_vite.inertia`)**](inertia.md) | `InertiaPlugin`, `InertiaResponse`, `InertiaRedirect`, `InertiaExternalRedirect`, `InertiaBack`, `InertiaRequest`, `InertiaDetails`, `InertiaMiddleware`, `PrecognitionResponse`, `PageProps`, prop wrappers (`defer`, `once`, `optional`, `lazy`, `always`, `merge`, `scroll_props`, `only`, `except_`), and request state helpers (`share`, `flash`, `error`, `clear_history`, `precognition`) |
| [**Fragments & SSR IPC**](fragments-and-ipc.md) | `FragmentEngine`, `ComponentResponse`, `vite_fragment`, `render_fragment`, `BaseIPCTransport`, `StdioIPCTransport`, `WasmIPCTransport`, `TCPStreamIPCTransport`, `resolve_ssr_transport`, `is_wasm_available`, `SSRCircuitBreaker`, `CircuitState`, `IPCRequest`, `IPCResponse`, and IPC exceptions |
| [**Runtime, Assets & Exceptions**](runtime-and-assets.md) | `ViteAssetLoader`, `render_hmr_client`, `render_asset_tag`, `render_static_asset`, `render_routes`, `AppHandler`, `ViteProxyMiddleware`, `StaticPlacement`, `StaticServerConfig`, `StaticServerMount`, `StaticFilesConfig`, `JSExecutor` hierarchy, `resolve_ssr_command`, and `LitestarViteError` exceptions |
| [**Tooling, Codegen, Deploy & Doctor**](tooling-and-codegen.md) | `ViteDoctor`, `DoctorIssue`, `ViteDeployer`, `SyncPlan`, `SyncResult`, `FrameworkTemplate`, `TemplateContext`, `generate_project`, and `litestar_vite.codegen` (`export_integration_assets`, `generate_routes_json`, `generate_routes_ts`, `extract_inertia_pages`, `normalize_asyncapi_document`, `ChannelKeyAllocator`, `channel_key_base`, `extract_ws_server_url`, `write_if_changed`) |

---

## TypeScript Package Reference

All 18 public subpaths declared in `package.json["exports"]` are automatically documented from the compiled TypeScript declarations:

| Reference Page | Subpaths Covered |
| --- | --- |
| [**Main Vite Plugin & Config**](typescript/index.md) | `litestar-vite-plugin` (`.`), `./inertia`, `./virtual` |
| [**Runtime & Inertia Helpers**](typescript/helpers.md) | `./helpers`, `./inertia-helpers` |
| [**Framework Bindings & Meta-Frameworks**](typescript/frameworks.md) | `./react`, `./vue`, `./svelte`, `./astro`, `./sveltekit`, `./nuxt` |
| [**Server Fragments, Islands & SSR Runtimes**](typescript/fragments.md) | `./fragments`, `./fragments/client`, `./fragments/react`, `./fragments/vue`, `./fragments/svelte`, `./dev-ssr`, `./ssr-worker` |

---

## CLI, Wire Contracts & Contributing

- [**CLI (`litestar assets`)**](cli.md) — Auto-generated reference for all 9 `litestar assets` commands (`init`, `install`, `update`, `serve`, `build`, `deploy`, `generate-types`, `export-routes`, `doctor`, `status`).
- [**Bridge & Wire Contracts**](contracts.md) — Field-by-field JSON schemas for `.litestar.json`, `<bundle_dir>/hot`, NDJSON/HTTP SSR IPC (`IPCRequest` / `IPCResponse`), and Inertia.js `PageProps`.
- [**Contributing & Development Setup**](contributing.md) — Local polyglot workspace setup, verification gates, and architectural guardrails.

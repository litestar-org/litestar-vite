=========
Changelog
=========

Notable changes to this project are documented in this file.

Litestar Vite Changelog
^^^^^^^^^^^^^^^^^^^^^^^

0.26.1 - 2026-07-06
-------------------

- Fixed ``litestar assets build`` so ``.litestar.json`` is written before pre-build code generators and the JS typegen CLI read the Vite bridge.

0.26.0 - 2026-07-05
-------------------

Migration notes
~~~~~~~~~~~~~~~

- Inertia asset-version mismatches now follow the protocol more strictly: stale ``GET`` visits receive the ``409`` refresh response, while stale non-``GET`` submissions continue to their handlers. Review handlers that relied on non-``GET`` mismatch short-circuiting.
- Inertia infinite-scroll metadata is now emitted as ``scrollProps`` keyed by data prop name. Frontend code that read a single flat scroll config should read ``scrollProps.<propName>`` instead.
- Type generation now fails production builds by default when generation fails. Set ``TypeGenConfig(fail_on_error=False)`` or ``types.failOnError = false`` to keep warn-only build behavior.

- Fixed Inertia asset-version mismatch handling so only ``GET`` requests can return the protocol ``409`` refresh response; non-GET submissions now continue to their handlers instead of being downgraded and losing the request body. (#306)
- Fixed ``share()`` with Inertia redirects so top-level sync special props are materialized before session storage and async special props are skipped instead of crashing session serialization. (#306)
- Fixed request-scope Inertia shared props so they are still rendered on routes without session middleware.
- Fixed Inertia infinite-scroll ``scrollProps`` to emit a record keyed by data prop name, matching the official client protocol. (#306)
- Fixed explicit Inertia ``scroll_props=`` responses so metadata is keyed by the returned data prop when there is a single route prop.
- Fixed auto-wrapped Inertia responses so non-Inertia JSON handlers preserve Litestar's resolved ``201``/``204`` status codes while user-created ``InertiaResponse`` statuses still win. (#306)
- Fixed Precognition validation success handling for handlers without an explicit ``request`` parameter by using the middleware request context. (#306)
- Fixed Inertia SSR serialization so app, handler, and response type encoders are honored for custom page prop values. (#306)
- Fixed Inertia partial reloads so ``deferredProps`` metadata is omitted on partial responses while initial responses still advertise deferred props. (#306)
- Fixed Inertia partial reloads so plain dict route props honor ``X-Inertia-Partial-Data`` and ``X-Inertia-Partial-Except`` independently.
- Fixed ``litestar assets init`` so generated ``package.json`` files no longer emit duplicate dependency keys. (#302, #303)
- Fixed type generation so the JS plugin resolves local ``@hey-api/openapi-ts`` installs first, uses a pinned package-manager fallback when needed, fails production builds loudly by default, and lets ``TypeGenConfig(fail_on_error=False)`` or ``types.failOnError = false`` opt out. (#311, #314)
- Fixed Deno type-generation fallback execution when the providing npm package exposes a binary with a different name.
- Fixed type generation reliability for generated outputs by preserving queued dev regenerations, checking that expected output files exist before reusing caches, watching ``routes.json``, emitting ``static-props.ts`` from the shared CLI path, and handling semantic aliases and nested hey-api operation types. (#311, #314)
- Fixed Vite dev-server resilience by revalidating hotfile targets by mtime, recovering after missing or replaced hotfiles, tolerating additive/corrupt bridge config files, aligning TLS certificate env vars, and preserving static-files defaults when user overrides leave fields unset. (#312, #314)
- Fixed ``litestar assets init`` scaffold correctness for framework variants without dedicated directories, Tailwind CSS/PostCSS dependencies and entry inputs, current hey-api/TanStack/Vite template APIs, transactional writes, and non-interactive collision handling. (#313, #314)
- Updated npm publishing to use trusted publishing with provenance and no npm token. (#314)
- Fixed Vite dev-server lifecycle handling so unexpected exits are restarted with capped backoff and intentional shutdowns do not trigger restarts. (#317)
- Fixed Vite dev-server auto-restart so each recovered crash gets a fresh retry budget instead of exhausting the lifetime budget.
- Changed SPA/proxy route-prefix fallbacks so ``/docs`` is no longer reserved unless Litestar actually registers docs there or ``RuntimeConfig.extra_route_prefixes`` includes it. (#317)
- Added ``ViteConfig(enabled=...)`` and ``VITE_ENABLED`` so Vite routes and lifespans can be disabled in CLI, worker, and test contexts while keeping asset CLI commands available. (#301, #310)
- Added ``RuntimeConfig.extra_route_prefixes`` for deliberately reserving custom backend prefixes from SPA/proxy fallbacks. (#317)
- Fixed ``getCsrfToken()`` so SPA and HTMX helpers can fall back to the ``csrftoken`` or ``XSRF-TOKEN`` cookie when injected page-state sources are absent. (#299, #310)
- Hardened HTMX helper handling so dynamic ``href``, ``src``, and ``action`` attributes reject dangerous protocols and expression checks catch denied globals reconstructed through string concatenation. (#316)
- Simplified Vite integration internals by consolidating type-config resolution, hotfile handling, proxy helpers, Inertia prop wrappers, and typing-only helper paths without removing public exports. (#316)
- Reduced duplicate work in type generation, route metadata extraction, proxy header filtering, deploy diffing, bridge reads, placeholder probing, and Inertia response wrapping while preserving generated output paths and public behavior. (#315)
- Fixed SPA startup so async lifespan initialization uses the async handler path and custom Inertia component option keys are preserved when startup wrappers are installed. (#315)
- Fixed production SPA manifest resolution for Vite's default ``.vite/manifest.json`` path and recursive deploy change detection for nested bundle assets. (#315)
- Updated Python dependencies: ``typing-extensions`` 4.16.0, ``prek`` 0.4.8, ``slotscheck`` 0.20.1, and ``coverage`` 7.15.0. (#309)

0.25.0 - 2026-06-25
-------------------

- Fixed Vite 8.1 HMR compatibility by moving network overrides to ``server.ws.*`` (#292, #293).

0.24.1 - 2026-06-07
-------------------

- Fixed structured handler returns so Inertia bootstrap responses expose them as HTML props (#272, #277).

0.24.0 - 2026-06-03
-------------------

- Excluded the SPA handler's own routes from the Litestar route prefix list so SPA fallbacks no longer mask real backend routes (#264).
- Added Python 3.14 to the CI test matrix (#263).
- Fixed Inertia partial reloads so resolved keys are removed from ``deferredProps`` and non-requested properties are not included in the response (#265).
- Replaced Biome with Oxlint and Oxfmt for JavaScript linting and formatting (#232).
- Prepared the integration for Litestar 3 deprecations and tightened Inertia bootstrap behavior (#269).

0.23.4 - 2026-05-06
-------------------

- Fixed Inertia bootstrap responses to always use the HTML content type (#256).

0.23.3 - 2026-05-04
-------------------

- Normalized browser app URLs (#255).
- Honored RuntimeConfig.executor for local typegen binary on bun/deno (#253).

0.23.2 - 2026-05-04
-------------------

- Preserved resolved Vite hotfile targets (#252).

0.23.1 - 2026-05-03
-------------------

- Fixed the asset loader so it re-reads the hotfile on demand (#251).

0.23.0 - 2026-05-03
-------------------

- Fixed VitePlugin startup so it eagerly invokes ``InertiaPlugin.on_app_init`` (#249).
- Cleaned up dev proxy and config (#250).

0.22.2 - 2026-05-03
-------------------

- Fixed proxy requests so ``GET``, ``HEAD``, and ``OPTIONS`` requests do not send request bodies (#242, #246).
- Fixed Inertia async prop callbacks by pre-resolving ``optional()``, ``defer()``, ``lazy()``, and ``once()`` callbacks on the request event loop, avoiding asyncpg/aiosqlite/sqlspec cross-loop failures (#244, #245).
- Fixed Inertia page remounts during navigation and partial reloads by memoizing ``resolvePageComponent`` wrappers with a ``WeakMap`` (#245).
- Removed the internal ``BlockingPortal`` path from Inertia prop rendering; direct unresolved async prop rendering now raises ``RuntimeError`` because async callbacks are resolved during response dispatch (#245).
- Fixed dev-proxy and Inertia fallback regressions (#248).

0.22.1 - 2026-04-19
-------------------

- Fixed metadata extraction for Inertia deferred props before initial and partial response filtering (#236, #241).
- Updated the documentation build so ``llms.txt`` and ``llms-full.txt`` are published at the site root (#240, #241).
- Isolated TanStack Router generated assets into ``src/generated/`` in the examples and scaffolding templates (#241).
- Changed non-Inertia scaffold defaults to use ``src`` as ``resource_dir`` while keeping Inertia templates on ``resources`` (#241).
- Updated CLI and documentation wording to consistently use ``litestar assets`` and document ``--frontend-dir`` (#241).
- Added Node 24 to CI (#234).

0.22.0 - 2026-03-30
-------------------

- Updated LLM guidance text (#230).
- Added ``extra_commands`` to ``TypeGenConfig`` for frontend code-generation CLIs (#231).

0.21.1 - 2026-03-29
-------------------

- Fixed ``resolvePageComponent`` types for compatibility with the Inertia v3 ``ComponentResolver`` (#229).

0.21.0 - 2026-03-29
-------------------

- Fixed type-generation builds and enabled Inertia 3.0 support (#227).

0.20.0 - 2026-03-23
-------------------

- Added Vite 8 support (#217).
- Normalized resolved command binaries (#218).
- Hardened the bridge schema and added config validation (#219).
- Updated Angular packages to latest in examples (#220).

0.19.0 - 2026-03-09
-------------------

- Aligned stable inertia contract and bootstrap guidance (#209).

0.18.4 - 2026-03-05
-------------------

- Prevented proxy bypasses for dev CSS assets and hardened diagnostics (#208).

0.18.3 - 2026-03-03
-------------------

- Aligned proxy/static and inertia script payload handling (#205).
- Synced ``llms.txt`` and ``llms-full.txt`` to the v0.18.3 codebase (#206).

0.18.2 - 2026-02-23
-------------------

- Fixed CLI file-existence checks so they respect ``--frontend-dir`` (#190).
- Allowed numeric framework selection in assets init prompt (#197).
- Fixed CLI next-step output so it includes the ``--frontend-dir`` path (#191).
- Fixed the docs logo target and removed stale ``watch_patterns`` documentation (#199).
- Fixed module-prefixed enum type resolution and updated docs (#200).

0.18.1 - 2026-02-04
-------------------

- Fixed CLI initialization so it respects the configured ``--frontend-dir`` path (#186).
- Improved openapi-ts error handling and included ``LICENSE`` in the npm package (#187).

0.18.0 - 2026-01-29
-------------------

- Fixed proxy handling for ``node_modules`` paths and made SPA caching configurable (#184).

0.17.0 - 2026-01-19
-------------------

- Changed the restricted test port from 5061 to 5050 (#177).
- Added the static-props bridge and fixed the HTMX template (#178, #179).

0.16.4 - 2026-01-07
-------------------

- Updated path validation logic to reduce spurious warnings (#175).

0.16.3 - 2026-01-06
-------------------

- Removed outdated context files for Litestar, React, Svelte, Vue, Vite, and Testing (#174).

0.16.2 - 2026-01-05
-------------------

- Fixed PyPI publishing by building Python distributions into ``dist/py`` so JavaScript build output is not uploaded as a Python package (#173).

0.16.1 - 2026-01-05
-------------------

- Fixed source distributions by including ``package.json`` and ``package-lock.json`` for the build hook (#172).

0.16.0 - 2026-01-05
-------------------

- Cleaned up and updated console format (#171).

0.15.0 - 2025-12-22
-------------------

- Finalized the 0.15.0 overhaul after the prerelease series, including single-port Vite integration, framework-mode docs, Inertia protocol improvements, stronger type generation, route helpers, and Precognition support.
- This release is a migration point; users should review the updated docs before upgrading from 0.14.x.

0.15.0-rc.5 - 2025-12-21
------------------------

- Added ProxyHeadersMiddleware for secure reverse proxy support (#168).
- Added Precognition support (#169).

0.15.0-rc.4 - 2025-12-20
------------------------

- Fixed session helpers to return ``bool`` and added a query-parameter fallback for flash messages (#165).

0.15.0-rc.3 - 2025-12-19
------------------------

- Fixed page-prop type resolution and deployment configuration (#161).
- Fixed deterministic build output and write-on-change (#162).
- Split large modules into packages (#163).

0.15.0-rc.2 - 2025-12-16
------------------------

- Detected Inertia mode from ``hybrid`` in ``.litestar.json`` (#158).
- Restored route helpers for runtime navigation (#159).

0.15.0-rc.1 - 2025-12-15
------------------------

- Added auto-install during builds (#152).

0.15.0-beta.6 - 2025-12-13
--------------------------

- Cleaned up routing internals (#151).

0.15.0-beta.5 - 2025-12-11
--------------------------

- Cleaned up external handler (#148).
- Enhanced body parameter detection for route handlers (#149).

0.15.0-beta.4 - 2025-12-10
--------------------------

- Improved pagination support (#146).

0.15.0-beta.3 - 2025-12-09
--------------------------

- Updated CI to bypass checks for GIF generation (#143).
- Prevented vite proxy from shadowing litestar routes (#144).

0.15.0-beta.2 - 2025-12-09
--------------------------

- Fixed Litestar route handling (#138).
- Fixed the Vue Inertia favicon (#140).
- Added the litestar-fullstack reference link (#142).

0.15.0-beta.1 - 2025-12-08
--------------------------

- Added animated console gifs (#130).
- Improved Inertia configuration and integration behavior (#131).
- Fixed proxy handling (#132).

0.15.0-alpha.7 - 2025-12-07
---------------------------

- Hardened Inertia security and quality behavior (#127).

0.15.0-alpha.6 - 2025-12-06
---------------------------

- Enhanced type generation from OpenAPI schemas (#120).

0.15.0-alpha.5 - 2025-12-05
---------------------------

- Added end-to-end tests for examples (#119).

0.15.0-alpha.4 - 2025-12-01
---------------------------

- Removed Vite 5 support and fixed production-mode behavior (#118).

0.15.0-alpha.3 - 2025-12-01
---------------------------

- Implemented lazy initialization for ViteSPAHandler (#111).
- Cleaned up path info (#112).

0.15.0-alpha.2 - 2025-11-30
---------------------------

- Overhauled the documentation (#108).
- Updated the README (#109).
- Corrected index auto-detection and port proxying (#110).

0.15.0-alpha.1 - 2025-11-29
---------------------------

- **Breaking**: Added single-port Vite integration (#104).

0.14.0 - 2025-08-21
-------------------

- Corrected a README typo (#88).
- Added Vite 7 support and made Jinja2 optional (#93).

0.13.2 - 2025-05-05
-------------------

- Fixed ``initialize_loader`` errors in the loader asset plugin (#80, #78).
- Updated the example app to use Jinja templating (#79).
- Fixed plugin ``index.html`` detection (#86).

0.13.1 - 2025-03-27
-------------------

- **Breaking**: Dropped Python 3.8 support and added Python 3.13 tests (#70).
- Detected and served ``index.html`` automatically (#75).

0.13.0 - 2025-01-04
-------------------

- Allowed static file config options (#65).
- Corrected issues related to hatchling (#67).

0.12.1 - 2024-12-30
-------------------

- Updated ``lazy`` handling (#64).
- Allowed no template_config, enabling you to use litestar-vite with html frameworks other than Jinja2 (#63).

0.12.0 - 2024-12-23
-------------------

- Added experimental Inertia ``lazy()`` support for deferring prop rendering until a partial reload requests the data (#61).

0.11.1 - 2024-12-09
-------------------

- Used subprocess directly.

0.11.0 - 2024-12-09
-------------------

- Improved process management (#59).

0.10.0 - 2024-12-08
-------------------

- **Breaking**: Removed the custom ``JinjaTemplateEngine`` integration and switched to patching Litestar's built-in ``TemplateConfig`` instead (#58).
- Applications should configure Litestar templates through ``template_config=TemplateConfig(...)`` and keep ``VitePlugin`` focused on Vite assets.

0.9.0 - 2024-12-07
------------------

- Reformatted the ``Makefile`` (#56).
- Added SPA ``index.html`` auto-detection (#57).

0.8.3 - 2024-12-06
------------------

- Fixed remaining npm-package publishing issues after the 0.8.x build pipeline updates.

0.8.2 - 2024-12-06
------------------

- Fixed ``--root-path`` option behavior during CLI initialization (#48).

0.8.1 - 2024-12-01
------------------

- Fixed the generated wheel so the ``litestar_vite`` Python module is included.

0.8.0 - 2024-12-01
------------------

- Added 404 redirect option (#46).

0.7.1 - 2024-11-30
------------------

- Updated ``build_docs.py`` (#54).
- Updated release process (#55).

0.7.0 - 2024-11-30
------------------

- Synchronized the Python ``litestar-vite`` package and TypeScript ``vite-plugin`` package versions after earlier version drift.
- Updated the example app with JavaScript route helpers (#43).
- Added API documentation, introduced the Vite plugin package, and moved project tooling to ``uv`` (#53).

0.2.9 - 2024-08-04
------------------

- Updated exception handler (#42).

0.2.8 - 2024-07-30
------------------

- Fixed external redirect (#41).

0.2.7 - 2024-07-28
------------------

- Added ``ImproperConfig`` to exception handler (#40).

0.2.6 - 2024-07-28
------------------

- Fixed URL reconstruction with ``urlunparse``.

0.2.5 - 2024-07-28
------------------

- Used the referer scheme for redirects (#39).

0.2.4 - 2024-07-27
------------------

- Improved invalid-session error handling (#38).

0.2.3 - 2024-07-27
------------------

- Added automatic session props (#36).
- Improved error handling (#37).

0.2.2 - 2024-07-22
------------------

- Updated ``referer`` handling (#35).

0.2.1 - 2024-07-21
------------------

- Fixed flash handling so it only runs when a session exists (#34).

0.2.0 - 2024-07-21
------------------

- Improved integration with the ``flash`` plugin (#21).
- Fixed Python 3.8 compatibility by avoiding ``removesuffix`` (#28).
- Added the base Inertia.js integration (#5).
- Enhanced Inertia.js support (#33).

0.1.22 - 2024-03-23
-------------------

- Fixed template initialization (#19).

0.1.21 - 2024-03-20
-------------------

- Removed ``cli`` from the required ``litestar`` optional features (#18).

0.1.20 - 2024-03-17
-------------------

- Fixed serving ``public_dir`` when it exists (#17).

0.1.19 - 2024-02-20
-------------------

- Replaced deprecated static-file integration (#15).

0.1.18 - 2024-02-04
-------------------

- Set the engine instance during configuration and adjusted the default manifest path (#14).

0.1.17 - 2024-01-02
-------------------

- Added automatic Litestar static-file configuration for Vite assets.

0.1.16 - 2023-12-30
-------------------

- Improved CLI console output, simplified Jinja templates, and added environment-variable configuration support.

0.1.15 - 2023-12-19
-------------------

- Fixed websocket-client rendering when dev mode is disabled.

0.1.14 - 2023-12-19
-------------------

- Fixed HMR rendering so it follows dev-mode status and HMR configuration.

0.1.13 - 2023-12-19
-------------------

- Fixed ``hot_file`` location loading when ``DEV_MODE`` is enabled.

0.1.12 - 2023-12-19
-------------------

- Added the ``set_environment`` call to server lifespan handling.

0.1.11 - 2023-12-19
-------------------

- Fixed startup before frontend assets have been built.

0.1.10 - 2023-12-17
-------------------

- Cleaned up templates and added default entry points (#13).

0.1.9 - 2023-12-13
------------------

- Removed stale ``asset_path`` references (#12).

0.1.8 - 2023-12-13
------------------

- Removed ``asset_dir`` and allowed paths to be passed as strings (#11).

0.1.7 - 2023-12-11
------------------

- Added ``build --watch`` option and updated ``README`` (#10).

0.1.6 - 2023-12-10
------------------

- Updated default manifest location (#9).

0.1.5 - 2023-12-10
------------------

- Optimized imports (#8).

0.1.4 - 2023-12-10
------------------

- Added project templating and the JavaScript plugin (#4).
- Added additional Vite install templates (#6).

0.1.3 - 2023-10-08
------------------

- Added ``py.typed`` to the package (#3).

0.1.2 - 2023-10-05
------------------

- Corrected a typo (#2).

0.1.1 - 2023-10-05
------------------

- Corrected imports (#1).

0.1.0 - 2023-10-04
------------------

- Initial release of the Litestar Vite plugin.

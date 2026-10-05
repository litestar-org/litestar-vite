==================================================
Single-File Executables (`litestar assets bundle`)
==================================================

``litestar assets bundle`` compiles a Litestar application, its built Vite assets,
an embedded CPython runtime, and (optionally) a compiled SSR worker into one
self-contained executable using `PyApp <https://github.com/ofek/pyapp>`_ and
`python-build-standalone <https://github.com/astral-sh/python-build-standalone>`_.
The resulting binary runs on hosts without Python or a JavaScript runtime installed.

Prerequisites
-------------

- Rust toolchain (``cargo``) for compiling the PyApp launcher. ``--stage-only``
  produces the relocatable distribution without Cargo.
- ``uv`` for building the project wheel and staging dependencies.
- ``curl`` and ``git`` on ``PATH`` (distribution download and PyApp checkout).
- Optional: ``bun`` or ``deno`` when ``compile_ssr_worker`` is set; ``cargo-zigbuild``
  and ``zig`` when ``use_zigbuild`` is enabled for cross-compilation.

Run ``litestar assets doctor`` to confirm the toolchain; it reports missing
``cargo``, ``zig``, SSR compilers, and entrypoints whenever bundling is configured.

Configuration
-------------

Bundling is configured once in ``pyproject.toml`` under ``[tool.litestar.bundle]``.
``binary_name`` defaults to ``[project].name`` and ``project_version`` to
``[project].version``:

.. code-block:: toml

    [project]
    name = "acme-portal"
    version = "1.4.0"

    [project.scripts]
    acme-portal = "acme_portal.cli:run"

    [tool.litestar.bundle]
    exec_spec = "acme_portal.cli:run"
    python_version = "3.12"
    pbs_release = "20241016"
    install_root = "~/.acme-portal/runtime"
    compile_ssr_worker = "bun"
    strip_dist = true
    strip_symbols = true
    static_compression_libs = true
    output_dir = "dist/bundle"

Every key maps to a :class:`~litestar_vite.config.BundleConfig` attribute. The most
relevant options:

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Key
     - Purpose
   * - ``exec_module`` / ``exec_spec``
     - Startup entrypoint passed to PyApp as ``PYAPP_EXEC_MODULE`` or
       ``PYAPP_EXEC_SPEC`` (mutually exclusive). Defaults to the project name as a module.
   * - ``python_version`` / ``pbs_release``
     - CPython ``major.minor`` and ``python-build-standalone`` release used to derive
       the distribution URL. Pairs outside the built-in table require ``pbs_urls``.
   * - ``pbs_urls`` / ``platform_map``
     - Per-target-triple overrides for the distribution archive (``https://`` only) and
       the pip platform tag used by ``uv pip install --python-platform``.
   * - ``target_arch``
     - Default Rust target triple; ``--target`` overrides it per invocation.
   * - ``install_root``
     - Base directory where the launcher extracts the runtime at first start. PyApp still
       appends ``<project_name>/<distribution_id>/<project_version>`` so upgrades never reuse
       a stale runtime, and ``PYAPP_INSTALL_DIR_<PROJECT_NAME>`` set at runtime still wins.
       Supports ``~/`` paths.
   * - ``full_isolation`` / ``pass_location`` / ``skip_install``
     - PyApp runtime flags. ``full_isolation=true`` is required for the bundled SSR
       worker to be discovered next to the interpreter.
   * - ``compile_ssr_worker`` / ``ssr_bytecode``
     - ``"bun"`` or ``"deno"`` compiles ``ssr.js`` into ``litestar-ssr-worker`` inside the
       staged distribution; ``"none"`` (default) relies on the WASM transport or a host runtime.
   * - ``strip_dist`` / ``strip_symbols`` / ``static_compression_libs``
     - Remove stdlib test suites, ``__pycache__``, headers and static libs; strip the
       launcher binary; enable the ``bzip2`` crate ``static`` feature. PyApp ``v0.28+``
       already uses a pure-Rust ``bzip2`` backend, so the last flag only matters for
       older ``pyapp_version`` pins that link the C library.
   * - ``use_zigbuild`` / ``glibc_version``
     - Cross-compile with ``cargo zigbuild`` targeting a glibc floor (default ``2.17``).
   * - ``pyapp_version``
     - PyApp git tag cloned when ``--pyapp-source`` is not supplied (default ``v0.29.0``).
   * - ``extra_wheels`` / ``extra_pip_args``
     - Additional wheels and ``uv pip install`` arguments for the staged ``site-packages``.

``ViteConfig(bundle=...)`` accepts ``True`` (load the table above), ``False`` (default;
``pyproject.toml`` is not read at application startup), or an explicit
:class:`~litestar_vite.config.BundleConfig`. The CLI and doctor read the table
directly, so most applications leave ``bundle`` unset.

Building
--------

.. code-block:: console

    $ litestar assets bundle
    $ litestar assets bundle --target aarch64-unknown-linux-gnu --zigbuild
    $ litestar assets bundle --compile-ssr deno --output dist/acme-portal
    $ litestar assets bundle --stage-only

The command performs these steps:

1. Runs the Vite production build unless ``--no-build`` is passed.
2. Builds the project wheel with ``uv build --wheel``.
3. Downloads (or reuses) the ``install_only_stripped`` distribution for the target,
   extracts it with path-traversal and symlink validation, and installs the wheel plus
   dependencies into its ``site-packages`` using ``uv pip install --target``.
4. Optionally compiles ``ssr.js`` into ``python/bin/litestar-ssr-worker``
   (``python/litestar-ssr-worker.exe`` on Windows).
5. Strips bytecode caches, stdlib tests, headers, and static libraries, then repacks
   ``python-dist.tar.gz`` under ``output_dir``. ``--stage-only`` stops here (``--output`` is ignored).
6. Clones PyApp at ``pyapp_version`` (or copies ``--pyapp-source``), patches
   ``install_root`` and static compression into the Rust sources, and runs
   ``cargo build --release --target <triple>`` with ``PYAPP_*`` environment variables.
7. Copies the launcher to ``output_dir/<binary_name>``.

SSR inside the binary
---------------------

Production SSR bundles are built with ``ssr.noExternal: true`` so ``ssr.js`` has no
``node_modules`` dependency. At runtime :func:`~litestar_vite.ipc.resolve_ssr_transport`
picks the first available option:

1. An explicit ``InertiaSSRConfig(command=...)``.
2. A compiled ``litestar-ssr-worker`` next to ``sys.executable`` (requires
   ``compile_ssr_worker`` and ``full_isolation``).
3. The configured JavaScript runtime (``node``, ``bun``, ``deno``) from the virtual
   environment or ``PATH``.
4. The in-process :class:`~litestar_vite.ipc.WasmIPCTransport` when the
   ``litestar-vite[wasm]`` extra is installed (experimental; no host runtime needed).

Set ``RuntimeConfig(ssr_transport="wasm")`` or ``"stdio"`` to force a transport.

Programmatic API
----------------

:class:`~litestar_vite.bundler.PyAppBundler` exposes each phase
(``build_project_wheel``, ``stage_distribution``, ``prepare_pyapp_source``,
``compile_binary``) and accepts a ``runner`` callable so CI pipelines or tests can
intercept subprocess execution. See :doc:`/reference/bundler`.

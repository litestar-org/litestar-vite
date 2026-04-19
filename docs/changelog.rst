=========
Changelog
=========

All commits to this project will be documented in this file.

Litestar Vite Changelog
^^^^^^^^^^^^^^^^^^^^^^^

Unreleased
----------

- Fixed metadata loss for Inertia deferred props (#236). Metadata is now correctly extracted before props are filtered for initial/partial responses.
- Updated documentation build to include ``llms.txt`` and ``llms-full.txt`` at the site root for better LLM discovery.
- Default ``resource_dir`` set to ``src`` for non-Inertia templates; Inertia stays on ``resources/``.
- CLI/docs now reference `litestar assets` consistently and document `--frontend-dir`.

---
description: Validate Litestar-Vite asset integration and run CLI diagnostics
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Asset Integration Check

Validating Litestar-Vite assets workflow for: **$ARGUMENTS**

## Phase 1: CLI Diagnostics

```bash
litestar assets status
litestar assets doctor
```

## Phase 2: Bridge File and Config Sanity

- Verify `.litestar.json` exists after startup
- Check `vite.config.ts` for minimal overrides
- Confirm `ViteConfig.paths` and `RuntimeConfig` align with project layout

Suggested checks:

```
Grep(pattern="ViteConfig\(|TypeGenConfig\(|InertiaConfig\(", path="src/py")
Grep(pattern="litestarVitePlugin", path="src")
```

## Phase 3: Mode and Proxy Validation

Confirm:
- `ViteConfig.mode` matches framework intent (spa, template, htmx, hybrid, framework, external)
- `RuntimeConfig.proxy_mode` matches dev strategy (vite, proxy, direct, None)

## Phase 4: Report

Summarize:
- CLI diagnostics results
- Any config mismatches
- Recommended fixes with file paths

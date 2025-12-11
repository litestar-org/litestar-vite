# Tasks: Python Code Cleanup for Beta Release

## Phase 1: Planning ✓
- [x] Create PRD
- [x] Identify affected files
- [x] Document all nested imports
- [x] Document comments to remove
- [x] Identify defensive patterns to review

## Phase 1.5: Breaking Changes & Enhancements

### Rename ViteSPAHandler → AppHandler
- [ ] Rename `spa.py` → `handler.py`
- [ ] Rename class `ViteSPAHandler` → `AppHandler`
- [ ] Update `__init__.py` exports
- [ ] Update imports in `plugin.py`
- [ ] Update any other internal imports

### Add Custom Guards Support
- [ ] Add `guards: Sequence[Guard] | None = None` to `ViteConfig`
- [ ] Pass guards to `AppHandler` route registration
- [ ] Update docstrings with example usage

### Config Consolidation (InertiaConfig/SPAConfig)
- [ ] Remove `InertiaConfig.app_selector` - use `SPAConfig.app_selector` instead
- [ ] Remove `InertiaConfig.spa_mode` - determined by `ViteConfig.mode`
- [ ] Update `_sync_inertia_spa_mode` to read from `spa.app_selector`
- [ ] Auto-set `spa.inject_csrf=True` when `inertia` is configured
- [ ] Update `InertiaResponse` to use `spa.app_selector`
- [ ] Update docstrings and examples

### Validate
- [ ] Run `make lint && make test`

## Phase 2: cli.py Cleanup (High Priority)
- [ ] Move `LoggingConfig` import to top-level (line 55)
- [ ] Remove duplicate `console` imports (lines 96, 262, 528, 632, 668, etc.)
- [ ] Move `msgspec` import to top-level (line 217)
- [ ] Move `InertiaConfig, TypeGenConfig` imports to top-level (line 219)
- [ ] Move `sys` import to top-level (line 260)
- [ ] Move `Prompt, Confirm` imports to top-level
- [ ] Move `ViteDoctor, VitePlugin` imports to top-level
- [ ] Move scaffolding imports to top-level
- [ ] Move `ViteExecutionError, set_environment` imports to top-level
- [ ] Move `httpx` import - KEEP NESTED (optional dependency)
- [ ] Remove redundant `# Reset executor` comments (lines 65, 75)
- [ ] Consolidate all Path imports
- [ ] Run `make lint` on cli.py
- [ ] Run `make test` to verify no regressions

## Phase 3: executor.py Cleanup (Medium Priority)
- [ ] Move `find_spec` import to top-level (line 225)
- [ ] Remove duplicate comment block (lines 258-267)
- [ ] Convert remaining subprocess comments to docstring if valuable
- [ ] Keep stdin comment (line 148) - important behavior note
- [ ] Run `make lint` on executor.py
- [ ] Run `make test` to verify no regressions

## Phase 4: helpers.py Cleanup (Medium Priority)
- [ ] Move first `ScrollPropsConfig` import to top-level (line 406)
- [ ] Remove duplicate `ScrollPropsConfig` import (line 988) - use single top-level import
- [ ] Run `make lint` on helpers.py
- [ ] Run `make test` to verify no regressions

## Phase 5: Minor Cleanups (Low Priority)
- [ ] doctor.py: Review `_check_plugin_spread` method - currently disabled
- [ ] deploy.py: Review section divider comments (keep for navigation)
- [ ] Run `make lint` on modified files
- [ ] Run `make test` to verify no regressions

## Phase 6: Final Validation
- [ ] Run full `make lint`
- [ ] Run full `make test`
- [ ] Run `make type-check`
- [ ] Verify no public API changes (imports/exports unchanged)
- [ ] Run a few examples to verify runtime behavior

## Phase 7: Quality Gate
- [ ] All tests pass
- [ ] Linting clean
- [ ] No breaking changes confirmed
- [ ] Archive workspace

---

## Import Consolidation Reference

### cli.py - Imports to Add at Top Level

```python
# Standard library
import sys

# Third-party
import httpx  # KEEP NESTED - optional dependency
import msgspec
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

# Litestar imports (some already present)
# from litestar.cli._utils import console  # Already present

# Local imports
from litestar_vite.config import InertiaConfig, LoggingConfig, TypeGenConfig
from litestar_vite.doctor import ViteDoctor
from litestar_vite.exceptions import ViteExecutionError
from litestar_vite.plugin import VitePlugin, set_environment
from litestar_vite.scaffolding import TemplateContext, generate_project, get_available_templates
from litestar_vite.scaffolding.templates import FrameworkType, get_template
```

### executor.py - Imports to Add at Top Level

```python
from importlib.util import find_spec
```

### helpers.py - Imports to Add at Top Level

```python
from litestar_vite.inertia.types import ScrollPropsConfig
```

---

## Files Summary

| File | Changes | Priority |
|------|---------|----------|
| cli.py | ~25 import moves, ~2 comment removals | High |
| executor.py | 1 import move, 1 comment block removal | Medium |
| helpers.py | 2 import consolidations | Medium |
| doctor.py | Review disabled code | Low |
| deploy.py | No changes needed | N/A |

---

## Estimated Effort

- cli.py: 30-45 minutes (most work)
- executor.py: 10-15 minutes
- helpers.py: 5-10 minutes
- doctor.py: 5 minutes
- Validation: 15-20 minutes

**Total: ~1-1.5 hours**

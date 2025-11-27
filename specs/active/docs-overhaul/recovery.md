# Recovery: Documentation Overhaul

**Workspace**: `specs/active/docs-overhaul/`
**Last Updated**: 2025-11-27

---

## Quick Context

This workspace contains the PRD and implementation plan for overhauling the litestar-vite documentation to align with the main Litestar project's documentation standards and add dynamic animated demonstrations.

## Current Status

**Phase**: PRD Complete, Ready for Implementation

## Key Files

| File | Purpose |
|------|---------|
| `prd.md` | Full Product Requirements Document with research findings |
| `tasks.md` | Implementation checklist with all tasks |
| `recovery.md` | This file - session resume instructions |

## Research Summary

### What We Learned

1. **Litestar Main Docs** use:
   - `litestar_sphinx_theme` (v3) with full configuration
   - 15+ Sphinx extensions including mermaid, paramlinks, togglebutton
   - Rich landing page with logo, badges, 6 feature cards, sponsor section
   - Multi-version support with `versioning.js`
   - GitHub Pages deployment via `JamesIves/github-pages-deploy-action@v4`

2. **litestar-vite Current State**:
   - Uses same theme but options are commented out (`docs/conf.py:169-213`)
   - Minimal landing page with TODO placeholder
   - Missing logos, favicons, visual assets
   - No demo GIFs or visual demonstrations

3. **GIF Generation Recommendation**: Charmbracelet VHS
   - Write terminal recordings as declarative `.tape` files
   - GitHub Action available: `charmbracelet/vhs-action@v2`
   - Deterministic, reproducible builds
   - Multiple output formats (GIF, MP4, WebM)

## Key Decisions Made

1. **Theme**: Keep `litestar_sphinx_theme`, enable all options
2. **GIF Tool**: Use VHS with GitHub Action
3. **Landing Page**: Redesign with sphinx-design cards and grids
4. **Demos**: Create at least 2 demo GIFs (scaffolding, HMR)

## Decisions Made

1. **Multi-version docs**: No - single version only for now
2. **Sponsor section**: No - not needed
3. **Tutorials**: Yes - create 5 dedicated tutorials:
   - Getting Started with Vite + Litestar
   - Building a React SPA with Inertia.js
   - Vue.js Integration
   - Project Scaffolding
   - Advanced Configuration

## Resume Instructions

### To Continue Implementation

1. Read `prd.md` for full context and technical specification
2. Follow `tasks.md` checklist in order (Phase 1 -> Phase 2 -> etc.)
3. Start with Phase 1: Theme Configuration Enhancement

### Key Files to Modify

- `docs/conf.py` - Theme options, extensions
- `docs/index.rst` - Landing page redesign
- `pyproject.toml` - Add new docs dependencies
- `.github/workflows/docs.yml` - Add GIF generation job
- `Makefile` - Add `docs-demos` target

### Commands

```bash
# Install dependencies
uv sync --all-extras --dev

# Build docs locally
make docs

# Serve docs locally (port 8002)
make docs-serve

# Check links
make docs-linkcheck

# Generate demos (requires vhs installed)
make docs-demos  # To be added
```

## References

- PRD: `specs/active/docs-overhaul/prd.md`
- Litestar main docs: https://github.com/litestar-org/litestar/tree/main/docs
- VHS: https://github.com/charmbracelet/vhs
- VHS Action: https://github.com/charmbracelet/vhs-action
- sphinx-design: https://sphinx-design.readthedocs.io/

# Research Plan: Documentation Overhaul

**Workspace**: `specs/active/docs-overhaul/`
**Status**: Completed

---

## Research Objectives

1. Analyze Litestar main project documentation setup
2. Compare with current litestar-vite documentation
3. Research animated GIF generation options for documentation
4. Identify best practices for Sphinx documentation

---

## Research Tasks

### Task 1: Litestar Main Docs Analysis

**Status**: Complete

**Sources Analyzed**:
- `github.com/litestar-org/litestar/docs/conf.py`
- `github.com/litestar-org/litestar/docs/index.rst`
- `github.com/litestar-org/litestar/.github/workflows/docs.yml`
- `github.com/litestar-org/litestar/pyproject.toml`

**Findings**:
- Uses `litestar_sphinx_theme` with full configuration
- 15+ Sphinx extensions
- Rich landing page with visual elements
- Multi-version documentation support
- GitHub Pages deployment

### Task 2: litestar-vite Docs Analysis

**Status**: Complete

**Files Analyzed**:
- `/home/cody/code/litestar/litestar-vite/docs/conf.py`
- `/home/cody/code/litestar/litestar-vite/docs/index.rst`
- `/home/cody/code/litestar/litestar-vite/.github/workflows/docs.yml`

**Findings**:
- Theme options are commented out (lines 169-213)
- Missing extensions: mermaid, paramlinks, togglebutton
- Basic landing page without visual elements
- No demo GIFs
- GitHub Pages deployment is working

### Task 3: GIF Generation Research

**Status**: Complete

**Tools Evaluated**:

| Tool | Pros | Cons | Recommendation |
|------|------|------|----------------|
| **VHS** | Declarative, GH Action, deterministic | Go-based, requires deps | **Recommended** |
| **asciinema** | Mature, SVG output | Requires JS player | Alternative |
| **termsvg** | Direct SVG | Early stage | Not recommended |

**Decision**: Use Charmbracelet VHS with vhs-action

---

## Key Research Outputs

1. **PRD**: `specs/active/docs-overhaul/prd.md`
2. **Tasks**: `specs/active/docs-overhaul/tasks.md`
3. **Recovery**: `specs/active/docs-overhaul/recovery.md`

---

## External Resources

### Documentation
- [Litestar Docs](https://docs.litestar.dev/)
- [sphinx-design](https://sphinx-design.readthedocs.io/)
- [sphinxcontrib-mermaid](https://sphinxcontrib-mermaid-demo.readthedocs.io/)

### Tools
- [Charmbracelet VHS](https://github.com/charmbracelet/vhs)
- [VHS GitHub Action](https://github.com/charmbracelet/vhs-action)
- [asciinema](https://asciinema.org/)

### Theme
- [litestar-sphinx-theme](https://github.com/litestar-org/litestar-sphinx-theme)

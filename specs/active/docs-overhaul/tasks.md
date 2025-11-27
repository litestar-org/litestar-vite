# Tasks: Documentation Overhaul

**Workspace**: `specs/active/docs-overhaul/`
**PRD**: `prd.md`
**Status**: Not Started

---

## Phase 1: Theme Configuration Enhancement

### 1.1 Enable Theme Options
- [ ] Uncomment `html_theme_options` in `docs/conf.py`
- [ ] Configure `logo_target`, `github_url`, `github_repo_name`
- [ ] Configure `nav_links` with Home, Docs, Code links
- [ ] Configure `light_css_variables` for light theme
- [ ] Configure `dark_css_variables` for dark theme
- [ ] Test theme locally with `make docs-serve`

### 1.2 Add Missing Extensions
- [ ] Add `sphinxcontrib-mermaid>=0.9.2` to `pyproject.toml` docs dependencies
- [ ] Add `sphinx-paramlinks>=0.6.0` to `pyproject.toml` docs dependencies
- [ ] Add `sphinx-togglebutton>=0.3.2` to `pyproject.toml` docs dependencies
- [ ] Add extensions to `docs/conf.py` extensions list
- [ ] Configure mermaid options if needed
- [ ] Run `uv sync --all-extras --dev` to install new dependencies
- [ ] Test extensions work with `make docs`

### 1.3 Add Static Assets
- [ ] Create/obtain `favicon.png` (16x16, 32x32)
- [ ] Create/obtain `favicon.svg` (scalable)
- [ ] Create/obtain `logo-dark.png` (for dark theme)
- [ ] Create/obtain `logo-light.png` (for light theme)
- [ ] Create/obtain `logo.svg` (main logo, ~400x400)
- [ ] Add assets to `docs/_static/`
- [ ] Update `html_favicon` in `docs/conf.py`
- [ ] Update `html_logo` in `docs/conf.py` (if applicable)
- [ ] Enhance `docs/_static/style.css` as needed

---

## Phase 2: Landing Page Redesign

### 2.1 Page Structure
- [ ] Add logo image at top of `docs/index.rst`
- [ ] Add status badges (GitHub stars, PyPI version, coverage, downloads)
- [ ] Update project description paragraph
- [ ] Add 4 CTA buttons (Getting Started, Usage, API Reference, Examples)

### 2.2 Feature Grid
- [ ] Create 6-card grid using `sphinx-design`
- [ ] Card 1: Getting Started - link to quickstart guide
- [ ] Card 2: Inertia.js - link to inertia docs
- [ ] Card 3: CLI Reference - link to CLI docs
- [ ] Card 4: Changelog - link to changelog
- [ ] Card 5: GitHub Issues - link to issue tracker
- [ ] Card 6: Contributing - link to contribution guide

### 2.3 Demo Section
- [ ] Create "See it in Action" section header
- [ ] Add tab-set for different demos
- [ ] Tab 1: Project Scaffolding demo GIF
- [ ] Tab 2: Hot Module Replacement demo GIF
- [ ] Tab 3: Production Build demo GIF (optional)
- [ ] Add placeholder images for initial development

### 2.4 Installation Section
- [ ] Keep existing tab-set for pip/uv/pdm/poetry
- [ ] Add npm installation for JS library
- [ ] Add quick start code example

### 2.5 Additional Sections
- [ ] Add "Why Litestar Vite?" section with benefits
- [ ] Add architecture diagram using mermaid

---

## Phase 3: Dynamic GIF Generation

### 3.1 VHS Tape Files
- [ ] Create `docs/_tapes/` directory
- [ ] Create `docs/_static/demos/` directory
- [ ] Create `.gitkeep` in `docs/_static/demos/`
- [ ] Write `scaffolding.tape` - demonstrates `litestar assets init`
- [ ] Write `hmr.tape` - demonstrates HMR workflow
- [ ] Write `build.tape` - demonstrates production build (optional)
- [ ] Test tape files locally with `vhs <file>.tape`

### 3.2 GitHub Workflow Integration
- [ ] Create separate job `generate-demos` in `docs.yml`
- [ ] Add `charmbracelet/vhs-action@v2` step
- [ ] Configure artifact upload for generated GIFs
- [ ] Add artifact download to build job
- [ ] Add path filters for efficient triggering
- [ ] Test workflow in a feature branch

### 3.3 Local Development Support
- [ ] Add `docs-demos` target to Makefile
- [ ] Add dependency check for vhs CLI
- [ ] Document local VHS installation in CONTRIBUTING.md
- [ ] Add fallback behavior when VHS not available

### 3.4 Caching & Optimization
- [ ] Configure GIF caching in CI
- [ ] Optimize GIF dimensions (900x500 max)
- [ ] Consider WebM fallback for browsers that support it
- [ ] Add conditional execution (only when tapes change)

---

## Phase 4: Polish & Testing

### 4.1 Content Review
- [ ] Review all existing documentation pages
- [ ] Update outdated content
- [ ] Fill in TODO placeholders in usage docs
- [ ] Ensure consistent formatting

### 4.2 Link Checking
- [ ] Run `make docs-linkcheck`
- [ ] Fix all broken internal links
- [ ] Fix all broken external links
- [ ] Add new intersphinx mappings if needed

### 4.3 Visual Testing
- [ ] Test docs in Chrome
- [ ] Test docs in Firefox
- [ ] Test docs in Safari
- [ ] Test dark mode appearance
- [ ] Test light mode appearance
- [ ] Test mobile responsiveness

### 4.4 Performance
- [ ] Check page load times
- [ ] Optimize image sizes if needed
- [ ] Verify GIF file sizes are reasonable (<2MB each)

---

## Phase 5: Tutorials

### 5.1 Tutorial Structure
- [ ] Create `docs/tutorials/` directory
- [ ] Create `docs/tutorials/index.rst` with tutorial overview
- [ ] Add tutorials toctree to main index.rst

### 5.2 Tutorial 1: Getting Started
- [ ] Create `docs/tutorials/getting-started.rst`
- [ ] Cover basic Vite + Litestar setup from scratch
- [ ] Include VitePlugin configuration
- [ ] Show dev server with HMR
- [ ] Show production build process
- [ ] Add code examples and expected outputs

### 5.3 Tutorial 2: React SPA with Inertia.js
- [ ] Create `docs/tutorials/inertia-react.rst`
- [ ] Cover Inertia setup with React
- [ ] Show page and layout creation
- [ ] Demonstrate navigation patterns
- [ ] Show server-client data sharing
- [ ] Include complete working example

### 5.4 Tutorial 3: Vue.js Integration
- [ ] Create `docs/tutorials/vue-integration.rst`
- [ ] Cover Vue 3 setup with Vite
- [ ] Show component-based architecture
- [ ] Include state management patterns
- [ ] Provide complete example

### 5.5 Tutorial 4: Project Scaffolding
- [ ] Create `docs/tutorials/scaffolding.rst`
- [ ] Document `litestar assets init` command
- [ ] Cover all template options (React, Vue, Svelte, HTMX)
- [ ] Show customization options
- [ ] This tutorial pairs well with scaffolding demo GIF

### 5.6 Tutorial 5: Advanced Configuration
- [ ] Create `docs/tutorials/advanced-config.rst`
- [ ] Cover custom Vite configurations
- [ ] Document asset bundling strategies
- [ ] Show environment-specific settings
- [ ] Include troubleshooting tips

---

## Phase 6: Deployment & Verification

### 6.1 Pre-deployment
- [ ] Merge feature branch to main
- [ ] Verify CI workflow completes successfully
- [ ] Check build artifacts

### 6.2 Post-deployment
- [ ] Verify docs are accessible at GitHub Pages URL
- [ ] Check all pages render correctly
- [ ] Verify GIFs display and animate
- [ ] Test navigation works correctly

### 6.3 Documentation
- [ ] Update README.md with docs link
- [ ] Update CONTRIBUTING.md with docs build instructions
- [ ] Document VHS tape file format in contributing guide

---

## Dependencies Checklist

### Python Packages
- [ ] `sphinxcontrib-mermaid>=0.9.2`
- [ ] `sphinx-paramlinks>=0.6.0`
- [ ] `sphinx-togglebutton>=0.3.2`

### CI/CD
- [ ] `charmbracelet/vhs-action@v2`
- [ ] Verify `actions/upload-artifact@v4` is up to date
- [ ] Verify `actions/download-artifact@v4` is up to date

### Local Tools (Optional)
- [ ] VHS CLI (`brew install vhs` or from releases)
- [ ] ffmpeg (required by VHS)
- [ ] ttyd (required by VHS)

---

## Acceptance Criteria

- [ ] Landing page has logo, badges, and feature cards
- [ ] Theme matches Litestar main docs styling
- [ ] At least 2 demo GIFs are displayed on landing page
- [ ] GIFs are generated automatically in CI
- [ ] All links pass linkcheck
- [ ] Docs build completes in under 5 minutes
- [ ] Dark mode and light mode both look professional
- [ ] At least 5 tutorials are complete and accessible
- [ ] Tutorials section linked from landing page

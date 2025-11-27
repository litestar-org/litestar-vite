# PRD: Documentation Overhaul and Alignment with Litestar Docs

**Version**: 1.0
**Created**: 2025-11-27
**Status**: Draft
**Slug**: docs-overhaul

---

## Executive Summary

This PRD outlines a comprehensive documentation overhaul for litestar-vite to align with the main Litestar project's documentation standards and enhance the landing page with dynamic animated demonstrations. The goal is to create a seamless, professional documentation experience that matches the quality of the Litestar ecosystem.

---

## Problem Statement

### Current Issues

1. **Basic Theme Configuration**: The litestar-vite docs use the `litestar_sphinx_theme` but with most theme options commented out (`docs/conf.py:169-213`), resulting in an underutilized, bare-bones appearance.

2. **Sparse Landing Page**: The current `docs/index.rst` is minimal (72 lines) with:
   - Basic feature list with emojis
   - Installation instructions
   - Empty "Usage" section with a TODO marker
   - No visual demonstrations or engaging content

3. **Missing Visual Demonstrations**: No animated GIFs or terminal recordings to showcase:
   - CLI scaffolding commands
   - HMR in action
   - Project setup workflows

4. **Inconsistent with Parent Project**: The Litestar main docs feature:
   - Rich landing page with logo, badges, and sponsor sections
   - Feature grid with 6 cards (Tutorials, Topics, Changelog, Discussions, Issues, Contributing)
   - Professional navigation with call-to-action buttons
   - Versioning support with `versioning.js`

---

## Goals

### Primary Goals

1. **Theme Alignment**: Enable and configure all `litestar_sphinx_theme` options to match Litestar docs
2. **Landing Page Redesign**: Create an engaging, feature-rich landing page
3. **Dynamic GIF Generation**: Implement automated terminal recording generation during docs build
4. **GitHub Pages Deployment**: Ensure docs are properly deployed and accessible

### Success Metrics

- Landing page has visual parity with main Litestar docs
- At least 3 animated demonstrations are generated automatically
- Docs build time increases by no more than 60 seconds
- Zero broken links in final build

---

## Research Findings

### Litestar Main Docs Analysis

**Source**: `github.com/litestar-org/litestar/docs/`

| Component | Litestar Implementation |
|-----------|------------------------|
| **Framework** | Sphinx 7.1.2+ |
| **Theme** | `litestar_sphinx_theme` (v3) |
| **Extensions** | 15+ including `sphinxcontrib.mermaid`, `sphinx_paramlinks`, `sphinx_togglebutton` |
| **Landing Page** | Logo (400x400), badges, 4 CTA buttons, 6 feature cards, sponsor section |
| **Static Assets** | favicon, logos, versioning.js, custom CSS |
| **Deployment** | GitHub Pages via `JamesIves/github-pages-deploy-action@v4` |

**Key Differentiators**:
- Versioning support (`versioning.js`, `versions.json`)
- Rich `html_context` with navigation menus
- Sponsor integration
- Mermaid diagrams support

### litestar-vite Current Docs Analysis

**Source**: `/home/cody/code/litestar/litestar-vite/docs/`

| Component | Current State | Gap |
|-----------|--------------|-----|
| **Theme** | `litestar_sphinx_theme` | Options commented out |
| **Extensions** | 13 | Missing mermaid, paramlinks, togglebutton |
| **Landing Page** | Basic text + installation | No visuals, no cards, no CTAs |
| **Static Assets** | `style.css` only | Missing logos, favicons, versioning |
| **Deployment** | GitHub Pages (working) | No versioning |

### Animated GIF Generation Options

#### Option 1: Charmbracelet VHS (Recommended)

**Repository**: [charmbracelet/vhs](https://github.com/charmbracelet/vhs)

**Pros**:
- Write terminal recordings as code (`.tape` files)
- Deterministic, reproducible outputs
- GitHub Action available: [vhs-action](https://github.com/charmbracelet/vhs-action)
- Multiple output formats: GIF, MP4, WebM, PNG sequence
- Highly configurable (fonts, themes, dimensions)

**Cons**:
- Requires `ttyd` and `ffmpeg` dependencies
- Go-based tool (not Python)
- Adds CI build time

**Example `.tape` file**:
```tape
Output demo.gif
Set FontSize 14
Set Width 800
Set Height 400
Set Theme "Dracula"

Type "litestar assets init --template react"
Enter
Sleep 2s
Type "y"
Enter
Sleep 3s
```

#### Option 2: asciinema + SVG

**Pros**:
- Mature ecosystem
- SVG output is crisp at all resolutions
- Smaller file sizes than GIF
- Sphinx extension: `sphinxcontrib.asciinema`

**Cons**:
- SVG rendering requires JavaScript player
- Less deterministic (real-time recording)
- svg-term-cli hasn't been updated in 5+ years

#### Option 3: termsvg

**Pros**:
- Go-based, actively maintained
- Direct SVG output

**Cons**:
- Early stage
- Less feature-rich than VHS

### Recommendation

**Use Charmbracelet VHS with vhs-action** for the following reasons:
1. Declarative tape files can be version-controlled
2. Deterministic builds ensure consistency
3. GitHub Action integration fits existing workflow
4. GIF format has universal support in documentation

---

## Technical Specification

### Phase 1: Theme Configuration Enhancement

#### 1.1 Enable Theme Options (`docs/conf.py`)

Uncomment and configure:
```python
html_theme_options = {
    "logo_target": "/",
    "github_url": "https://github.com/litestar-org/litestar-vite",
    "github_repo_name": "Litestar Vite",
    "nav_links": [
        {"title": "Home", "url": "https://litestar-org.github.io/litestar-vite/"},
        {"title": "Docs", "url": "https://litestar-org.github.io/litestar-vite/latest/"},
        {"title": "Code", "url": "https://github.com/litestar-org/litestar-vite"},
    ],
    "light_css_variables": { ... },
    "dark_css_variables": { ... },
}
```

#### 1.2 Add Missing Extensions

```python
extensions = [
    # Existing...
    "sphinxcontrib.mermaid",      # Diagram support
    "sphinx_paramlinks",           # Parameter linking
    "sphinx_togglebutton",         # Collapsible sections
]
```

#### 1.3 Add Static Assets

```
docs/_static/
├── favicon.png
├── favicon.svg
├── logo-dark.png
├── logo-light.png
├── logo.svg
├── versioning.js (if implementing versioning)
└── style.css (enhance existing)
```

### Phase 2: Landing Page Redesign

#### 2.1 New `docs/index.rst` Structure

```rst
==============
Litestar Vite
==============

.. image:: _static/logo.svg
   :alt: Litestar Vite
   :class: landing-logo
   :width: 400px

.. badges (GitHub stars, PyPI version, coverage, etc.)

Supercharge your Litestar applications with Vite's modern frontend tooling.

.. grid:: 2
    :gutter: 3

    .. grid-item-card:: Getting Started
        :link: usage/index
        :link-type: doc

        Quick start guide for integrating Vite with Litestar

    .. grid-item-card:: Inertia.js
        :link: usage/inertia
        :link-type: doc

        Build SPAs with server-side routing using Inertia.js

.. Demo Section with animated GIFs

See it in Action
----------------

.. tab-set::

    .. tab-item:: Project Scaffolding

        .. image:: _static/demos/scaffolding.gif
           :alt: Project scaffolding demo

    .. tab-item:: Hot Module Replacement

        .. image:: _static/demos/hmr.gif
           :alt: HMR demo

.. Feature Cards (6-card grid like Litestar)
```

### Phase 3: Dynamic GIF Generation

#### 3.1 VHS Tape Files

Create `docs/_tapes/` directory:

```
docs/_tapes/
├── scaffolding.tape    # litestar assets init demo
├── hmr.tape            # HMR demonstration
└── build.tape          # Production build demo
```

**Example: `scaffolding.tape`**
```tape
Output docs/_static/demos/scaffolding.gif

Require litestar

Set Shell "bash"
Set FontSize 14
Set Width 900
Set Height 500
Set Theme "Catppuccin Mocha"
Set Padding 20

Type "litestar assets init"
Enter
Sleep 1500ms

Type "my-app"
Enter
Sleep 500ms

# Select React template
Down
Down
Enter
Sleep 500ms

# Confirm
Type "y"
Enter
Sleep 3000ms

Type "ls -la my-app/"
Enter
Sleep 2000ms
```

#### 3.2 GitHub Workflow Update

Modify `.github/workflows/docs.yml`:

```yaml
name: Documentation Building

on:
  release:
    types: [published]
  push:
    branches:
      - main
    paths:
      - 'docs/**'
      - 'src/py/litestar_vite/**'
  workflow_dispatch:

jobs:
  generate-demos:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync --all-extras --dev

      - name: Install litestar-vite CLI
        run: uv pip install -e .

      - name: Generate Demo GIFs
        uses: charmbracelet/vhs-action@v2
        with:
          path: "docs/_tapes/*.tape"
          install-fonts: true

      - name: Upload demos artifact
        uses: actions/upload-artifact@v4
        with:
          name: demo-gifs
          path: docs/_static/demos/

  build:
    needs: generate-demos
    permissions:
      contents: write
      pages: write
      id-token: write
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download demo artifacts
        uses: actions/download-artifact@v4
        with:
          name: demo-gifs
          path: docs/_static/demos/

      # ... rest of existing build steps
```

#### 3.3 Local Development Support

Add Makefile target:
```makefile
docs-demos:  ## Generate demo GIFs locally (requires vhs)
    @command -v vhs >/dev/null 2>&1 || { echo "VHS required: brew install vhs"; exit 1; }
    mkdir -p docs/_static/demos
    for tape in docs/_tapes/*.tape; do vhs "$$tape"; done
```

### Phase 4: Additional Enhancements

#### 4.1 Versioning Support (Optional)

If implementing multi-version docs like Litestar main:

1. Add `versioning.js` from Litestar
2. Create `versions.json` with version entries
3. Update `build_docs.py` for version handling

#### 4.2 Mermaid Diagrams

Enable architecture diagrams in documentation:

```rst
.. mermaid::

   flowchart LR
       A[Litestar App] --> B[VitePlugin]
       B --> C{Mode?}
       C -->|Dev| D[Vite Dev Server]
       C -->|Prod| E[Manifest]
```

---

## Dependencies

### New Python Dependencies

```toml
[project.optional-dependencies]
docs = [
    # Existing...
    "sphinxcontrib-mermaid>=0.9.2",
    "sphinx-paramlinks>=0.6.0",
    "sphinx-togglebutton>=0.3.2",
]
```

### CI Dependencies

- VHS GitHub Action: `charmbracelet/vhs-action@v2`
- Fonts (optional): JetBrains Mono (included), or custom fonts

### Local Development

- VHS CLI: `brew install vhs` (macOS) or from [releases](https://github.com/charmbracelet/vhs/releases)
- ffmpeg: Required by VHS
- ttyd: Required by VHS

---

## Implementation Phases

### Phase 1: Theme & Config (2-3 days)
- Enable theme options
- Add missing Sphinx extensions
- Add static assets (logos, favicons)

### Phase 2: Landing Page (2-3 days)
- Redesign index.rst with cards and grids
- Add badges and CTAs
- Create placeholder for demos

### Phase 3: GIF Generation (3-4 days)
- Create VHS tape files
- Update GitHub workflow
- Add local development support
- Test CI pipeline

### Phase 4: Polish (1-2 days)
- Review and test all pages
- Fix any broken links
- Performance optimization

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| VHS build failures in CI | Demo GIFs not updated | Cache GIFs, fallback to existing |
| Build time increase | Slower deployments | Parallel jobs, conditional execution |
| Theme incompatibility | Visual bugs | Test locally, use pinned theme version |
| GIF file size | Slow page loads | Optimize dimensions, use WebP fallback |

---

## Decisions

1. **Versioning**: No multi-version docs for now - single version only
2. **Sponsor Section**: No sponsor section on landing page
3. **Tutorials**: Yes - create dedicated tutorial content

## Tutorials to Create

Based on project capabilities, the following tutorials should be created:

### Tutorial 1: Getting Started with Vite + Litestar
- Basic setup from scratch
- Configuring VitePlugin
- Running dev server with HMR
- Building for production

### Tutorial 2: Building a React SPA with Inertia.js
- Setting up Inertia with React
- Creating pages and layouts
- Handling navigation
- Sharing data between server and client

### Tutorial 3: Vue.js Integration
- Vue 3 setup with Vite
- Component-based architecture
- State management patterns

### Tutorial 4: Project Scaffolding
- Using `litestar assets init`
- Template options (React, Vue, Svelte, HTMX)
- Customizing generated projects

### Tutorial 5: Advanced Configuration
- Custom Vite configurations
- Asset bundling strategies
- Environment-specific settings

---

## References

- [Litestar Docs Repository](https://github.com/litestar-org/litestar/tree/main/docs)
- [litestar-sphinx-theme](https://github.com/litestar-org/litestar-sphinx-theme)
- [Charmbracelet VHS](https://github.com/charmbracelet/vhs)
- [VHS GitHub Action](https://github.com/charmbracelet/vhs-action)
- [asciinema Integrations](https://docs.asciinema.org/integrations/)
- [sphinx-design](https://sphinx-design.readthedocs.io/)

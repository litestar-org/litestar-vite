# Tasks: Inertia Documentation Redesign

## Phase 0: Pre-Implementation Verification

> **IMPORTANT**: Complete this phase before writing any documentation

- [ ] **Re-evaluate API consistency**
  - [ ] Read `src/py/litestar_vite/config.py` and verify InertiaConfig matches PRD
  - [ ] Read `src/py/litestar_vite/inertia/helpers.py` and verify all helpers match PRD
  - [ ] Read `src/py/litestar_vite/inertia/response.py` and verify response classes match PRD
  - [ ] Run `make test` to ensure all tests pass
  - [ ] Update PRD if any API differences found
- [ ] **Verify inertia-typed-page-props completion**
  - [ ] Check if `specs/active/inertia-typed-page-props/` is moved to archive (completed)
  - [ ] Verify TypeGenConfig has `generate_page_props`, `page_props_path` options
  - [ ] Verify `litestar assets generate-types` creates `page-props.ts`
  - [ ] If not complete, document current state and what's available
- [ ] **Document any deviations from PRD** in recovery.md

## Phase 1: Planning
- [x] Create PRD
- [x] Identify documentation structure
- [x] Map current content to new pages
- [x] Incorporate inertia-typed-page-props features into docs plan

## Phase 2: Setup

- [ ] Create `docs/inertia/` directory
- [ ] Create `docs/inertia/index.rst` with section toctree
- [ ] Update `docs/index.rst` to include new inertia section

## Phase 3: Core Documentation Pages

### Getting Started
- [ ] Create `docs/inertia/installation.rst` - Installation and setup guide
- [ ] Create `docs/inertia/configuration.rst` - InertiaConfig reference (complete)

### Core Concepts
- [ ] Create `docs/inertia/how-it-works.rst` - Protocol explanation with link to official

### The Basics
- [ ] Create `docs/inertia/pages.rst` - Component kwarg, page routing
- [ ] Create `docs/inertia/responses.rst` - InertiaResponse, props
- [ ] Create `docs/inertia/redirects.rst` - InertiaRedirect, InertiaBack, InertiaExternalRedirect
- [ ] Create `docs/inertia/forms.rst` - Form handling, validation, errors
- [ ] Create `docs/inertia/links.rst` - route() helper, navigation

### Data & Props
- [ ] Create `docs/inertia/shared-data.rst` - share(), extra_static_page_props, extra_session_page_props
- [ ] Create `docs/inertia/partial-reloads.rst` - Lazy props, only(), except_()
- [ ] Create `docs/inertia/deferred-props.rst` - defer(), lazy(), groups
- [ ] Create `docs/inertia/merging-props.rst` - merge(), scroll_props(), infinite scroll

### Security
- [ ] Create `docs/inertia/csrf-protection.rst` - CSRFConfig setup
- [ ] Create `docs/inertia/history-encryption.rst` - encrypt_history, clear_history()

### Advanced
- [ ] Create `docs/inertia/templates.rst` - Root template reference, all helpers
- [ ] Create `docs/inertia/error-handling.rst` - Exception handlers, validation
- [ ] Create `docs/inertia/asset-versioning.rst` - Version checking, 409 handling

### TypeScript Integration (from inertia-typed-page-props)
- [ ] Create `docs/inertia/typescript.rst` - Overview of TypeScript integration
- [ ] Create `docs/inertia/type-generation.rst` - TypeGenConfig, routes.ts, page-props.ts
- [ ] Create `docs/inertia/typed-page-props.rst` - PageProps usage in Vue/React/Svelte
- [ ] Create `docs/inertia/shared-props-typing.rst` - SharedProps extension via module augmentation

### Examples
- [ ] Create `docs/inertia/fullstack-example.rst` - Reference to litestar-fullstack-inertia

## Phase 4: Cleanup

- [ ] Update `docs/frameworks/inertia.rst` to point to new section
- [ ] Archive or redirect `docs/usage/inertia.rst`
- [ ] Add cross-references (See Also) to all pages
- [ ] Verify all internal links work

## Phase 5: Quality

- [ ] Build docs locally (`make docs`)
- [ ] Fix any RST warnings/errors
- [ ] Review each page for conciseness (<200 lines)
- [ ] Verify all external links are valid
- [ ] Final review of rendered documentation

## Definition of Done

- [ ] **Phase 0 verification complete** - API matches documentation
- [ ] All pages created and properly linked
- [ ] Docs build without warnings
- [ ] Structure mirrors official Inertia.js docs
- [ ] Each page is focused and concise
- [ ] All config options documented (InertiaConfig + TypeGenConfig)
- [ ] All helpers documented
- [ ] Template helpers documented
- [ ] TypeScript type generation documented (PageProps, SharedProps)
- [ ] Links to official docs where appropriate

## Dependencies

```
inertia-typed-page-props (must complete first)
         │
         ▼
Phase 0: Pre-Implementation Verification
         │
         ▼
Phase 2: Setup
         │
         ▼
Phase 3: Core Documentation
         │
         ├── Getting Started (no deps)
         ├── Core Concepts (no deps)
         ├── The Basics (no deps)
         ├── Data & Props (no deps)
         ├── Security (no deps)
         ├── Advanced (no deps)
         └── TypeScript Integration (depends on inertia-typed-page-props)
         │
         ▼
Phase 4: Cleanup
         │
         ▼
Phase 5: Quality Gate
```

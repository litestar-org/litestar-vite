# Angular Integration - Implementation Tasks

**PRD:** [prd.md](./prd.md)
**Status:** Not Started

---

## Phase 1: Core Scaffolding (MVP)

### 1.1 Framework Types & Templates

#### Option A: Vite-based (`angular`)

- [ ] Add `ANGULAR = "angular"` to `FrameworkType` enum in `templates.py`
- [ ] Create `FrameworkTemplate` configuration for Angular (Vite-based)
- [ ] Verify template is accessible via `get_template(FrameworkType.ANGULAR)`

#### Option B: Angular CLI-based (`angular-cli`)

- [ ] Add `ANGULAR_CLI = "angular-cli"` to `FrameworkType` enum
- [ ] Create `FrameworkTemplate` configuration for Angular CLI
- [ ] Add `uses_vite=False` flag to template (skip litestar-vite-plugin)
- [ ] Verify template is accessible via `get_template(FrameworkType.ANGULAR_CLI)`

### 1.2 Template Files (Vite-based)

- [ ] Create `src/py/litestar_vite/templates/angular/` directory
- [ ] Create `vite.config.ts.j2`
- [ ] Create `tsconfig.json.j2`
- [ ] Create `tsconfig.app.json.j2`
- [ ] Create `index.html.j2`
- [ ] Create `package.json.j2`
- [ ] Create `src/main.ts.j2`
- [ ] Create `src/styles.css.j2`
- [ ] Create `src/app/app.component.ts.j2`
- [ ] Create `src/app/app.component.html.j2`
- [ ] Create `src/app/app.component.css.j2`
- [ ] Create `src/app/app.config.ts.j2`
- [ ] Create `src/app/app.routes.ts.j2`
- [ ] Ensure Vite config aligns with litestar single-port proxy defaults (hotfile at `public/hot`, assetUrl `/static/`, dev server proxy to ASGI when single-port mode active)
- [ ] Include generated types/routes defaults (`src/generated/*`) matching litestar typed-routes pipeline

### 1.3 Template Files (Angular CLI-based)

- [ ] Create `src/py/litestar_vite/templates/angular-cli/` directory
- [ ] Create `angular.json.j2`
- [ ] Create `tsconfig.json.j2`
- [ ] Create `tsconfig.app.json.j2`
- [ ] Create `tsconfig.spec.json.j2`
- [ ] Create `package.json.j2`
- [ ] Create `proxy.conf.json.j2`
- [ ] Create `src/index.html.j2`
- [ ] Create `src/main.ts.j2`
- [ ] Create `src/styles.css.j2`
- [ ] Create `src/app/` component files (same as Vite-based)
- [ ] Document that typed-routes/proxy automation does not apply; rely on Angular CLI proxy for API

### 1.4 Testing

- [ ] Add unit tests for Angular template registration
- [ ] Add unit tests for Angular CLI template registration
- [ ] Add unit tests for file generation (both templates)
- [ ] Manual test: `litestar vite init --framework angular`
- [ ] Manual test: `litestar vite init --framework angular-cli`
- [ ] Manual test: Vite-based - `npm install && npm run dev`
- [ ] Manual test: Angular CLI - `npm install && npm start`
- [ ] Manual test: Both - production build
- [ ] Manual test: Vite-based single-port mode (ASGI proxy) with HMR/WebSocket

---

## Phase 2: Build Integration

### 2.1 Vite-based (`angular`) Integration

- [ ] Verify `litestar-vite-plugin` works with `@analogjs/vite-plugin-angular`
- [ ] Test HMR with Angular component changes
- [ ] Test CSS changes trigger reload
- [ ] Verify production build outputs correct files
- [ ] Verify manifest.json generation
- [ ] Test asset URL resolution in production

### 2.2 Angular CLI-based (`angular-cli`) Integration

- [ ] Verify Angular CLI builds to correct output directory
- [ ] Test `ng serve` with proxy configuration
- [ ] Verify Litestar serves static `dist/browser/` output
- [ ] Document that manifest.json is not used (static file serving)

---

## Phase 3: Documentation & Examples

### 3.1 Documentation

- [ ] Add Angular section to usage docs (both options)
- [ ] Document trade-offs between Vite-based and Angular CLI approaches
- [ ] Add troubleshooting section
- [ ] Update framework comparison table

### 3.2 Example Projects

- [ ] Create `examples/angular/` directory (Vite-based)
- [ ] Create `examples/angular-cli/` directory (Angular CLI-based)
- [ ] Add working Litestar + Angular examples
- [ ] Include API route examples
- [ ] Add README with setup instructions for each

---

## Phase 4: Optional Enhancements (Future)

### 4.1 SSR Support

- [ ] Research AnalogJS SSR with external backend
- [ ] Create SSR configuration template
- [ ] Document SSR deployment patterns

### 4.2 Additional Features

- [ ] TailwindCSS addon compatibility (both options)
- [ ] Angular Material integration option
- [ ] Zoneless mode documentation

---

## Acceptance Criteria

### Vite-based (`angular`)

1. `litestar vite init --framework angular` generates valid project
2. `npm install` succeeds without errors
3. `npm run dev` starts Vite with HMR
4. Angular component edits trigger hot reload
5. `npm run build` produces production bundle with manifest
6. Litestar serves production assets via manifest

### Angular CLI-based (`angular-cli`)

1. `litestar vite init --framework angular-cli` generates valid project
2. `npm install` succeeds without errors
3. `npm start` starts Angular dev server with proxy
4. Angular component edits trigger hot reload
5. `npm run build` produces production bundle
6. Litestar serves static files from `dist/browser/`

### Both

1. API proxy to Litestar works in development
2. All existing tests continue to pass
3. Documentation is complete and accurate

---

## Phase 5: Cleanup & Agent Updates

### 5.1 Agent Command Templates

- [ ] Update `.claude/commands/update-templates.md` to include Angular framework handling
- [ ] Update `.gemini/commands/update-templates.md` to include Angular framework handling
- [ ] Ensure agents know about `angular` vs `angular-cli` distinction
- [ ] Document Angular-specific patterns (standalone components, zone.js, etc.)

### 5.2 Final Cleanup

- [ ] Run full test suite (`make test`)
- [ ] Run linting (`make lint`)
- [ ] Verify all quality gates pass
- [ ] Update CHANGELOG with Angular support
- [ ] Archive workspace to `specs/archive/`

---

## Notes

- Target Angular 18+ for initial implementation
- Use standalone components (not NgModules)
- Include RxJS and zone.js in dependencies
- SSR deferred to future iteration

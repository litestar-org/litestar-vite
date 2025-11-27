# PRD: Angular Integration (SPA)

**Status:** Draft
**Author:** AI Assistant
**Created:** 2025-11-27
**Target Version:** 0.15.0+

---

## 1. Overview

### 1.1 Problem Statement

litestar-vite currently supports React, Vue, Svelte, SvelteKit, Nuxt, Astro, and HTMX for frontend scaffolding. Angular, one of the most widely-used enterprise frameworks, is notably absent. Users who prefer Angular must manually configure their projects, losing the benefits of the integrated scaffolding system.

### 1.2 Proposed Solution

Add Angular SPA support with **two approaches**:

#### Option A: Vite-based (Recommended) - `--framework angular`

Uses `@analogjs/vite-plugin-angular` - the standalone Vite plugin for Angular compilation. This is **not** the AnalogJS meta-framework, but rather just the compilation plugin that enables vanilla Angular apps to use Vite directly.

This approach:

- Creates a **simple SPA** (like our React/Vue templates), not a meta-framework
- Uses standard `vite.config.ts` (compatible with `litestar-vite-plugin`)
- No SSR complexity - just a client-side Angular app
- Familiar to Angular developers - standard component structure
- Mirrors the pattern of React/Vue scaffolds
- Full Vite ecosystem access (HMR, plugins, optimized builds)

#### Option B: Angular CLI-based - `--framework angular-cli`

For developers who prefer the official Angular CLI toolchain:

- Uses `ng new` style project with `angular.json` configuration
- Angular CLI handles all building via `@angular-devkit/build-angular`
- Litestar serves the static output from `dist/browser/`
- No `litestar-vite-plugin` integration (Angular CLI wraps Vite internally)
- API proxy configured in `angular.json` proxy configuration

**Trade-offs:**

| Aspect | Vite-based (`angular`) | Angular CLI (`angular-cli`) |
|--------|------------------------|----------------------------|
| Build tool | Vite (direct) | Angular CLI (wraps Vite) |
| Config file | `vite.config.ts` | `angular.json` |
| litestar-vite-plugin | ✅ Full integration | ❌ Not applicable |
| Manifest generation | ✅ Automatic | ❌ Manual static serving |
| HMR proxy | ✅ Via Vite | ✅ Via Angular CLI |
| Familiar to Angular devs | Moderate | High |
| Vite plugin ecosystem | ✅ Full access | ❌ Limited |

### 1.3 Goals

1. Enable `litestar vite init --framework angular` scaffolding (Vite-based)
2. Enable `litestar vite init --framework angular-cli` scaffolding (Angular CLI-based)
3. Generate **vanilla Angular 18+ SPAs** (not AnalogJS meta-framework)
4. Provide working Angular + Litestar development environment
5. Support HMR via Vite dev server (angular) or Angular CLI (angular-cli)
6. Enable production builds with proper asset handling
7. Align with litestar single-port proxy + typed-routes pipeline: Vite-based Angular uses hotfile `public/hot`, asset base `/static/`, and generated artifacts in `src/generated/*`; Angular-CLI path explicitly documented as outside this automation.

### 1.4 Non-Goals (v1)

1. Inertia.js support (no official Angular adapter exists)
2. SSR/SSG support (keep it simple - SPA only)
3. AnalogJS meta-framework features (file-based routing, API routes)
4. Zone.js-free (zoneless) mode by default
5. Angular Material or other UI library scaffolding

---

## 2. Background Research

### 2.1 Angular Build System Evolution

| Version | Build System | Vite Support |
|---------|--------------|--------------|
| v16 | Webpack (default), esbuild (preview) | Dev preview |
| v17 | esbuild + Vite (default for new) | Full support |
| v18+ | esbuild + Vite (stable) | Native |
| v20+ | esbuild + Vite | Enhanced |

Angular CLI v17+ uses Vite internally for the dev server, but wraps it in the Angular-specific `@angular-devkit/build-angular:application` builder. This makes it incompatible with custom `vite.config.ts` files.

### 2.2 @analogjs/vite-plugin-angular (Standalone)

The key insight: `@analogjs/vite-plugin-angular` can be used **independently** of the AnalogJS meta-framework. It's just a Vite plugin that compiles Angular components.

From the [AnalogJS documentation](https://analogjs.org/docs/packages/vite-plugin-angular/overview):
> "The Analog Vite plugin for Angular is usable for outside ecosystems including Astro, Qwik, Playwright, and **Vanilla Vite + Angular app**"

**How it works:**
- Tells Vite how to transpile Angular source files into JavaScript
- Uses Angular Compiler (like the official Angular CLI)
- Works for both development AND production builds
- Full access to Vite plugin ecosystem

**Requirements:**
- `tsconfig.app.json` at project root
- Standalone components (Angular 14+)

### 2.3 Integration Pattern Comparison

| Framework | Our Template Type | Vite Plugin | Pattern |
|-----------|------------------|-------------|---------|
| React | SPA | `@vitejs/plugin-react` | Simple SPA |
| Vue | SPA | `@vitejs/plugin-vue` | Simple SPA |
| Svelte | SPA | `@sveltejs/vite-plugin-svelte` | Simple SPA |
| **Angular** | **SPA** | `@analogjs/vite-plugin-angular` | **Simple SPA** |
| SvelteKit | Meta-framework | N/A (own build) | SSR |
| Nuxt | Meta-framework | N/A (own build) | SSR |

**Key point:** Angular template follows the React/Vue/Svelte SPA pattern, NOT the Nuxt/SvelteKit meta-framework pattern.

---

## 3. Technical Design

### 3.1 New Framework Types

```python
# src/py/litestar_vite/scaffolding/templates.py

class FrameworkType(str, Enum):
    # ... existing ...
    ANGULAR = "angular"          # Vite-based (recommended)
    ANGULAR_CLI = "angular-cli"  # Angular CLI-based (native)
```

### 3.2 Template Configurations

#### Option A: Vite-based (`angular`)

```python
FrameworkType.ANGULAR: FrameworkTemplate(
    name="Angular",
    type=FrameworkType.ANGULAR,
    description="Angular 18+ SPA with Vite",
    vite_plugin="@analogjs/vite-plugin-angular",
    dependencies=[
        "@angular/core",
        "@angular/common",
        "@angular/compiler",
        "@angular/platform-browser",
        "@angular/platform-browser-dynamic",
        "@angular/router",
        "rxjs",
        "zone.js",
    ],
    dev_dependencies=[
        "@analogjs/vite-plugin-angular",
        "typescript",
        "litestar-vite-plugin",
    ],
    files=[
        "vite.config.ts",
        "tsconfig.json",
        "tsconfig.app.json",
        "package.json",
        "index.html",
        "src/main.ts",
        "src/styles.css",
        "src/app/app.component.ts",
        "src/app/app.component.html",
        "src/app/app.component.css",
        "src/app/app.config.ts",
        "src/app/app.routes.ts",
    ],
    uses_typescript=True,
    has_ssr=False,  # SPA only
    inertia_compatible=False,
    notes="Leverages litestar-vite single-port proxy + typed-routes defaults (hotfile public/hot, asset base /static/, generated artifacts in src/generated).",
),
```

#### Option B: Angular CLI-based (`angular-cli`)

```python
FrameworkType.ANGULAR_CLI: FrameworkTemplate(
    name="Angular (CLI)",
    type=FrameworkType.ANGULAR_CLI,
    description="Angular 18+ SPA with Angular CLI",
    vite_plugin=None,  # No Vite plugin - Angular CLI wraps Vite internally
    dependencies=[
        "@angular/animations",
        "@angular/common",
        "@angular/compiler",
        "@angular/core",
        "@angular/forms",
        "@angular/platform-browser",
        "@angular/platform-browser-dynamic",
        "@angular/router",
        "rxjs",
        "tslib",
        "zone.js",
    ],
    dev_dependencies=[
        "@angular-devkit/build-angular",
        "@angular/cli",
        "@angular/compiler-cli",
        "typescript",
    ],
    files=[
        "angular.json",
        "tsconfig.json",
        "tsconfig.app.json",
        "tsconfig.spec.json",
        "package.json",
        "src/index.html",
        "src/main.ts",
        "src/styles.css",
        "src/app/app.component.ts",
        "src/app/app.component.html",
        "src/app/app.component.css",
        "src/app/app.config.ts",
        "src/app/app.routes.ts",
        "proxy.conf.json",  # API proxy configuration
    ],
    uses_typescript=True,
    has_ssr=False,  # SPA only
    inertia_compatible=False,
    uses_vite=False,  # Does not use litestar-vite-plugin
    notes="Angular CLI wraps Vite; typed-routes/proxy automation not applied. Use Angular proxy.conf for API.",
),
```

### 3.3 Template Files

#### `vite.config.ts.j2`

```typescript
import { defineConfig } from "vite";
import angular from "@analogjs/vite-plugin-angular";
import litestar from "litestar-vite-plugin";

export default defineConfig({
  plugins: [
    angular(),
    litestar({
      input: ["src/main.ts", "src/styles.css"],
      refresh: true,
    }),
  ],
  server: {
    port: {{ vite_port }},
    proxy: {
      "/api": {
        target: "http://localhost:{{ litestar_port }}",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "{{ bundle_dir }}",
    target: "esnext",
  },
});
```

#### `src/main.ts.j2`

```typescript
import { bootstrapApplication } from "@angular/platform-browser";
import { AppComponent } from "./app/app.component";
import { appConfig } from "./app/app.config";

bootstrapApplication(AppComponent, appConfig)
  .catch((err) => console.error(err));
```

#### `src/app/app.component.ts.j2`

```typescript
import { Component } from "@angular/core";
import { RouterOutlet } from "@angular/router";

@Component({
  selector: "app-root",
  standalone: true,
  imports: [RouterOutlet],
  templateUrl: "./app.component.html",
  styleUrl: "./app.component.css",
})
export class AppComponent {
  title = "{{ project_name }}";
}
```

#### `src/app/app.component.html.j2`

```html
<main class="container">
  <h1>Welcome to {{ "{{" }} title {{ "}}" }}</h1>
  <p>Angular + Litestar + Vite</p>

  <div class="card">
    <h2>Getting Started</h2>
    <p>Edit <code>src/app/app.component.ts</code> to modify this page.</p>
  </div>

  <router-outlet />
</main>
```

#### `src/app/app.component.css.j2`

```css
.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
  text-align: center;
}

.card {
  background: #f5f5f5;
  border-radius: 8px;
  padding: 1.5rem;
  margin-top: 2rem;
}

code {
  background: #e0e0e0;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-family: monospace;
}
```

#### `src/app/app.config.ts.j2`

```typescript
import { ApplicationConfig, provideZoneChangeDetection } from "@angular/core";
import { provideRouter } from "@angular/router";
import { provideHttpClient } from "@angular/common/http";
import { routes } from "./app.routes";

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideHttpClient(),
  ],
};
```

#### `src/app/app.routes.ts.j2`

```typescript
import { Routes } from "@angular/router";

export const routes: Routes = [];
```

#### `tsconfig.json.j2`

```json
{
  "compileOnSave": false,
  "compilerOptions": {
    "outDir": "./dist/out-tsc",
    "strict": true,
    "noImplicitOverride": true,
    "noPropertyAccessFromIndexSignature": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "experimentalDecorators": true,
    "moduleResolution": "bundler",
    "importHelpers": true,
    "target": "ES2022",
    "module": "ES2022",
    "lib": ["ES2022", "dom"],
    "types": ["vite/client"]
  },
  "angularCompilerOptions": {
    "enableI18nLegacyMessageIdFormat": false,
    "strictInjectionParameters": true,
    "strictInputAccessModifiers": true,
    "strictTemplates": true
  }
}
```

#### `tsconfig.app.json.j2`

```json
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "outDir": "./out-tsc/app",
    "types": []
  },
  "files": ["src/main.ts"],
  "include": ["src/**/*.ts"]
}
```

#### `index.html.j2`

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{{ project_name }}</title>
    <link rel="stylesheet" href="/src/styles.css" />
  </head>
  <body>
    <app-root></app-root>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

#### `src/styles.css.j2`

```css
*,
*::before,
*::after {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen,
    Ubuntu, Cantarell, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

### 3.4 Package.json Templates

#### Vite-based (`angular`)

```json
{
  "name": "{{ project_name }}",
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@angular/common": "^18.0.0",
    "@angular/compiler": "^18.0.0",
    "@angular/core": "^18.0.0",
    "@angular/platform-browser": "^18.0.0",
    "@angular/platform-browser-dynamic": "^18.0.0",
    "@angular/router": "^18.0.0",
    "rxjs": "^7.8.0",
    "zone.js": "^0.14.0"
  },
  "devDependencies": {
    "@analogjs/vite-plugin-angular": "^1.0.0",
    "litestar-vite-plugin": "^{{ version }}",
    "typescript": "~5.4.0",
    "vite": "^6.0.0"
  }
}
```

#### Angular CLI-based (`angular-cli`)

```json
{
  "name": "{{ project_name }}",
  "version": "0.0.0",
  "scripts": {
    "ng": "ng",
    "start": "ng serve --proxy-config proxy.conf.json",
    "build": "ng build",
    "watch": "ng build --watch --configuration development"
  },
  "dependencies": {
    "@angular/animations": "^18.0.0",
    "@angular/common": "^18.0.0",
    "@angular/compiler": "^18.0.0",
    "@angular/core": "^18.0.0",
    "@angular/forms": "^18.0.0",
    "@angular/platform-browser": "^18.0.0",
    "@angular/platform-browser-dynamic": "^18.0.0",
    "@angular/router": "^18.0.0",
    "rxjs": "^7.8.0",
    "tslib": "^2.6.0",
    "zone.js": "^0.14.0"
  },
  "devDependencies": {
    "@angular-devkit/build-angular": "^18.0.0",
    "@angular/cli": "^18.0.0",
    "@angular/compiler-cli": "^18.0.0",
    "typescript": "~5.4.0"
  }
}
```

### 3.5 Angular CLI-specific Template Files

#### `angular.json.j2`

```json
{
  "$schema": "./node_modules/@angular/cli/lib/config/schema.json",
  "version": 1,
  "newProjectRoot": "projects",
  "projects": {
    "{{ project_name }}": {
      "projectType": "application",
      "root": "",
      "sourceRoot": "src",
      "prefix": "app",
      "architect": {
        "build": {
          "builder": "@angular-devkit/build-angular:application",
          "options": {
            "outputPath": "{{ bundle_dir }}",
            "index": "src/index.html",
            "browser": "src/main.ts",
            "polyfills": ["zone.js"],
            "tsConfig": "tsconfig.app.json",
            "assets": [{ "glob": "**/*", "input": "public" }],
            "styles": ["src/styles.css"],
            "scripts": []
          },
          "configurations": {
            "production": {
              "budgets": [
                { "type": "initial", "maximumWarning": "500kB", "maximumError": "1MB" },
                { "type": "anyComponentStyle", "maximumWarning": "2kB", "maximumError": "4kB" }
              ],
              "outputHashing": "all"
            },
            "development": {
              "optimization": false,
              "extractLicenses": false,
              "sourceMap": true
            }
          },
          "defaultConfiguration": "production"
        },
        "serve": {
          "builder": "@angular-devkit/build-angular:dev-server",
          "configurations": {
            "production": { "buildTarget": "{{ project_name }}:build:production" },
            "development": { "buildTarget": "{{ project_name }}:build:development" }
          },
          "defaultConfiguration": "development"
        }
      }
    }
  }
}
```

#### `proxy.conf.json.j2`

```json
{
  "/api": {
    "target": "http://localhost:{{ litestar_port }}",
    "secure": false,
    "changeOrigin": true
  }
}
```

#### `src/index.html.j2` (Angular CLI version)

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{{ project_name }}</title>
    <base href="/" />
    <link rel="icon" type="image/x-icon" href="favicon.ico" />
  </head>
  <body>
    <app-root></app-root>
  </body>
</html>
```

**Note:** Angular CLI automatically injects script and style tags during build.

---

## 4. Implementation Plan

### Phase 1: Core Scaffolding (MVP)

1. Add `FrameworkType.ANGULAR` and `FrameworkType.ANGULAR_CLI` to enum
2. Create `FrameworkTemplate` configuration
3. Create template files in `src/py/litestar_vite/templates/angular/`
4. Test scaffolding with `litestar vite init --framework angular`

### Phase 2: Build Integration

1. Verify `litestar-vite-plugin` works with Angular builds
2. Test HMR with Angular components
3. Ensure production build outputs to correct directory

### Phase 3: Documentation & Examples

1. Add Angular section to documentation
2. Create `examples/angular/` working example
3. Update README with Angular support

### Phase 4: Optional SSR (Future)

1. Add AnalogJS SSR configuration
2. Create Nitro -> Litestar proxy setup
3. Document SSR deployment patterns

---

## 5. Testing Strategy

### 5.1 Unit Tests

```python
def test_angular_template_exists():
    """Verify Angular template is registered."""
    from litestar_vite.scaffolding.templates import FrameworkType, get_template

    template = get_template(FrameworkType.ANGULAR)
    assert template is not None
    assert template.name == "Angular (Analog)"
    assert template.vite_plugin == "@analogjs/vite-plugin-angular"


def test_angular_scaffolding_generates_files(tmp_path):
    """Verify all required files are generated."""
    from litestar_vite.scaffolding.generator import generate_project, TemplateContext
    from litestar_vite.scaffolding.templates import get_template, FrameworkType

    template = get_template(FrameworkType.ANGULAR)
    context = TemplateContext(project_name="test-angular", framework=template)

    files = generate_project(tmp_path, context)

    assert (tmp_path / "vite.config.ts").exists()
    assert (tmp_path / "src" / "main.ts").exists()
    assert (tmp_path / "src" / "app" / "app.component.ts").exists()
```

### 5.2 Integration Tests

1. Scaffold Angular project
2. Run `npm install`
3. Run `npm run dev` - verify Vite starts
4. Run `npm run build` - verify production build succeeds
5. Verify assets appear in bundle directory

### 5.3 Manual Testing Checklist

- [ ] `litestar vite init --framework angular` works
- [ ] Vite dev server starts with HMR
- [ ] Angular component changes trigger hot reload
- [ ] Production build generates correct assets
- [ ] Litestar serves built assets correctly
- [ ] API proxy works in development

---

## 6. Dependencies

### 6.1 NPM Packages

| Package | Version | Purpose |
|---------|---------|---------|
| `@angular/core` | ^18.0.0 | Angular framework |
| `@angular/common` | ^18.0.0 | Common utilities |
| `@angular/platform-browser` | ^18.0.0 | Browser platform |
| `@angular/router` | ^18.0.0 | Routing |
| `@analogjs/vite-plugin-angular` | ^1.0.0 | Vite compilation |
| `@analogjs/platform` | ^1.0.0 | Platform utilities |
| `rxjs` | ^7.8.0 | Reactive extensions |
| `zone.js` | ^0.14.0 | Change detection |

### 6.2 Version Compatibility Matrix

| Angular | AnalogJS | Vite | Node.js |
|---------|----------|------|---------|
| 18.x | 1.x | 5.x, 6.x | 18.x, 20.x |
| 19.x | 1.x | 6.x | 20.x, 22.x |
| 20.x | 2.x | 6.x, 7.x | 20.x, 22.x |

---

## 7. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| AnalogJS breaking changes | Medium | High | Pin to stable versions, test upgrades |
| Angular version fragmentation | Medium | Medium | Support Angular 18+ only |
| Zone.js complexity | Low | Low | Document zoneless option for future |
| Bundle size concerns | Low | Low | Document optimization strategies |

---

## 8. Success Metrics

1. **Scaffolding works:** `litestar vite init --framework angular` creates runnable project
2. **Dev workflow works:** HMR functional, API proxy working
3. **Production build works:** Assets correctly bundled and served
4. **Documentation complete:** Users can follow guide start-to-finish

---

## 9. Open Questions

1. Should we support Angular 17 or start with 18+?
2. Should SSR be included in v1 or deferred?
3. Should we include `@angular/forms` in default dependencies?
4. Should TailwindCSS addon work with Angular?

---

## 10. References

- [AnalogJS Documentation](https://analogjs.org/)
- [AnalogJS Vite Plugin](https://analogjs.org/docs/packages/vite-plugin-angular/overview)
- [Angular Build System](https://angular.dev/tools/cli/build)
- [Angular Standalone Components](https://angular.dev/guide/components)
- [litestar-vite Scaffolding](../../../src/py/litestar_vite/scaffolding/)

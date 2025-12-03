# Example Applications

This directory contains example applications demonstrating litestar-vite integration with various frontend frameworks. All examples share a consistent backend API and UI design to make it easy to compare frameworks.

## Commands (per example)

- `dev` – start Vite dev server
- `build` – type-check (where applicable) + Vite build
- `preview`/`serve` – preview built assets
- `generate-types` – run @hey-api/openapi-ts using the example’s `hey-api.config.ts`

Type generation defaults:

- OpenAPI input: `./src/generated/openapi.json`
- Output: `./src/generated`
- Client: axios
- Zod: off by default. To enable, set `schemas.type = "zod"` in `hey-api.config.ts` and install `zod`.

## Requirements for Examples

Every example **MUST** follow these requirements to maintain consistency across the project.

### Backend Requirements

#### 1. Library Controller API

All examples must implement the same "Library" backend with these endpoints:

```python
from litestar import Controller, get
from msgspec import Struct

class Book(Struct):
    id: int
    title: str
    author: str
    year: int
    tags: list[str]

class Summary(Struct):
    app: str
    headline: str
    total_books: int
    featured: Book

BOOKS: list[Book] = [
    Book(id=1, title="Async Python", author="C. Developer", year=2024, tags=["python", "async"]),
    Book(id=2, title="Type-Safe Web", author="J. Dev", year=2025, tags=["typescript", "api"]),
    Book(id=3, title="Frontend Patterns", author="A. Designer", year=2023, tags=["frontend", "ux"]),
]

class LibraryController(Controller):
    @get("/api/summary")
    async def summary(self) -> Summary:
        return Summary(
            app="litestar-vite library",
            headline="One backend, many frontends",
            total_books=len(BOOKS),
            featured=BOOKS[0],
        )

    @get("/api/books")
    async def books(self) -> list[Book]:
        return BOOKS

    @get("/api/books/{book_id:int}")
    async def book_detail(self, book_id: int) -> Book:
        # Return book or raise NotFoundException
        ...
```

#### 2. App Configuration

```python
from litestar import Litestar
from litestar_vite import ViteConfig, VitePlugin, PathConfig

vite = VitePlugin(config=ViteConfig(
    dev_mode=DEV_MODE,
    paths=PathConfig(root=here),
))

app = Litestar(
    route_handlers=[LibraryController],
    plugins=[vite],
    debug=True,
)
```

### Frontend Requirements

#### 1. Styling: Tailwind CSS v4

All examples must use Tailwind CSS v4 with this base configuration:

**`app.css` / `style.css` / `global.css`:**

```css
@import "tailwindcss";

:root {
  font-family: "Inter", "SF Pro Text", system-ui, -apple-system, sans-serif;
  color: #202235;
  background-color: #f8fafc;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
}
```

**`vite.config.ts`:**

```typescript
import tailwindcss from "@tailwindcss/vite"

export default defineConfig({
  plugins: [
    tailwindcss(),
    // ... framework plugin
  ],
})
```

#### 2. UI Components

All examples must implement this exact UI structure:

##### Header

```html
<header class="space-y-2">
  <p class="font-semibold text-[#edb641] text-sm uppercase tracking-[0.14em]">
    Litestar · Vite
  </p>
  <h1 class="font-semibold text-3xl text-[#202235]">
    Library ({Framework Name})
  </h1>
  <p class="max-w-3xl text-slate-600">
    Same API, different frontend. {Framework description}.
  </p>
  <!-- Navigation tabs -->
</header>
```

##### Navigation Tabs

```html
<nav class="inline-flex gap-2 rounded-full bg-slate-100 p-1 shadow-sm" aria-label="Views">
  <button class="rounded-full px-4 py-2 font-semibold text-sm transition {active ? 'bg-white text-[#202235] shadow' : 'text-slate-600'}">
    Overview
  </button>
  <button class="rounded-full px-4 py-2 font-semibold text-sm transition {active ? 'bg-white text-[#202235] shadow' : 'text-slate-600'}">
    Books ({count})  <!-- Must show book count from API -->
  </button>
</nav>
```

##### Overview Section (when Overview tab active)

```html
<section class="space-y-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-200/40">
  <h2 class="font-semibold text-[#202235] text-xl">{headline}</h2>
  <p class="text-slate-600">Featured book</p>
  <article class="rounded-xl border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-4">
    <h3 class="font-semibold text-[#202235] text-lg">{title}</h3>
    <p class="mt-1 text-slate-600">{author} • {year}</p>
    <p class="mt-1 text-[#202235] text-sm">{tags}</p>
  </article>
</section>
```

##### Books Grid (when Books tab active)

```html
<section class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="Books">
  <!-- For each book -->
  <article class="rounded-xl border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-4 shadow-sm">
    <h3 class="font-semibold text-[#202235] text-lg">{title}</h3>
    <p class="mt-1 text-slate-600">{author} • {year}</p>
    <p class="mt-1 text-[#202235] text-sm">{tags}</p>
  </article>
</section>
```

##### Footer with Routes

```html
<footer class="border-slate-200 border-t pt-8 text-slate-400 text-xs">
  <details>
    <summary class="cursor-pointer">Server Routes (from generated routes.json)</summary>
    <div class="mt-2 grid grid-cols-1 gap-1 sm:grid-cols-2">
      <!-- For each route -->
      <span class="font-mono text-slate-600">{name} → {uri}</span>
    </div>
  </details>
</footer>
```

#### 3. Main Container

Wrap everything in:

```html
<main class="mx-auto max-w-5xl space-y-6 px-4 py-10">
  <!-- content -->
</main>
```

#### 4. Loading States

Show "Loading..." text while data is being fetched:

```html
<div class="text-slate-600">Loading...</div>
```

### Color Palette

| Element | Color |
|---------|-------|
| Eyebrow text | `#edb641` (yellow) |
| Headings | `#202235` (dark blue) |
| Body text | `text-slate-600` |
| Muted text | `text-slate-400` |
| Background | `#f8fafc` (light gray) |
| Cards | `bg-white` to `bg-slate-50` gradient |
| Borders | `border-slate-200` |

### Framework-Specific Notes

#### SvelteKit

- Use Svelte 5 syntax (`$state`, `$derived`, `$props`)
- Layout must use `{@render children()}` not `<slot />`
- tsconfig.json must extend `./.svelte-kit/tsconfig.json`

#### Nuxt

- Use `useFetch` for data loading
- Use Vue 3 Composition API with `<script setup>`

#### Astro

- Use client-side JavaScript for interactivity
- TypeScript types in `<script>` blocks

#### React

- Use functional components with hooks
- Use React Router for URL-based navigation (optional)

#### Vue

- Use Composition API with `<script setup lang="ts">`
- No scoped styles - use Tailwind classes only

#### Svelte (SPA)

- Use Svelte 5 runes (`$state`, `$derived`)
- Use `let` not `const` for `$state` variables that are reassigned

### File Structure

```
examples/{example-name}/
├── app.py                 # Litestar application with LibraryController
├── package.json           # NPM dependencies
├── vite.config.ts         # Vite configuration with Tailwind
├── tsconfig.json          # TypeScript configuration
├── src/                   # Frontend source (structure varies by framework)
│   ├── app.css           # Tailwind imports
│   └── ...
└── .gitignore
```

### Testing an Example

1. Install dependencies:

   ```bash
   cd examples/{example-name}
   npm install
   ```

2. Run the development server:

   ```bash
   uv run litestar --app-dir examples/{example-name} run
   ```

3. Verify:
   - [ ] Page loads without errors
   - [ ] Overview tab shows featured book
   - [ ] Books tab shows all books with count in tab
   - [ ] Tab switching works
   - [ ] Footer shows server routes
   - [ ] Styling matches other examples exactly

### Creating a New Example

1. Copy the closest existing example as a starting point
2. Update `app.py` with the LibraryController (can copy from any example)
3. Implement the frontend following the UI requirements above
4. Ensure all Tailwind classes match exactly
5. Test thoroughly against the checklist above
6. Add the example to `src/py/litestar_vite/scaffolding/templates.py` if it should be scaffoldable

### Updating Existing Examples

When updating examples:

1. Make the same change across ALL examples
2. Verify visual consistency by running multiple examples side-by-side
3. Run `npm run build` to ensure TypeScript compiles
4. Test each example individually

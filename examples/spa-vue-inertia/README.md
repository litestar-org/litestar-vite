# Vue 3 + Inertia.js + Litestar Example

This example demonstrates building a modern SPA with server-side routing using Vue 3, Inertia.js, and Litestar.

## Features

- Vue 3 with Composition API
- Inertia.js for server-side routing
- No separate API layer needed
- TypeScript support
- Hot Module Replacement (HMR)

## What is Inertia.js?

Inertia.js is the glue between your server-side framework and client-side framework. It allows you to:

- Build fully client-rendered SPAs
- Use server-side routing (no Vue Router needed)
- Share data between server and client seamlessly
- Maintain SEO-friendly URLs

## Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- uv (Python package manager)

### Installation

1. Install Python dependencies:
   ```bash
   cd examples/spa-vue-inertia
   uv pip install litestar litestar-vite jinja2
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

## Development

1. Start the Vite dev server (in one terminal):
   ```bash
   npm run dev
   ```

2. Start Litestar (in another terminal):
   ```bash
   litestar run --reload
   ```

3. Open http://localhost:8000 in your browser

## How It Works

### Server-Side (Python)

Routes return `InertiaResponse` with a component name and props:

```python
@get("/")
async def home() -> InertiaResponse:
    return InertiaResponse(
        component="Home",
        props={"message": "Hello!"},
    )
```

### Client-Side (Vue)

Pages are Vue components that receive props:

```vue
<script setup lang="ts">
defineProps<{
  message: string
}>()
</script>

<template>
  <div>{{ message }}</div>
</template>
```

## Project Structure

```
spa-vue-inertia/
├── app.py                 # Litestar backend with Inertia
├── package.json           # Node.js dependencies
├── vite.config.ts         # Vite configuration
├── templates/
│   └── index.html         # Root Jinja template
├── resources/
│   ├── main.ts            # Vue/Inertia entry
│   ├── style.css          # Global styles
│   └── pages/             # Inertia page components
│       ├── Home.vue
│       ├── About.vue
│       └── Users.vue
└── public/                # Build output
```

## Adding New Pages

1. Create a route in `app.py`:
   ```python
   @get("/new-page")
   async def new_page() -> InertiaResponse:
       return InertiaResponse(
           component="NewPage",
           props={"data": "value"},
       )
   ```

2. Create the Vue component in `resources/pages/NewPage.vue`

3. Navigate using Inertia's `Link` component:
   ```vue
   <Link href="/new-page">Go to New Page</Link>
   ```

## Learn More

- [Inertia.js Documentation](https://inertiajs.com/)
- [Vue 3 Documentation](https://vuejs.org/)
- [Litestar Vite Inertia Docs](/usage/inertia)

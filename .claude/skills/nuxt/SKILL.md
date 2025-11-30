---
name: nuxt
description: Expert knowledge for Nuxt 3 development. Use when building Nuxt apps with Litestar API backend, server routes, or composables.
---

# Nuxt 3 Framework Skill

## Quick Reference

### Nuxt Configuration

```typescript
// nuxt.config.ts
export default defineNuxtConfig({
  devtools: { enabled: true },
  ssr: false, // SPA mode for Litestar integration
  nitro: {
    devProxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

### Composables for API

```typescript
// composables/useApi.ts
export function useApi<T>(endpoint: string) {
  return useFetch<T>(`/api${endpoint}`, {
    baseURL: useRuntimeConfig().public.apiBase,
  });
}

// Usage in component
const { data: items, pending, error } = await useApi<Item[]>('/items');
```

### Page Components

```vue
<!-- pages/index.vue -->
<script setup lang="ts">
const { data: items } = await useApi<Item[]>('/items');
</script>

<template>
  <div>
    <h1>Items</h1>
    <ul>
      <li v-for="item in items" :key="item.id">
        {{ item.name }}
      </li>
    </ul>
  </div>
</template>
```

### Server API Routes

```typescript
// server/api/proxy/[...path].ts
export default defineEventHandler(async (event) => {
  const path = event.context.params?.path || '';
  const target = `http://localhost:8000/api/${path}`;

  return await $fetch(target, {
    method: event.method,
    headers: getHeaders(event),
    body: event.method !== 'GET' ? await readBody(event) : undefined,
  });
});
```

### Litestar Backend

```python
from litestar import Litestar, get
from litestar_vite import VitePlugin, ViteConfig

@get("/api/items")
async def get_items() -> list[dict]:
    return [{"id": 1, "name": "Item 1"}]

app = Litestar(
    route_handlers=[get_items],
    plugins=[
        VitePlugin(
            config=ViteConfig(
                dev_mode=True,
                # Nuxt runs on its own dev server
                is_react=False,
            ),
        ),
    ],
)
```

### Auto-imports

```typescript
// Nuxt auto-imports these
// No need to import manually:
// - ref, computed, watch from vue
// - useFetch, useRoute, useRouter from nuxt
// - Custom composables from composables/

const route = useRoute();
const items = ref<Item[]>([]);
```

## Project-Specific Patterns

- SPA mode (`ssr: false`) for Litestar integration
- Use `devProxy` to forward API requests
- TypeScript with strict mode
- Composition API style

## Context7 Lookup

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/nuxt/nuxt",
    topic="configuration composables fetch",
    mode="code"
)
```

## Related Files

- `examples/nuxt/` - Nuxt example
- `src/py/litestar_vite/templates/nuxt/` - Nuxt templates

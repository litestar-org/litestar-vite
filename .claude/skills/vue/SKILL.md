---
name: vue
description: Expert knowledge for Vue 3 development with TypeScript. Use when building Vue components, Composition API, or integrating with Litestar/Vite.
---

# Vue 3 Framework Skill

## Quick Reference

### Composition API Components

```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';

interface Props {
  title: string;
  items: Item[];
}

const props = defineProps<Props>();
const emit = defineEmits<{
  select: [item: Item];
}>();

const selected = ref<Item | null>(null);
const filteredItems = computed(() =>
  props.items.filter(item => item.active)
);

function handleSelect(item: Item) {
  selected.value = item;
  emit('select', item);
}

onMounted(() => {
  console.log('Component mounted');
});
</script>

<template>
  <div>
    <h2>{{ title }}</h2>
    <ul>
      <li
        v-for="item in filteredItems"
        :key="item.id"
        @click="handleSelect(item)"
      >
        {{ item.name }}
      </li>
    </ul>
  </div>
</template>
```

### API Integration with Litestar

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue';
import type { Item } from './generated/api';

const items = ref<Item[]>([]);
const loading = ref(true);

async function fetchItems() {
  try {
    const response = await fetch('/api/items');
    items.value = await response.json();
  } finally {
    loading.value = false;
  }
}

onMounted(fetchItems);
</script>
```

### Vue with Inertia.js

```typescript
// main.ts
import { createApp, h } from 'vue';
import { createInertiaApp } from '@inertiajs/vue3';

createInertiaApp({
  resolve: (name) => {
    const pages = import.meta.glob('./pages/**/*.vue', { eager: true });
    return pages[`./pages/${name}.vue`];
  },
  setup({ el, App, props, plugin }) {
    createApp({ render: () => h(App, props) })
      .use(plugin)
      .mount(el);
  },
});
```

### Vite + Vue Setup

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { litestarVitePlugin } from 'litestar-vite-plugin';

export default defineConfig({
  plugins: [
    vue(),
    litestarVitePlugin({ input: ['src/main.ts'] }),
  ],
});
```

## Project-Specific Patterns

- Use `<script setup>` syntax
- TypeScript with strict mode
- Composition API (not Options API)
- Entry point: `src/main.ts`

## Context7 Lookup

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/vuejs/core",
    topic="composition api typescript",
    mode="code"
)
```

## Related Files

- `examples/vue/` - Vue SPA example
- `examples/vue-inertia/` - Vue + Inertia example
- `src/py/litestar_vite/templates/vue/` - Vue templates

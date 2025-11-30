# Vue Context

Expert knowledge for Vue 3 with Litestar Vite. Reference when building Vue SPAs, components, or integrating with Inertia.js.

## Quick Reference

### App Setup with Vite

```typescript
// src/main.ts
import { createApp } from 'vue';
import App from './App.vue';
import './style.css';

createApp(App).mount('#app');
```

### Inertia.js Integration

```typescript
// src/main.ts
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

### Page Component

```vue
<script setup lang="ts">
import { Head, Link } from '@inertiajs/vue3';

interface Props {
  items: Item[];
  user: User;
}

defineProps<Props>();
</script>

<template>
  <Head title="Items" />
  <h1>Welcome, {{ user.name }}</h1>
  <ul>
    <li v-for="item in items" :key="item.id">
      <Link :href="`/items/${item.id}`">{{ item.name }}</Link>
    </li>
  </ul>
</template>
```

### Form Handling with Inertia

```vue
<script setup lang="ts">
import { useForm } from '@inertiajs/vue3';

const form = useForm({
  name: '',
  description: '',
});

function submit() {
  form.post('/items');
}
</script>

<template>
  <form @submit.prevent="submit">
    <input v-model="form.name" type="text" />
    <span v-if="form.errors.name">{{ form.errors.name }}</span>
    <button type="submit" :disabled="form.processing">Create</button>
  </form>
</template>
```

### Composition API Pattern

```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';

const items = ref<Item[]>([]);
const loading = ref(true);

const activeItems = computed(() =>
  items.value.filter((item) => item.active)
);

onMounted(async () => {
  items.value = await fetchItems();
  loading.value = false;
});

function addItem(item: Item) {
  items.value.push(item);
}
</script>
```

### Pinia Store (if needed)

```typescript
// stores/items.ts
import { defineStore } from 'pinia';

export const useItemsStore = defineStore('items', {
  state: () => ({
    items: [] as Item[],
    loading: false,
  }),
  actions: {
    async fetchItems() {
      this.loading = true;
      this.items = await api.getItems();
      this.loading = false;
    },
  },
});
```

## Vite Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { litestarVitePlugin } from 'litestar-vite-plugin';

export default defineConfig({
  plugins: [
    vue(),
    litestarVitePlugin({
      input: 'src/main.ts',
    }),
  ],
});
```

## Context7 Lookup

```python
mcp__context7__resolve-library-id(libraryName="vue")
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/vuejs/core",
    topic="composition api reactivity components",
    mode="code"
)
```

## Related Files

- `examples/vue/` - Vue SPA example
- `examples/vue-inertia/` - Vue + Inertia example
- `src/py/litestar_vite/templates/vue/` - Vue scaffolding templates

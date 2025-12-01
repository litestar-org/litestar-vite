---
name: svelte
description: Expert knowledge for Svelte 5 development. Use when building Svelte components, using runes, or integrating with SvelteKit and Litestar.
---

# Svelte 5 Framework Skill

## Quick Reference

### Svelte 5 Runes

```svelte
<script lang="ts">
  interface Props {
    title: string;
    items: Item[];
    onSelect?: (item: Item) => void;
  }

  let { title, items, onSelect }: Props = $props();

  let selected = $state<Item | null>(null);
  let filteredItems = $derived(items.filter(i => i.active));

  function handleSelect(item: Item) {
    selected = item;
    onSelect?.(item);
  }

  $effect(() => {
    console.log('Selected changed:', selected);
  });
</script>

<div>
  <h2>{title}</h2>
  <ul>
    {#each filteredItems as item (item.id)}
      <li onclick={() => handleSelect(item)}>
        {item.name}
      </li>
    {/each}
  </ul>
</div>
```

### API Integration with Litestar

```svelte
<script lang="ts">
  import type { Item } from './generated/api';

  let items = $state<Item[]>([]);
  let loading = $state(true);

  async function fetchItems() {
    try {
      const response = await fetch('/api/items');
      items = await response.json();
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    fetchItems();
  });
</script>

{#if loading}
  <p>Loading...</p>
{:else}
  <ul>
    {#each items as item}
      <li>{item.name}</li>
    {/each}
  </ul>
{/if}
```

### Vite + Svelte Setup

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { litestarVitePlugin } from 'litestar-vite-plugin';

export default defineConfig({
  plugins: [
    svelte(),
    litestarVitePlugin({ input: ['src/main.ts'] }),
  ],
});
```

### Svelte with Inertia.js

```typescript
// main.ts
import { createInertiaApp } from '@inertiajs/svelte';
import { mount } from 'svelte';

createInertiaApp({
  resolve: (name) => {
    const pages = import.meta.glob('./pages/**/*.svelte', { eager: true });
    return pages[`./pages/${name}.svelte`];
  },
  setup({ el, App }) {
    mount(App, { target: el });
  },
});
```

### SvelteKit Integration

```typescript
// svelte.config.js
import adapter from '@sveltejs/adapter-static';

export default {
  kit: {
    adapter: adapter({
      fallback: 'index.html',
    }),
  },
};
```

## Project-Specific Patterns

- Use Svelte 5 runes (`$state`, `$derived`, `$effect`, `$props`)
- TypeScript with strict mode
- Entry point: `src/main.ts`

## Context7 Lookup

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/sveltejs/svelte",
    topic="runes state reactivity",
    mode="code"
)
```

## Related Files

- `examples/svelte/` - Svelte SPA example
- `examples/sveltekit/` - SvelteKit example
- `src/py/litestar_vite/templates/svelte/` - Svelte templates

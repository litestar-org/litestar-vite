# Svelte Context

Expert knowledge for Svelte 5 with Litestar Vite. Reference when building Svelte SPAs, components, or integrating with SvelteKit.

## Quick Reference

### App Setup with Vite

```typescript
// src/main.ts
import App from './App.svelte';
import './app.css';

const app = new App({
  target: document.getElementById('app')!,
});

export default app;
```

### Svelte 5 Runes (Modern Pattern)

```svelte
<script lang="ts">
  interface Props {
    items: Item[];
    user: User;
  }

  let { items, user }: Props = $props();

  let count = $state(0);
  let doubled = $derived(count * 2);

  function increment() {
    count++;
  }
</script>

<h1>Welcome, {user.name}</h1>
<p>Count: {count}, Doubled: {doubled}</p>
<button onclick={increment}>Increment</button>

<ul>
  {#each items as item (item.id)}
    <li>{item.name}</li>
  {/each}
</ul>
```

### Svelte 5 Effects

```svelte
<script lang="ts">
  let count = $state(0);

  $effect(() => {
    console.log(`Count changed to ${count}`);
    // Cleanup function (optional)
    return () => {
      console.log('Cleanup');
    };
  });
</script>
```

### Form Handling

```svelte
<script lang="ts">
  let name = $state('');
  let description = $state('');
  let submitting = $state(false);

  async function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    submitting = true;
    await fetch('/api/items', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    });
    submitting = false;
  }
</script>

<form onsubmit={handleSubmit}>
  <input bind:value={name} type="text" />
  <textarea bind:value={description}></textarea>
  <button type="submit" disabled={submitting}>Create</button>
</form>
```

### Component with Slots

```svelte
<!-- Card.svelte -->
<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    title: string;
    children: Snippet;
    footer?: Snippet;
  }

  let { title, children, footer }: Props = $props();
</script>

<div class="card">
  <h2>{title}</h2>
  <div class="content">
    {@render children()}
  </div>
  {#if footer}
    <div class="footer">
      {@render footer()}
    </div>
  {/if}
</div>
```

### SvelteKit Integration

```typescript
// src/routes/items/+page.ts
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
  const response = await fetch('/api/items');
  const items = await response.json();
  return { items };
};
```

## Vite Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { litestarVitePlugin } from 'litestar-vite-plugin';

export default defineConfig({
  plugins: [
    svelte(),
    litestarVitePlugin({
      input: 'src/main.ts',
    }),
  ],
});
```

## Context7 Lookup

```python
mcp__context7__resolve-library-id(libraryName="svelte")
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/sveltejs/svelte",
    topic="runes state reactivity components",
    mode="code"
)
```

## Related Files

- `examples/svelte/` - Svelte SPA example
- `examples/sveltekit/` - SvelteKit + Litestar example
- `src/py/litestar_vite/templates/svelte/` - Svelte scaffolding templates

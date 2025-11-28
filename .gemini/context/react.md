# React Context

Expert knowledge for React with Litestar Vite. Reference when building React SPAs, components, or integrating with Inertia.js.

## Quick Reference

### App Setup with Vite

```tsx
// src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

### Inertia.js Integration

```tsx
// src/main.tsx
import { createInertiaApp } from '@inertiajs/react';
import { createRoot } from 'react-dom/client';

createInertiaApp({
  resolve: (name) => {
    const pages = import.meta.glob('./pages/**/*.tsx', { eager: true });
    return pages[`./pages/${name}.tsx`];
  },
  setup({ el, App, props }) {
    createRoot(el).render(<App {...props} />);
  },
});
```

### Page Component

```tsx
import { Head, Link, usePage } from '@inertiajs/react';

interface Props {
  items: Item[];
  user: User;
}

export default function ItemsIndex({ items, user }: Props) {
  return (
    <>
      <Head title="Items" />
      <h1>Welcome, {user.name}</h1>
      <ul>
        {items.map((item) => (
          <li key={item.id}>
            <Link href={`/items/${item.id}`}>{item.name}</Link>
          </li>
        ))}
      </ul>
    </>
  );
}
```

### Form Handling with Inertia

```tsx
import { useForm } from '@inertiajs/react';

export default function CreateItem() {
  const { data, setData, post, processing, errors } = useForm({
    name: '',
    description: '',
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    post('/items');
  }

  return (
    <form onSubmit={submit}>
      <input
        type="text"
        value={data.name}
        onChange={(e) => setData('name', e.target.value)}
      />
      {errors.name && <span>{errors.name}</span>}
      <button type="submit" disabled={processing}>
        Create
      </button>
    </form>
  );
}
```

### Hooks Pattern

```tsx
import { useState, useEffect, useCallback } from 'react';

function useItems() {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchItems().then((data) => {
      setItems(data);
      setLoading(false);
    });
  }, []);

  const addItem = useCallback((item: Item) => {
    setItems((prev) => [...prev, item]);
  }, []);

  return { items, loading, addItem };
}
```

## Vite Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { litestarVitePlugin } from 'litestar-vite-plugin';

export default defineConfig({
  plugins: [
    react(),
    litestarVitePlugin({
      input: 'src/main.tsx',
    }),
  ],
});
```

## Context7 Lookup

```python
mcp__context7__resolve-library-id(libraryName="react")
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/facebook/react",
    topic="hooks components state",
    mode="code"
)
```

## Related Files

- `examples/spa-react/` - React SPA example
- `examples/inertia/` - React + Inertia example
- `src/py/litestar_vite/templates/react/` - React scaffolding templates

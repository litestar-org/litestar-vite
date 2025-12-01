---
name: react
description: Expert knowledge for React 18+ development with TypeScript. Use when building React components, managing state, or integrating with Litestar/Vite.
---

# React Framework Skill

## Quick Reference

### Component Patterns

```tsx
import { useState, useEffect } from 'react';

interface Props {
  title: string;
  items: Item[];
  onSelect?: (item: Item) => void;
}

export function ItemList({ title, items, onSelect }: Props) {
  const [selected, setSelected] = useState<Item | null>(null);

  const handleSelect = (item: Item) => {
    setSelected(item);
    onSelect?.(item);
  };

  return (
    <div>
      <h2>{title}</h2>
      <ul>
        {items.map(item => (
          <li key={item.id} onClick={() => handleSelect(item)}>
            {item.name}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### API Integration with Litestar

```tsx
// Using generated types from litestar-vite
import type { paths } from './generated/api';

async function fetchItems(): Promise<Item[]> {
  const response = await fetch('/api/items');
  if (!response.ok) throw new Error('Failed to fetch');
  return response.json();
}

export function useItems() {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchItems()
      .then(setItems)
      .finally(() => setLoading(false));
  }, []);

  return { items, loading };
}
```

### Vite + React Setup

```tsx
// main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### React with Inertia.js

```tsx
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

## Project-Specific Patterns

- Entry point: `src/main.tsx`
- Generated types: `src/generated/api.ts`
- Use functional components with hooks
- TypeScript strict mode enabled

## Context7 Lookup

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/facebook/react",
    topic="hooks components typescript",
    mode="code"
)
```

## Related Files

- `examples/react/` - React SPA example
- `examples/vue-inertia/` - React + Inertia example
- `src/py/litestar_vite/templates/react/` - React templates

---
name: angular
description: Expert knowledge for Angular 18+ with Vite. Use when building Angular components, services, or integrating with Litestar backend.
---

# Angular Framework Skill

## Quick Reference

### Standalone Components

```typescript
// app.component.ts
import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { inject } from '@angular/core';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule],
  template: `
    <h1>{{ title() }}</h1>
    <ul>
      @for (item of items(); track item.id) {
        <li>{{ item.name }}</li>
      }
    </ul>
  `,
})
export class AppComponent {
  private http = inject(HttpClient);

  title = signal('My App');
  items = signal<Item[]>([]);
  itemCount = computed(() => this.items().length);

  ngOnInit() {
    this.http.get<Item[]>('/api/items').subscribe(items => {
      this.items.set(items);
    });
  }
}
```

### Services

```typescript
// services/item.service.ts
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ItemService {
  private http = inject(HttpClient);

  getItems(): Observable<Item[]> {
    return this.http.get<Item[]>('/api/items');
  }

  createItem(item: ItemCreate): Observable<Item> {
    return this.http.post<Item>('/api/items', item);
  }
}
```

### Vite + Angular (Analog)

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import analog from '@analogjs/platform';
import { litestarVitePlugin } from 'litestar-vite-plugin';

export default defineConfig({
  plugins: [
    analog(),
    litestarVitePlugin({
      input: ['src/main.ts'],
    }),
  ],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

### Angular CLI (Non-Vite)

```json
// proxy.conf.json
{
  "/api": {
    "target": "http://localhost:8000",
    "secure": false,
    "changeOrigin": true
  }
}
```

```bash
ng serve --proxy-config proxy.conf.json
```

### Signals and Effects

```typescript
import { signal, computed, effect } from '@angular/core';

// Reactive state
const count = signal(0);
const doubled = computed(() => count() * 2);

// Side effects
effect(() => {
  console.log('Count changed:', count());
});

// Update
count.set(5);
count.update(c => c + 1);
```

### HTTP Interceptors

```typescript
// interceptors/auth.interceptor.ts
import { HttpInterceptorFn } from '@angular/common/http';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const token = localStorage.getItem('token');
  if (token) {
    req = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    });
  }
  return next(req);
};

// app.config.ts
export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(withInterceptors([authInterceptor])),
  ],
};
```

## Project-Specific Patterns

- Standalone components (no NgModules)
- Signals for reactive state
- `inject()` for dependency injection
- Angular 18+ with new control flow syntax

## Context7 Lookup

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/angular/angular",
    topic="signals components standalone",
    mode="code"
)
```

## Related Files

- `examples/angular/` - Angular + Vite example
- `examples/angular-cli/` - Angular CLI example
- `src/py/litestar_vite/templates/angular/` - Angular templates

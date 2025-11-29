---
name: vite
description: Expert knowledge for Vite build tool. Use when configuring Vite, creating plugins, managing HMR, or handling asset bundling.
---

# Vite Build Tool Skill

## Quick Reference

### Plugin Configuration

```typescript
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [myPlugin()],
  build: {
    manifest: true,
    outDir: 'public/dist',
    rollupOptions: {
      input: ['src/main.ts'],
    },
  },
  server: {
    origin: 'http://localhost:5173',
    cors: true,
  },
});
```

### Creating Vite Plugins

```typescript
import type { Plugin, ResolvedConfig } from 'vite';

export function myPlugin(options: PluginOptions = {}): Plugin {
  let config: ResolvedConfig;

  return {
    name: 'my-plugin',

    configResolved(resolvedConfig) {
      config = resolvedConfig;
    },

    configureServer(server) {
      // Dev server middleware
      server.middlewares.use((req, res, next) => {
        next();
      });
    },

    transformIndexHtml(html) {
      return html.replace('<!-- inject -->', '<script>...</script>');
    },
  };
}
```

### Hot Module Replacement

```typescript
// In client code
if (import.meta.hot) {
  import.meta.hot.accept('./module.ts', (newModule) => {
    // Handle update
  });
}

// In plugin
export function hmrPlugin(): Plugin {
  return {
    name: 'hmr-plugin',
    handleHotUpdate({ file, server }) {
      if (file.endsWith('.custom')) {
        server.ws.send({ type: 'full-reload' });
        return [];
      }
    },
  };
}
```

### Manifest Handling

```json
{
  "src/main.ts": {
    "file": "assets/main-abc123.js",
    "src": "src/main.ts",
    "isEntry": true,
    "css": ["assets/main-def456.css"]
  }
}
```

## Project-Specific Patterns

This project's Vite plugin (`litestarVitePlugin`):
- Generates manifest for Python asset loader
- Configures dev server for Litestar proxy
- Handles hot file creation for HMR detection

## Context7 Lookup

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/vitejs/vite",
    topic="plugin api configuration",
    mode="code"
)
```

## Related Files

- `src/js/src/index.ts` - Main Vite plugin
- `examples/*/vite.config.ts` - Example configurations
- `src/py/litestar_vite/loader.py` - Python manifest loader

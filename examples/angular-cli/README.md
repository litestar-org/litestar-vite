# Angular CLI + Litestar Example

This example demonstrates integrating Angular using Angular CLI (not Vite) with a Litestar backend.

## Overview

Unlike the Vite-based Angular example, this approach uses the standard Angular CLI tooling:
- `ng serve` for development with proxy configuration
- `ng build` for production builds
- Litestar serves static files from the `dist/browser/` output

## Trade-offs

| Aspect | Angular CLI | Vite-based |
|--------|-------------|------------|
| **Build Tool** | Angular CLI (webpack) | Vite + @analogjs |
| **HMR** | Angular CLI built-in | Vite HMR |
| **Dev Experience** | Standard Angular | Faster rebuilds |
| **Integration** | Proxy to Litestar | Single-port proxy |
| **manifest.json** | Not used | Used for assets |

## Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- uv (Python package manager)

### Installation

1. Install Python dependencies:
   ```bash
   cd examples/angular-cli
   uv pip install litestar
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

### Development

1. Start the Litestar backend (in one terminal):
   ```bash
   litestar run --reload
   ```

2. Start Angular dev server (in another terminal):
   ```bash
   npm start
   ```

3. Open http://localhost:4200 in your browser

The Angular CLI dev server proxies API requests to Litestar running on port 8000.

### Production Build

1. Build the Angular app:
   ```bash
   npm run build
   ```

2. Run Litestar (serves static files):
   ```bash
   litestar run
   ```

3. Open http://localhost:8000

## Project Structure

```
angular-cli/
├── app.py                 # Litestar backend
├── angular.json           # Angular CLI configuration
├── proxy.conf.json        # Dev server proxy config
├── package.json           # Node.js dependencies
├── tsconfig.json          # TypeScript config
├── tsconfig.app.json      # App-specific TS config
├── src/
│   ├── index.html         # Entry HTML
│   ├── main.ts            # Angular bootstrap
│   ├── styles.css         # Global styles
│   └── app/
│       ├── app.component.ts
│       ├── app.component.html
│       ├── app.component.css
│       ├── app.config.ts
│       ├── app.routes.ts
│       └── home.component.ts
└── dist/                  # Build output (gitignored)
    └── browser/
```

## Notes

- This approach does NOT use litestar-vite-plugin
- The manifest.json-based asset loading is not available
- API proxy is configured in `proxy.conf.json` for development
- In production, Litestar serves the static build output

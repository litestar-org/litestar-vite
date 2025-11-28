# Vue 3 + Litestar Vite Example

This example demonstrates integrating Vue 3 with Litestar using the litestar-vite plugin.

## Features

- Vue 3 with Composition API
- Single File Components (SFC)
- TypeScript support
- Hot Module Replacement (HMR)
- API integration with Litestar backend

## Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- uv (Python package manager)

### Installation

1. Install Python dependencies:
   ```bash
   cd examples/spa-vue
   uv pip install litestar litestar-vite jinja2
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

## Development

1. Start the Vite dev server (in one terminal):
   ```bash
   npm run dev
   ```

2. Start Litestar (in another terminal):
   ```bash
   litestar run --reload
   ```

3. Open http://localhost:8000 in your browser

## Production Build

1. Build the frontend:
   ```bash
   npm run build
   ```

2. Update `app.py` to set `dev_mode=False`

3. Run Litestar:
   ```bash
   litestar run
   ```

## Project Structure

```
spa-vue/
├── app.py                 # Litestar backend
├── package.json           # Node.js dependencies
├── vite.config.ts         # Vite configuration
├── tsconfig.json          # TypeScript config
├── index.html             # Entry HTML for Vite
├── templates/
│   └── index.html         # Jinja template
├── src/
│   ├── main.ts            # Vue app entry
│   ├── App.vue            # Root component
│   ├── style.css          # Global styles
│   └── components/
│       ├── Counter.vue    # Counter component
│       └── UserList.vue   # User list component
└── public/                # Build output
```

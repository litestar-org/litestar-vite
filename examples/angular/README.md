# Angular + Litestar Vite Example

This example demonstrates using Angular 18+ with Vite and the litestar-vite plugin.

## Features

- Angular 18+ with standalone components
- Vite-based build with `@analogjs/vite-plugin-angular`
- Single-port proxy mode (all requests through Litestar)
- Hot Module Replacement (HMR) support
- TypeScript with strict mode

## Setup

1. Install Python dependencies:
   ```bash
   uv pip install litestar litestar-vite
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   # In one terminal, start Litestar
   litestar run --reload

   # In another terminal, start Vite
   npm run dev
   ```

4. Open http://localhost:8000 in your browser

## Production Build

```bash
npm run build
litestar run
```

## Project Structure

```
angular/
├── app.py              # Litestar application
├── package.json        # Node.js dependencies
├── vite.config.ts      # Vite configuration
├── tsconfig.json       # TypeScript configuration
├── index.html          # HTML entry point
├── public/             # Static assets (output)
└── src/
    ├── main.ts         # Angular bootstrap
    ├── styles.css      # Global styles
    └── app/
        ├── app.component.ts
        ├── app.component.html
        ├── app.component.css
        ├── app.config.ts
        ├── app.routes.ts
        └── home.component.ts
```

## API Endpoints

- `GET /api/hello` - Returns a greeting message
- `GET /api/data` - Returns sample data

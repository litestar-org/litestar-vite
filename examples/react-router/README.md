# React + React Router 7

SPA mode (`mode="spa"`) with React Router 7's **data router** API
(`createBrowserRouter` + `loader` + `useLoaderData`). The Litestar plugin
serves the SPA shell from `index.html` for any non-API route.

## Differences vs `examples/react`

| | `examples/react` | `examples/react-router` |
|---|---|---|
| Router API | `<Routes>` + `<Route>` (declarative) | `createBrowserRouter` + `loader` (data router) |
| Data fetching | `useEffect` in components | Route loaders (parallel with navigation) |
| Goal | Demonstrate `routes.ts` codegen | Demonstrate React Router 7's data API |

Both run as single-port SPAs through the Litestar/Vite pipeline; pick the
one that matches your routing pattern.

## Run

```bash
litestar --app-dir examples/react-router run
```

Production:

```bash
VITE_DEV_MODE=false litestar --app-dir examples/react-router run
```

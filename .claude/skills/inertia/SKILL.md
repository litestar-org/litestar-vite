---
name: inertia
description: Expert knowledge for Inertia.js with Litestar. Use when building SPAs with server-side routing, handling Inertia responses, or managing page components.
---

# Inertia.js Skill

## Quick Reference

### Python Backend (Litestar)

```python
from litestar import get, post, Controller
from litestar_vite.inertia import InertiaRequest, InertiaResponse, share

class DashboardController(Controller):
    path = "/dashboard"

    @get("/")
    async def index(self, request: InertiaRequest) -> InertiaResponse:
        return InertiaResponse(
            component="Dashboard/Index",
            props={
                "user": await get_current_user(request),
                "stats": await get_stats(),
            },
        )

    @post("/settings")
    async def update_settings(
        self,
        request: InertiaRequest,
        data: SettingsDTO,
    ) -> InertiaResponse:
        await save_settings(data)
        return InertiaResponse(
            component="Dashboard/Settings",
            props={"message": "Settings updated"},
        )
```

### Shared Data

```python
# Share data across all Inertia responses
from litestar_vite.inertia import InertiaPlugin, share

plugin = InertiaPlugin(
    config=InertiaConfig(
        root_template="base.html",
    ),
)

# In middleware or route
async def shared_data_middleware(request, call_next):
    share(request, {
        "auth": {"user": request.user},
        "flash": get_flash_messages(request),
    })
    return await call_next(request)
```

### Frontend (React)

```tsx
import { usePage, Link, router } from '@inertiajs/react';

interface PageProps {
  user: User;
  stats: Stats;
}

export default function Dashboard() {
  const { user, stats } = usePage<PageProps>().props;

  const handleRefresh = () => {
    router.reload({ only: ['stats'] });
  };

  return (
    <div>
      <h1>Welcome, {user.name}</h1>
      <Link href="/dashboard/settings">Settings</Link>
      <button onClick={handleRefresh}>Refresh Stats</button>
    </div>
  );
}
```

### Frontend (Vue)

```vue
<script setup lang="ts">
import { usePage, Link, router } from '@inertiajs/vue3';

interface PageProps {
  user: User;
  stats: Stats;
}

const page = usePage<PageProps>();

function handleRefresh() {
  router.reload({ only: ['stats'] });
}
</script>

<template>
  <div>
    <h1>Welcome, {{ page.props.user.name }}</h1>
    <Link href="/dashboard/settings">Settings</Link>
  </div>
</template>
```

### Inertia Protocol

Inertia requests include:
- `X-Inertia: true` header
- `X-Inertia-Version` for asset versioning
- `X-Inertia-Partial-Data` for partial reloads

## Project-Specific Patterns

- `InertiaConfig` in `src/py/litestar_vite/inertia/config.py`
- `InertiaPlugin` handles middleware and template rendering
- `InertiaResponse` for all Inertia route responses

## Context7 Lookup

```python
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/inertiajs/inertia",
    topic="protocol responses links",
    mode="code"
)
```

## Related Files

- `src/py/litestar_vite/inertia/` - Python Inertia implementation
- `examples/inertia/` - Inertia example
- `examples/spa-vue-inertia/` - Vue + Inertia example

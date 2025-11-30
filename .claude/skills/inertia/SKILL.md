---
name: inertia
description: Expert knowledge for Inertia.js with Litestar. Use when building SPAs with server-side routing, handling Inertia responses, or managing page components.
---

# Inertia.js Skill

## Quick Reference

### Python Backend (Litestar) - Route Handlers

**Key Pattern**: Use the `component` parameter in route decorators, return `dict` for props (not `InertiaResponse`):

```python
from litestar import get, post, Controller, Response
from litestar.di import Provide
from litestar_vite.inertia import InertiaRedirect

class DashboardController(Controller):
    path = "/dashboard"

    @get(component="Dashboard/Index", name="dashboard")
    async def index(self, request: Request) -> dict:
        """Show dashboard page.

        The component is specified in the decorator.
        Return a dict with props - NOT InertiaResponse.
        """
        return {
            "user": await get_current_user(request),
            "stats": await get_stats(),
        }

    @get(component="Dashboard/Settings", name="settings", path="/settings")
    async def settings(self, request: Request) -> dict:
        """Show settings page."""
        return {
            "settings": await get_user_settings(request),
        }
```

### Authentication Pattern

```python
from litestar import get, post, Controller, Response, Request
from litestar.di import Provide
from litestar_vite.inertia import InertiaRedirect
from app.lib.flash import flash

class AccessController(Controller):
    """User login and registration."""

    path = "/auth"
    include_in_schema = False
    exclude_from_auth = True

    @get(component="auth/login", name="login", path="/login/")
    async def show_login(self, request: Request) -> Response | dict:
        """Show the user login page.

        Returns:
            - dict with props if showing login form
            - InertiaRedirect if already authenticated
        """
        if request.session.get("user_id", False):
            flash(request, "Your account is already authenticated.", category="info")
            return InertiaRedirect(request, request.url_for("dashboard"))
        return {}

    @post(component="auth/login", name="login.check", path="/login/")
    async def login(
        self,
        request: Request,
        users_service: UserService,
        data: AccountLogin,
    ) -> Response:
        """Authenticate a user.

        Always returns InertiaRedirect after authentication attempt.
        """
        user = await users_service.authenticate(data.username, data.password)
        request.set_session({"user_id": user.email})
        flash(request, "Your account was successfully authenticated.", category="info")
        return InertiaRedirect(request, request.url_for("dashboard"))

    @post(name="logout", path="/logout/", exclude_from_auth=False)
    async def logout(self, request: Request) -> Response:
        """Account Logout - always redirects."""
        flash(request, "You have been logged out.", category="info")
        request.clear_session()
        return InertiaRedirect(request, request.url_for("login"))
```

### Shared Data

```python
from litestar_vite.inertia import InertiaPlugin, InertiaConfig, share

plugin = InertiaPlugin(
    config=InertiaConfig(
        root_template="base.html",
    ),
)

# Share data across all Inertia responses via middleware
async def shared_data_middleware(request, call_next):
    share(request, {
        "auth": {"user": request.user},
        "flash": get_flash_messages(request),
    })
    return await call_next(request)
```

### Key Patterns

| Scenario | Return Type | Notes |
|----------|-------------|-------|
| Show page | `dict` | Component in decorator, return props dict |
| Redirect | `InertiaRedirect` | After form submit, logout, etc. |
| Conditional | `Response \| dict` | Check condition, redirect or show |

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
- Use `component` parameter in route decorator, NOT `InertiaResponse`
- Return `dict` for props, use `InertiaRedirect` for redirects

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
- `examples/vue-inertia/` - Inertia example
- `examples/vue-inertia/` - Vue + Inertia example

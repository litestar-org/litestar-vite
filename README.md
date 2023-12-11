# Litestar Vite

> [!IMPORTANT]
> This plugin currently contains minimal features and is a work-in-progress

## Installation

```shell
pip install litestar-vite
```

## Usage

Here is a basic application that demonstrates how to use the plugin.

```python
from __future__ import annotations

from pathlib import Path

from litestar import Controller, get
from litestar.response import Template
from litestar.status_codes import HTTP_200_OK
from litestar_vite import ViteConfig, VitePlugin

class WebController(Controller):

    opt = {"exclude_from_auth": True}
    include_in_schema = False

    @get(["/", "/{path:str}"],status_code=HTTP_200_OK)
    async def index(self) -> Template:
        return Template(template_name="index.html.j2")


vite = VitePlugin(
    config=ViteConfig(
        bundle_dir=Path("./public"),
        resources_dir=Path("./resources"),
        assets_dir=Path("./resources/assets"),
        templates_dir=Path("./templates"),
        # Should be False when in production
        dev_mode=True,
        hot_reload=True, # Websocket HMR asset reloading is enabled when true.
    ),
)
app = Litestar(plugins=[vite], route_handlers=[WebController])

```

Create a template to serve the application in `./templates/index.html.h2`:

```html
<!DOCTYPE html>
<html class="h-full">
  <head>
    <meta charset="utf-8" />
    <!--IE compatibility-->
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta
      name="viewport"
      content="width=device-width, initial-scale=1.0, maximum-scale=1.0"
    />
  </head>

  <body class="font-sans leading-none text-gray-700 antialiased">
    <div id="app"></div>
    {{ vite_hmr() }} {{ vite('main.ts') }}
  </body>
</html>
```

Initialize the Vite configuration.

```shell
❯ litestar assets init
Using Litestar app from app:app
Initializing Vite ──────────────────────────────────────────────────────────────────────────────────────────
Do you intend to use Litestar with any SSR framework? [y/n]: n
INFO - 2023-12-11 12:33:41,455 - root - commands - Writing vite.config.ts
INFO - 2023-12-11 12:33:41,456 - root - commands - Writing package.json
INFO - 2023-12-11 12:33:41,456 - root - commands - Writing tsconfig.json
```

```shell
❯ tree
.
├── app.py
├── __init__.py
├── package.json
├── tsconfig.json
├── vite.config.ts
└── web
    ├── controllers.py
    ├── __init__.py
    ├── public
    └── resources
        └── assets
```

### Development

Install the packages required for development:

```shell
❯ litestar assets install
Using Litestar app from app:app
Starting Vite package installation process ──────────────────────────────────────────────────────────────────────────────────────────

added 25 packages, and audited 26 packages in 1s


5 packages are looking for funding
  run `npm fund` for details


found 0 vulnerabilities
```

To automatically start and stop the Vite instance with the Litestar application, you can enable the `use_server_lifespan` hooks in the `ViteConfig`.

Alternately, to start the development server manually, you can run the following

```shell
❯ litestar assets serve
Using Litestar app from app:app
Starting Vite build process ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

> build
> vite build


vite v5.0.7 building for production...

✓ 0 modules transformed.

```

**Note** This is equivalent to the the `npm run dev` command by default.

### Building for Production

```shell
❯ litestar assets build
Using Litestar app from app:app
Starting Vite build process ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

> build
> vite build


vite v5.0.7 building for production...

✓ 0 modules transformed.

```

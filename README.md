# Litestar Vite

## Installation

```shell
pip install litestar-vite
```

## Usage

Here is a basic application that demonstrates how to use the plugin.

```python
from __future__ import annotations

from pathlib import Path

from litestar import Controller, get, Litestar
from litestar.response import Template
from litestar.status_codes import HTTP_200_OK
from litestar.template.config import TemplateConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar_vite import ViteConfig, VitePlugin

class WebController(Controller):

    opt = {"exclude_from_auth": True}
    include_in_schema = False

    @get(["/", "/{path:str}"],status_code=HTTP_200_OK)
    async def index(self) -> Template:
        return Template(template_name="index.html.j2")

template_config = TemplateConfig(engine=JinjaTemplateEngine(directory='templates/'))
vite = VitePlugin(config=ViteConfig())
app = Litestar(plugins=[vite], template_config=template_config, route_handlers=[WebController])

```

Create a template to serve the application in `./templates/index.html.h2`:

```html
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <!--IE compatibility-->
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta
      name="viewport"
      content="width=device-width, initial-scale=1.0, maximum-scale=1.0"
    />
  </head>

  <body>
    <div id="app"></div>
    {{ vite_hmr() }} {{ vite('resources/main.ts') }}
  </body>
</html>
```

### Template initialization (Optional)

This is a command to help initialize Vite for your project. This is generally only needed a single time. You may also manually configure Vite and skip this step.

to initialize a Vite configuration:

```shell
❯ litestar assets init
Using Litestar app from app:app
Initializing Vite ──────────────────────────────────────────────────────────────────────────────────────────
Do you intend to use Litestar with any SSR framework? [y/n]: n
INFO - 2023-12-11 12:33:41,455 - root - commands - Writing vite.config.ts
INFO - 2023-12-11 12:33:41,456 - root - commands - Writing package.json
INFO - 2023-12-11 12:33:41,456 - root - commands - Writing tsconfig.json
```

### Install Javascript/Typescript Packages

Install the packages required for development:

**Note** This is equivalent to the the `npm install` by default. This command is configurable.

```shell
❯ litestar assets install
Using Litestar app from app:app
Starting Vite package installation process ──────────────────────────────────────────────────────────────────────────────────────────

added 25 packages, and audited 26 packages in 1s


5 packages are looking for funding
  run `npm fund` for details


found 0 vulnerabilities
```

### Development

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

**Note** This is equivalent to the the `npm run dev` command when `hot_reload` is enabled. Otherwise it is equivalent to `npm run build -- --watch`. This command is configurable.

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

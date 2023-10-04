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

from litestar import Litestar
from litestar_vite import ViteConfig, VitePlugin

vite = VitePlugin(
    config=ViteConfig(
        static_dir="./local_static_dir",
        templates_dir="./path_to_jinja_templates",
        # Should be False when in production
        hot_reload=True, # Websocket HMR asset reloading is enabled when true.
        port=3005,
    ),
)
app = Litestar(plugins=[vite])

```

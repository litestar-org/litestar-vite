# Litestar Aiosql

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
from litestar_vite import AiosqlPlugin, AiosqlConfig

vite = AiosqlPlugin(config=AiosqlConfig())
app = Litestar(plugins=[vite])

```

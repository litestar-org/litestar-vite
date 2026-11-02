# Angular

Litestar supports two integration approaches for Angular applications:

1. **Vite-Based (`angular` template, `mode="spa"`)** — Uses `@analogjs/vite-plugin-angular` directly with `litestar-vite-plugin` for single-port HMR and unified Vite builds.
2. **Angular CLI (`angular-cli` template, `mode="external"`)** — Uses the native Angular CLI (`ng serve` / `ng build` via `@angular/build:application`) with `ExternalDevServer` process management and `TypeGenConfig`.

---

## Comparison: Vite (`analogjs`) vs Angular CLI

| Feature | Option 1: Vite (`@analogjs/vite-plugin-angular`) | Option 2: Angular CLI (`@angular/build`) |
| --- | --- | --- |
| **Scaffold Template** | `litestar assets init --template angular` | `litestar assets init --template angular-cli` |
| **Operating Mode** | `mode="spa"` | `mode="external"` |
| **Build Tool** | Vite (`litestar-vite-plugin`) | Angular CLI (`angular.json` + `@angular/build:application`) |
| **Dev Server** | Vite HMR proxied through Litestar (`:8000`) | `ng serve` managed via `ExternalDevServer` |
| **Type Generation** | Automatic via `litestar-vite-plugin` | Automatic via `ViteConfig(types=TypeGenConfig(...))` |
| **Best For** | New fullstack projects wanting unified Vite tooling | Existing Angular CLI workspaces or enterprise `ng` pipelines |

---

## Option 1: Vite-Based Angular (`mode="spa"`)

### Quick Start

```bash
litestar assets init --template angular
litestar assets install
litestar run --reload
```

### Configuration

=== "Python (`app.py`)"

    ```python title="app.py"
    from pathlib import Path

    from litestar import Litestar, get
    from msgspec import Struct
    from litestar_vite import PathConfig, TypeGenConfig, ViteConfig, VitePlugin


    class Book(Struct):
        id: int
        title: str
        author: str


    @get("/api/books", name="books", sync_to_thread=False)
    def list_books() -> list[Book]:
        """Return typed book catalog."""
        return [Book(id=1, title="Async Python", author="Litestar Team")]


    app = Litestar(
        route_handlers=[list_books],
        plugins=[
            VitePlugin(
                config=ViteConfig(
                    mode="spa",
                    dev_mode=True,
                    paths=PathConfig(resource_dir=Path("src")),
                    types=TypeGenConfig(generate_sdk=True, generate_routes=True),
                ),
            ),
        ],
    )
    ```

=== "Vite (`vite.config.ts`)"

    <!-- docs-example: skip -->
    ```typescript title="vite.config.ts"
    import { defineConfig } from "vite";
    import angular from "@analogjs/vite-plugin-angular";
    import litestar from "litestar-vite-plugin";

    export default defineConfig({
      plugins: [
        angular(),
        litestar({
          input: ["src/main.ts"],
          types: "auto",
        }),
      ],
    });
    ```

### Standalone Component with `HttpClient` and `route()`

```typescript title="src/app/books.component.ts"
import { Component, inject, type OnInit } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { route } from "../generated/routes";
import type { Book } from "../generated/api";

@Component({
  selector: "app-books",
  standalone: true,
  template: `
    <section>
      <h2>Books</h2>
      <ul>
        @for (book of books; track book.id) {
          <li>{{ book.title }} — {{ book.author }}</li>
        }
      </ul>
    </section>
  `,
})
export class BooksComponent implements OnInit {
  private readonly http = inject(HttpClient);
  books: Book[] = [];

  ngOnInit(): void {
    this.http.get<Book[]>(route("books")).subscribe((data) => {
      this.books = data;
    });
  }
}
```

---

## Option 2: Angular CLI (`mode="external"`)

When using Angular CLI (`@angular/build:application` and `@angular/build:dev-server`), configure `mode="external"` and `ExternalDevServer` so `litestar run` starts `ng serve` and proxies non-API traffic automatically:

```bash
litestar assets init --template angular-cli
litestar assets install
litestar run --reload
```

```python title="app.py"
from pathlib import Path

from litestar import Litestar
from litestar_vite import ExternalDevServer, PathConfig, RuntimeConfig, TypeGenConfig, ViteConfig, VitePlugin

app = Litestar(
    route_handlers=[],
    plugins=[
        VitePlugin(
            config=ViteConfig(
                mode="external",
                dev_mode=True,
                paths=PathConfig(bundle_dir=Path("dist/browser")),
                runtime=RuntimeConfig(
                    external_dev_server=ExternalDevServer(
                        target="http://127.0.0.1:4200",
                        command=["npx", "ng", "serve", "--port", "4200"],
                        build_command=["npx", "ng", "build"],
                    ),
                ),
                types=TypeGenConfig(
                    output=Path("src/generated"),
                    generate_sdk=True,
                    generate_routes=True,
                ),
            ),
        ),
    ],
)
```

# Type Generation Demo
# Demonstrates: litestar assets generate-types with hey-api/openapi-ts
# Uses: examples/react-inertia (has TypeGenConfig enabled)

Output docs/_static/demos/type-generation.gif

Set Shell "bash"
Set FontSize 14
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 50ms

Type "# Litestar Vite - TypeScript Type Generation"
Enter
Sleep 1s

Hide
Type "source .venv/bin/activate"
Enter
Sleep 500ms
Type "cd examples/react-inertia"
Enter
Sleep 500ms
# Clean up any existing generated files for a fresh demo
Type "rm -rf resources/generated 2>/dev/null || true"
Enter
Sleep 300ms
Show

Type "# Generate TypeScript types from your Litestar API"
Enter
Sleep 500ms

Type "litestar --app app:app assets generate-types"
Enter
Sleep 4s

Type "# Let's see what was generated:"
Enter
Sleep 500ms

Type "tree resources/generated"
Enter
Sleep 2s

Type "# Type-safe API client with full IntelliSense!"
Enter
Sleep 500ms

Type "head -30 resources/generated/api/sdk.gen.ts"
Enter
Sleep 3s

Type "# Routes are also exported for type-safe navigation"
Enter
Sleep 500ms

Type "head -20 resources/generated/routes.json"
Enter
Sleep 2s

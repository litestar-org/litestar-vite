# VHS tape for recording type generation demo
# Run with: vhs docs/_tapes/type-generation.tape
# Output: docs/assets/demos/type-generation.gif

Output docs/assets/demos/type-generation.gif

Set FontSize 15
Set Width 950
Set Height 550
Set Theme "Dracula"
Set Padding 20
Set TypingSpeed 40ms

# Setup
Hide
Type "cd examples/react-inertia && clear"
Enter
Sleep 500ms
Show

Type "# Automatic TypeScript Type Generation with Litestar Vite"
Enter
Sleep 1s

# Show the Litestar routes
Type "# 1. Backend defines typed routes with Litestar:"
Enter
Sleep 500ms
Type "head -35 app.py"
Enter
Sleep 3s

# Generate types
Type "# 2. Generate TypeScript types from OpenAPI, AsyncAPI, and routes:"
Enter
Sleep 500ms
Type "litestar assets generate-types"
Enter
Sleep 4s

# Show generated files
Type "# 3. Generated files include routes.ts, schemas.ts, and API SDK:"
Enter
Sleep 500ms
Type "ls -la src/generated/"
Enter
Sleep 2s

# Show route helper
Type "# 4. Type-safe route() helper with autocomplete:"
Enter
Sleep 500ms
Type "head -40 src/generated/routes.ts"
Enter
Sleep 4s

Sleep 2s

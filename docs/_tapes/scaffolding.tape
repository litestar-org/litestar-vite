# Scaffolding Demo (FIXED)
# Demonstrates: litestar assets init
# Uses: temporary directory to show fresh project setup

Output docs/_static/demos/scaffolding.gif

Set Shell "bash"
Set FontSize 14
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 50ms

Type "# Litestar Vite - Scaffold a New Frontend"
Enter
Sleep 1s

Hide
Type "source .venv/bin/activate"
Enter
Sleep 500ms
# Create a temporary demo directory
Type "cd /tmp && rm -rf litestar-demo && mkdir litestar-demo && cd litestar-demo"
Enter
Sleep 500ms
# Create minimal app.py with VitePlugin
Type "cat > app.py << 'EOF'"
Enter
Type "from litestar import Litestar, get"
Enter
Type "from litestar_vite import ViteConfig, VitePlugin"
Enter
Type ""
Enter
Type "@get('/')"
Enter
Type "async def index() -> dict:"
Enter
Type "    return {'message': 'Hello!'}"
Enter
Type ""
Enter
Type "app = Litestar("
Enter
Type "    route_handlers=[index],"
Enter
Type "    plugins=[VitePlugin(config=ViteConfig(dev_mode=True))]"
Enter
Type ")"
Enter
Type "EOF"
Enter
Sleep 500ms
Show

Type "# Start with a basic Litestar app"
Enter
Sleep 500ms

Type "cat app.py"
Enter
Sleep 2s

Type "# Scaffold a React frontend with Inertia.js"
Enter
Sleep 500ms

Type "litestar --app app:app assets init --template react-inertia --no-prompt --no-install"
Enter
Sleep 4s

Type "# Files generated! Check the structure:"
Enter
Sleep 500ms

Type "tree -L 2 --dirsfirst -I 'node_modules'"
Enter
Sleep 3s

Type "# Next: litestar assets install && litestar run"
Enter
Sleep 2s

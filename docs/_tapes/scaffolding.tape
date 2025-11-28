Output docs/_static/demos/scaffolding.gif

Set Shell "bash"
Set FontSize 14
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 50ms

Type "# Litestar Vite - Scaffold a new frontend"
Enter
Sleep 1s

Hide
Type "cd examples/basic"
Enter
Sleep 500ms
Show

Type "# From an existing Litestar project with VitePlugin configured"
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
Sleep 3s

Type "# Files generated! Check the structure:"
Enter
Type "tree -L 2 --dirsfirst -I 'node_modules|__pycache__'"
Enter
Sleep 3s

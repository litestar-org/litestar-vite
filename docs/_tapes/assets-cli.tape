# Assets CLI Overview Demo
# Demonstrates: litestar assets wraps npm/bun/deno workflows
# Uses: examples/react-inertia

Output docs/_static/demos/assets-cli.gif

Set Shell "bash"
Set FontSize 14
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 50ms

Type "# Litestar Vite - Asset Management CLI"
Enter
Sleep 1s

Hide
Type "source .venv/bin/activate"
Enter
Sleep 500ms
Type "cd examples/react-inertia"
Enter
Sleep 500ms
Show

Type "# Wraps the npm/bun/deno workflow you already know"
Enter
Sleep 500ms

Type "litestar --app app:app assets --help"
Enter
Sleep 3s

Type "# 'install' wraps npm/bun/deno install"
Enter
Sleep 500ms

Type "litestar --app app:app assets install"
Enter
Sleep 4s

Type "# 'build' wraps vite build"
Enter
Sleep 500ms

Type "litestar --app app:app assets build"
Enter
Sleep 5s

Type "# Same tools, unified interface!"
Enter
Sleep 5s

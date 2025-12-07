# HMR Demo - Integrated Dev Server
# Demonstrates: litestar run with integrated Vite dev server
# Uses: examples/react-inertia

Output docs/_static/demos/hmr.gif

Set Shell "bash"
Set FontSize 14
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 50ms

Type "# Litestar Vite - Integrated Dev Server"
Enter
Sleep 1s

Hide
Type "source .venv/bin/activate"
Enter
Sleep 500ms
Type "cd examples/react-inertia"
Enter
Sleep 500ms
# Ensure dependencies are installed (hidden)
Type "litestar --app app:app assets install 2>/dev/null"
Enter
Sleep 4s
Show

Type "# One command starts everything - Litestar + Vite HMR"
Enter
Sleep 500ms

Type "# In dev_mode=True, Vite is automatically proxied"
Enter
Sleep 500ms

Type "litestar --app app:app run"
Enter
Sleep 5s

Type ""
Sleep 1s

# Show that server is running
Type "# Server running at http://localhost:5002"
Enter
Sleep 500ms

Type "# Vite HMR is proxied through /static/vite-hmr"
Enter
Sleep 500ms

Type "# Edit your React components - changes appear instantly!"
Enter
Sleep 2s

# Simulate Ctrl+C to stop
Ctrl+C
Sleep 500ms

Type "# That's it - unified development experience!"
Enter
Sleep 2s

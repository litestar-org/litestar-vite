# Production Build Demo
# Demonstrates: litestar assets build workflow
# Uses: examples/react-inertia

Output docs/_static/demos/production-build.gif

Set Shell "bash"
Set FontSize 14
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 50ms

Type "# Litestar Vite - Production Build"
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

Type "# Build optimized assets for production"
Enter
Sleep 500ms

Type "litestar --app app:app assets build"
Enter
Sleep 5s

Type "# Assets are built to public/ with a manifest"
Enter
Sleep 500ms

Type "ls -la public/"
Enter
Sleep 2s

Type "# The manifest maps source files to hashed outputs"
Enter
Sleep 500ms

Type "cat public/manifest.json | head -20"
Enter
Sleep 3s

Type "# Ready for deployment!"
Enter
Sleep 2s

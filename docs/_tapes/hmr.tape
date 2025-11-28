Output docs/_static/demos/hmr.gif

Set Shell "bash"
Set FontSize 14
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 50ms

Type "# Litestar Vite - Development with HMR"
Enter
Sleep 1s

Hide
Type "cd examples/basic"
Enter
Sleep 500ms
Show

Type "# With use_server_lifespan=True, one command starts everything"
Enter
Sleep 500ms

Type "# Litestar manages the Vite dev server automatically!"
Enter
Sleep 500ms

Type "litestar --app app:app run --reload"
Enter
Sleep 4s

Type ""
Enter
Sleep 1s

# Simulate Ctrl+C to stop
Ctrl+C
Sleep 500ms

Type "# That's it! Litestar + Vite HMR in one command."
Enter
Sleep 2s

# VHS tape for recording scaffolding demo
# Run with: vhs docs/_tapes/scaffolding.tape
# Output: docs/assets/demos/scaffolding.gif

Output docs/assets/demos/scaffolding.gif

Set FontSize 16
Set Width 900
Set Height 500
Set Theme "Dracula"
Set Padding 20
Set TypingSpeed 40ms

# Hide initial setup
Hide
Type "cd /tmp && rm -rf demo-app && mkdir demo-app && cd demo-app"
Enter
Sleep 500ms
Type "clear"
Enter
Sleep 500ms
Show

# Create a minimal Litestar app first
Type "# Scaffold a React + Inertia project with Litestar Vite"
Enter
Sleep 1s

# Run litestar assets init with React-Inertia template
Type "litestar assets init --template react-inertia --no-prompt"
Enter
Sleep 4s

# Show generated files
Type "ls -la"
Enter
Sleep 2s

# Show the resources directory
Type "ls -la resources/"
Enter
Sleep 2s

# Show vite.config.ts
Type "cat vite.config.ts"
Enter
Sleep 3s

# Final pause
Sleep 2s

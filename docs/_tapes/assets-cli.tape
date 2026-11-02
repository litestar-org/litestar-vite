# VHS tape for recording CLI commands demo
# Run with: vhs docs/_tapes/assets-cli.tape
# Output: docs/assets/demos/assets-cli.gif

Output docs/assets/demos/assets-cli.gif

Set FontSize 15
Set Width 950
Set Height 550
Set Theme "Dracula"
Set Padding 20
Set TypingSpeed 35ms

# Setup
Hide
Type "cd examples/vue && clear"
Enter
Sleep 500ms
Show

Type "# Litestar Vite CLI Commands"
Enter
Sleep 1s

# Show help
Type "litestar assets --help"
Enter
Sleep 3s

# Check status
Type "litestar assets status"
Enter
Sleep 3s

# Run doctor
Type "litestar assets doctor"
Enter
Sleep 3s

# Export routes
Type "litestar assets export-routes"
Enter
Sleep 2s

Sleep 2s

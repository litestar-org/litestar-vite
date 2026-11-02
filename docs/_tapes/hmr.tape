# VHS tape for recording HMR (Hot Module Replacement) demo
# Run with: vhs docs/_tapes/hmr.tape
# Output: docs/assets/demos/hmr.gif
# Note: This tape shows the terminal side of HMR

Output docs/assets/demos/hmr.gif

Set FontSize 15
Set Width 950
Set Height 550
Set Theme "Dracula"
Set Padding 20
Set TypingSpeed 40ms

# Setup in background
Hide
Type "cd examples/react && clear"
Enter
Sleep 500ms
Show

Type "# Starting Litestar with Vite single-port proxy + HMR"
Enter
Sleep 1s

# Show how to start both servers
Type "# Single command starts both Litestar and Vite:"
Enter
Sleep 1s

Type "litestar run --reload"
Enter
Sleep 5s

# Simulate Ctrl+C after showing output
Ctrl+C
Sleep 1s

Type "# Vite HMR updates components in-place without losing state"
Enter
Sleep 2s

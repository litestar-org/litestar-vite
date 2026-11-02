# VHS tape for recording production build demo
# Run with: vhs docs/_tapes/production-build.tape
# Output: docs/assets/demos/production-build.gif

Output docs/assets/demos/production-build.gif

Set FontSize 15
Set Width 950
Set Height 550
Set Theme "Dracula"
Set Padding 20
Set TypingSpeed 40ms

# Setup
Hide
Type "cd examples/vue && rm -rf public && clear"
Enter
Sleep 500ms
Show

Type "# Building for Production with Litestar Vite"
Enter
Sleep 1s

# Build assets
Type "litestar assets build"
Enter
Sleep 5s

# Show output directory
Type "# Built assets with content hashes for cache busting:"
Enter
Sleep 500ms
Type "ls -la public/"
Enter
Sleep 2s

# Show manifest
Type "# Manifest maps source files to hashed outputs:"
Enter
Sleep 500ms
Type "cat public/.vite/manifest.json"
Enter
Sleep 3s

Sleep 2s

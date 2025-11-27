Output docs/_static/demos/scaffolding.gif

Set Shell "bash"
Set FontSize 14
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"
Set Padding 20

Type "# Litestar Vite Project Scaffolding Demo"
Enter
Sleep 1s

Type "litestar assets init"
Enter
Sleep 2s

# Enter project name
Type "my-awesome-app"
Enter
Sleep 500ms

# Select template (React is usually option 2)
Type "2"
Enter
Sleep 500ms

# Confirm
Type "y"
Enter
Sleep 3s

Type "# Project created! Let's see what was generated:"
Enter
Sleep 1s

Type "ls -la my-awesome-app/"
Enter
Sleep 2s

Type "# Navigate into the project"
Enter
Type "cd my-awesome-app && tree -L 2"
Enter
Sleep 3s

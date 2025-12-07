# Recovery Guide: VHS Demo GIFs

## Current State

PRD and task breakdown created. Ready for implementation.

## Files Modified

- `specs/active/vhs-demo-gifs/prd.md` - PRD created
- `specs/active/vhs-demo-gifs/tasks.md` - Task breakdown created

## Existing Infrastructure

The following already exists and works:
- `docs/_tapes/hmr.tape` - HMR demonstration
- `docs/_tapes/scaffolding.tape` - Project scaffolding
- `docs/_static/demos/*.gif` - Generated outputs
- `Makefile` target `docs-demos` - Generation command
- `docs/index.rst` - Already references existing demos

## Next Steps

1. **Install VHS locally** (if not already):
   ```bash
   # macOS
   brew install vhs

   # Linux (with Go installed)
   go install github.com/charmbracelet/vhs@latest
   ```

2. **Test existing demos still work**:
   ```bash
   make docs-demos
   ```

3. **Create new tape files** (priority order):
   - `type-generation.tape` - High value, shows TypeScript integration
   - `assets-cli.tape` - Good overview demo
   - `production-build.tape` - Shows production workflow

4. **Update documentation** to include new demos

## Context for Resumption

### Key Files to Read
- [docs/_tapes/hmr.tape](docs/_tapes/hmr.tape) - Example tape structure
- [docs/_tapes/scaffolding.tape](docs/_tapes/scaffolding.tape) - Example tape structure
- [Makefile:279-287](Makefile#L279-L287) - `docs-demos` target

### VHS Syntax Quick Reference
```tape
Output docs/_static/demos/name.gif
Set Shell "bash"
Set FontSize 14
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 50ms

Hide                    # Stop recording
Type "cd examples/..."  # Hidden setup
Enter
Show                    # Resume recording

Type "# Comment shown in terminal"
Enter
Type "actual command"
Enter
Sleep 3s               # Wait for output
```

### Example Directories for Demos
- `examples/basic` - Simple Vite setup
- `examples/react-inertia` - Full Inertia.js with React
- `examples/vue-inertia` - Full Inertia.js with Vue

### Dependencies
- VHS CLI tool
- ffmpeg (VHS dependency)
- ttyd (VHS dependency)

## Open Questions

1. Should demos run against a temporary directory or use existing examples?
2. What's the best timing for `Sleep` commands when waiting for servers?
3. Should we add CI automation for demo regeneration?

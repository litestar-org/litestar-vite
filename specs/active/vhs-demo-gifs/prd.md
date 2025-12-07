# PRD: VHS Demo GIFs for Documentation

## Overview
- **Slug**: vhs-demo-gifs
- **Created**: 2025-12-07
- **Status**: Draft

## Problem Statement

Litestar-vite has VHS tape infrastructure configured (`make docs-demos`, `docs/_tapes/*.tape`) but:
1. Only 2 basic demos exist (HMR, scaffolding)
2. Many powerful CLI features lack visual demonstrations
3. The demos are referenced in `docs/index.rst` but could be featured more prominently
4. New developers can't quickly see what the tool does without reading documentation

Visual GIFs are highly effective for:
- Marketing/README appeal
- Quick feature discovery
- Reducing onboarding friction
- Demonstrating the developer experience

## Goals

1. Create comprehensive demo GIFs covering all major CLI commands
2. Update documentation to prominently feature demos where relevant
3. Document how to regenerate demos (in CONTRIBUTING or developer docs)
4. Ensure demos work with real examples and show actual tool output

## Non-Goals

- Video tutorials (GIFs only)
- Demos for every minor feature
- Demos requiring external services/APIs
- Localized/translated demos

## Acceptance Criteria

- [ ] At least 5-7 demo GIFs covering key features
- [ ] Each demo is self-contained and shows a complete workflow
- [ ] Demos render correctly at reasonable file sizes (<5MB each)
- [ ] Documentation includes demos in relevant sections
- [ ] `make docs-demos` successfully regenerates all demos
- [ ] CONTRIBUTING.md documents VHS requirements and usage

## Technical Approach

### Existing Infrastructure

Current setup:
- **Makefile target**: `make docs-demos` runs VHS on all `docs/_tapes/*.tape` files
- **Output location**: `docs/_static/demos/`
- **Existing tapes**: `hmr.tape`, `scaffolding.tape`
- **Referenced in**: `docs/index.rst` (featured in tab set)

### Proposed Demo GIFs

| Demo | Description | Tape File | Priority |
|------|-------------|-----------|----------|
| `scaffolding.gif` | Project initialization with `litestar assets init` | Exists | Done |
| `hmr.gif` | HMR demonstration with `litestar run` | Exists | Done |
| `type-generation.gif` | TypeScript type generation from OpenAPI | New | High |
| `inertia-flow.gif` | Inertia.js page navigation flow | New | High |
| `assets-cli.gif` | Overview of `litestar assets` commands | New | Medium |
| `production-build.gif` | Building for production | New | Medium |
| `doctor.gif` | Using `litestar assets doctor` for diagnostics | New | Low |

### Tape File Structure

Each tape should:
1. Set consistent styling (theme, font size, dimensions)
2. Use `Hide`/`Show` for setup commands
3. Include explanatory comments typed to the terminal
4. Run on a clean example project
5. Finish with visible success output

### VHS Configuration Standards

```tape
# Standard header for all tapes
Output docs/_static/demos/[name].gif

Set Shell "bash"
Set FontSize 14
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 50ms
```

### Documentation Updates

1. **docs/index.rst**: Already has scaffolding/HMR in tab set - add more tabs
2. **docs/usage/vite.rst**: Add relevant CLI demos
3. **docs/usage/types.rst**: Add type-generation demo
4. **docs/inertia/**: Add Inertia-specific demos
5. **CONTRIBUTING.md**: Document VHS requirements

### Affected Files

- `docs/_tapes/*.tape` - New tape files
- `docs/_static/demos/*.gif` - Generated output
- `docs/index.rst` - Additional demo tabs
- `docs/usage/*.rst` - CLI usage demos
- `docs/inertia/*.rst` - Inertia demos
- `CONTRIBUTING.md` - Developer documentation

## Testing Strategy

- **Manual testing**: Run `make docs-demos` and verify output
- **Visual inspection**: Check GIF renders correctly in docs preview
- **File size check**: Ensure GIFs are under 5MB
- **Doc build**: `make docs` should succeed with all images

## Implementation Plan

### Phase 1: New Tape Files

Create tape files for:
1. `type-generation.tape` - Generate TypeScript types from OpenAPI
2. `assets-cli.tape` - Quick overview of `litestar assets` subcommands
3. `production-build.tape` - Build and verify production assets
4. `inertia-flow.tape` - Navigate between Inertia pages

### Phase 2: Update Existing Tapes

Review and potentially update:
1. `hmr.tape` - Ensure it still works with current examples
2. `scaffolding.tape` - Verify templates and output

### Phase 3: Documentation Integration

1. Add demos to relevant documentation pages
2. Create a "See it in Action" section if not present
3. Update CONTRIBUTING.md with VHS instructions

## Research Questions

- [ ] What's the optimal GIF dimensions/framerate for documentation?
- [ ] Should demos use the `basic` example or dedicated demo project?
- [ ] Can VHS handle async operations reliably (server startup)?

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| VHS not installed on contributors' machines | Medium | Document in CONTRIBUTING, make optional |
| Demos become outdated with CLI changes | High | Include demo regeneration in release process |
| GIF file sizes too large | Medium | Optimize dimensions, use shorter durations |
| Server startup timing inconsistent | High | Use `Sleep` commands generously |
| Examples not building in demo context | High | Test with actual example directories |

## Dependencies

- [VHS](https://github.com/charmbracelet/vhs) CLI tool
- `ffmpeg` (VHS dependency)
- `ttyd` (VHS dependency)
- Working examples in `examples/` directory

## Future Considerations

- CI integration with [vhs-action](https://github.com/charmbracelet/vhs-action) for automated regeneration
- Video format alternatives (WebM, MP4) for higher quality
- Animated SVGs as alternative to GIFs

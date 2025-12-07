# Tasks: VHS Demo GIFs for Documentation

## Phase 1: Planning
- [x] Create PRD
- [x] Analyze existing tape files
- [x] Identify affected documentation
- [x] Document VHS tape syntax requirements

## Phase 2: New Tape Files

### Type Generation Demo
- [ ] Create `docs/_tapes/type-generation.tape`
- [ ] Show `litestar assets generate-types` command
- [ ] Demonstrate TypeScript output files
- [ ] Test in `examples/react-inertia` context

### Assets CLI Overview Demo
- [ ] Create `docs/_tapes/assets-cli.tape`
- [ ] Show `litestar assets --help` output
- [ ] Demonstrate key subcommands briefly
- [ ] Keep concise (under 30 seconds)

### Production Build Demo
- [ ] Create `docs/_tapes/production-build.tape`
- [ ] Show `litestar assets build` workflow
- [ ] Display manifest and output files
- [ ] Show production server start

### Inertia Flow Demo (Optional - depends on example stability)
- [ ] Create `docs/_tapes/inertia-flow.tape`
- [ ] Navigate between pages
- [ ] Show URL changes without page reload
- [ ] Demonstrate props passing

## Phase 3: Update Existing Tapes

- [ ] Test `hmr.tape` with current example structure
- [ ] Test `scaffolding.tape` with current templates
- [ ] Update if commands or output have changed

## Phase 4: Generate GIFs

- [ ] Run `make docs-demos` locally
- [ ] Verify all GIFs render correctly
- [ ] Check file sizes are reasonable (<5MB each)
- [ ] Visual inspection of each GIF

## Phase 5: Documentation Integration

### Index Page
- [ ] Add type-generation demo to tab set
- [ ] Add assets-cli demo to tab set (if created)
- [ ] Verify tab layout still looks good

### Usage Documentation
- [ ] Add type-generation demo to `docs/usage/types.rst`
- [ ] Add production-build demo to relevant section
- [ ] Add assets-cli demo to `docs/usage/vite.rst`

### Inertia Documentation
- [ ] Add inertia-flow demo to `docs/inertia/how-it-works.rst` (if created)

### Developer Documentation
- [ ] Update CONTRIBUTING.md with VHS section
- [ ] Document `make docs-demos` command
- [ ] List VHS installation instructions

## Phase 6: Quality Assurance

- [ ] Run `make docs` - verify docs build
- [ ] Preview docs locally - check GIF display
- [ ] Test GIFs in multiple browsers
- [ ] Verify no broken image links

## Completion Checklist

- [ ] All new tape files created and tested
- [ ] All GIFs generate without errors
- [ ] Documentation updated with demo references
- [ ] CONTRIBUTING.md updated
- [ ] PR ready for review

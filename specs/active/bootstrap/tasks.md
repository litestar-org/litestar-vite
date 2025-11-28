# Implementation Tasks: AI Development Infrastructure Bootstrap

## Phase 1: Planning & Research ✓

- [x] Analyze existing .claude/ and .gemini/ structure
- [x] Document current command, agent, and skill patterns
- [x] Deep thinking analysis (20 sequential thoughts)
- [x] Create workspace structure
- [x] Write comprehensive PRD (800+ words)
- [x] Document research findings (500+ words)

## Phase 2: Claude Bootstrap Implementation ✓

### 2.1: Core Structure ✓

- [x] Create `.claude/commands/bootstrap.md` file (2394 lines)
- [x] Write Header section with purpose and usage instructions
- [x] Write Preflight section with environment checks
- [x] Write Detection section instructions

### 2.2: Detection Logic ✓

- [x] Embed language detection rules (Python, TypeScript, Rust, Go, Java)
- [x] Embed framework detection rules (litestar, fastapi, react, vue, svelte, angular, vite)
- [x] Embed test framework detection rules (pytest, vitest, jest)
- [x] Embed code style detection rules (type hints, docstrings, test patterns)
- [x] Embed build system detection rules (make, npm scripts, uv, poetry)

### 2.3: Core Templates ✓

- [x] Embed CLAUDE.md template with placeholder variables
- [x] Embed prd.md command template (full PRD workflow)
- [x] Embed implement.md command template
- [x] Embed test.md command template
- [x] Embed review.md command template
- [x] Embed explore.md command template
- [x] Embed fix-issue.md command template

### 2.4: Agent Templates ✓

- [x] Embed prd.md agent template
- [x] Embed expert.md agent template
- [x] Embed testing.md agent template
- [x] Embed docs-vision.md agent template

### 2.5: Framework Knowledge ✓

- [x] Embed Litestar skill template
- [x] Embed FastAPI skill template
- [x] Embed React skill template
- [x] Embed Vue skill template
- [x] Embed Svelte skill template
- [x] Embed Angular skill template
- [x] Embed Vite skill template
- [x] Embed Inertia skill template
- [x] Embed pytest skill template
- [x] Embed vitest skill template

### 2.6: Settings & Specs ✓

- [x] Embed settings.local.json generation logic
- [x] Embed specs/ directory structure generation
- [x] Embed architecture.md template
- [x] Embed code-style.md template
- [x] Embed testing.md template
- [x] Embed quality-gates.yaml template

### 2.7: Alignment Mode ✓

- [x] Write existing config detection logic
- [x] Write custom content preservation rules
- [x] Write merge/update logic
- [x] Write version tracking logic

### 2.8: Verification ✓

- [x] Write verification phase instructions
- [x] Write summary output format
- [x] Write next steps guidance

## Phase 3: Gemini Bootstrap Implementation ✓ (Enhanced v2.0)

### 3.1: Core Structure ✓

- [x] Create `.gemini/commands/bootstrap.toml` file (1506 lines - Enhanced)
- [x] Write Header section (Gemini-specific)
- [x] Write Preflight section
- [x] Write Detection section (shared logic with Claude)

### 3.2: Gemini-Specific Templates ✓

- [x] Embed GEMINI.md template
- [x] Embed prd.toml command template
- [x] Embed implement.toml command template
- [x] Embed test.toml command template
- [x] Embed review.toml command template
- [x] Embed explore.toml command template
- [x] Embed fix-issue.toml command template

### 3.3: Context Files ✓

- [x] Embed framework context templates (litestar, react, vue, pytest, vite, vitest)
- [x] Embed settings.json generation logic

### 3.4: Alignment Mode ✓

- [x] Write Gemini-specific alignment logic
- [x] Write TOML merge strategies

### 3.5: Intelligence Enhancements ✓ (NEW)

- [x] Add Bootstrap Philosophy section (Intelligence Principles)
- [x] Add Intelligent Project Analysis phase (Deep codebase understanding)
- [x] Add MCP Tool Detection with Python script
- [x] Add Adaptive Quality Gates (quality-gates.yaml)
- [x] Add Intelligent Workflow Templates (workflows/intelligent-development.yaml)
- [x] Add Pattern Library initialization (specs/guides/patterns/)
- [x] Add Knowledge Base with pattern extraction
- [x] Add Adaptive Checkpoints (6/8/10+ based on complexity)

## Phase 4: Testing (Auto via /test command)

- [ ] Test Claude bootstrap on fresh Python project
- [ ] Test Claude bootstrap on fresh TypeScript project
- [ ] Test Claude bootstrap on mixed Python+TypeScript project
- [ ] Test Gemini bootstrap on same projects
- [ ] Test alignment mode with existing configurations
- [ ] Test custom content preservation
- [ ] Verify all generated files are valid format
- [ ] Verify generated commands work correctly

## Phase 5: Documentation (Auto via /review command)

- [ ] Update CLAUDE.md to reference bootstrap command
- [ ] Update .gemini/GEMINI.md to reference bootstrap command
- [ ] Add bootstrap to available commands list
- [ ] Create usage examples in research/ folder

## Phase 6: Quality Gate

- [ ] All acceptance criteria verified
- [ ] Bootstrap files are self-contained
- [ ] No external references in bootstrap files
- [ ] Anti-pattern scan clean
- [ ] Workspace ready for archival

## Phase 7: Archival

- [ ] Move specs/active/bootstrap/ to specs/archive/bootstrap/
- [ ] Create ARCHIVED.md with summary
- [ ] Update any cross-references

## Estimated Effort

| Phase | Complexity | Est. Lines |
|-------|------------|------------|
| Claude Core | High | ~2000 |
| Claude Frameworks | Medium | ~3000 |
| Claude Alignment | Medium | ~500 |
| Gemini Core | Medium | ~1500 |
| Gemini Frameworks | Low | ~2000 |
| Gemini Alignment | Low | ~300 |
| **Total per file** | | ~5000-7000 |

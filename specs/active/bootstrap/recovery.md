# Recovery Guide: AI Development Infrastructure Bootstrap

**Slug**: bootstrap
**Created**: 2025-11-28
**Status**: Planning Complete

## Current Phase

Phase 2 & 3 (Implementation) - COMPLETE + ENHANCED

Checkpoints completed:

- ✓ Checkpoint 0: Context loaded (existing .claude/ and .gemini/ structure analyzed)
- ✓ Checkpoint 1: Requirements analyzed (user request for self-contained bootstrap)
- ✓ Checkpoint 2: Workspace created at specs/active/bootstrap/
- ✓ Checkpoint 3: Deep analysis (20 sequential thinking steps)
- ✓ Checkpoint 4: Research completed (520+ words documented)
- ✓ Checkpoint 5: PRD written (1800+ words with 23 acceptance criteria)
- ✓ Checkpoint 6: Tasks broken down into 7 phases with 60+ tasks
- ✓ Checkpoint 7: Recovery guide created
- ✓ Checkpoint 8: Claude bootstrap.md created (1226 lines - Enhanced v2.0)
- ✓ Checkpoint 9: Gemini bootstrap.toml created (1506 lines - Enhanced v2.0)
- ✓ Checkpoint 10: Intelligence enhancements from sqlspec added to both files

## Next Steps

**Ready for testing and review**:

1. Run `/test bootstrap` to validate generated files
2. Run `/review bootstrap` for quality gates and archival
3. Both bootstrap files have been enhanced with intelligence features:
   - `.claude/commands/bootstrap.md` (1226 lines - Intelligent Edition v2.0)
   - `.gemini/commands/bootstrap.toml` (1506 lines - Intelligent Edition v2.0)

## Intelligence Enhancements Added

Both bootstrap files now include:

- **Bootstrap Philosophy** - Context-first, adaptive complexity, knowledge accumulation
- **Intelligent Project Analysis** - Deep codebase understanding, pattern extraction
- **MCP Tool Detection** - Python script for automatic tool capability detection
- **Adaptive Quality Gates** - quality-gates.yaml with flexible rules
- **Intelligent Workflow Templates** - workflows/intelligent-development.yaml
- **Pattern Library** - specs/guides/patterns/ for knowledge capture
- **Adaptive Checkpoints** - 6/8/10+ checkpoints based on feature complexity
- **Knowledge Capture** - Patterns extracted and documented during development

## Important Context

**Key deliverables**:

- `.claude/bootstrap.md` - Self-contained Claude Code bootstrap command
- `.gemini/bootstrap.md` - Self-contained Gemini CLI bootstrap command

**Core capabilities each bootstrap must have**:

1. **Detection**: Analyze codebase for languages, frameworks, patterns
2. **Generation**: Create commands, agents, skills, settings, specs/
3. **Alignment**: Update existing configs without losing customizations

**Embedded knowledge requirements**:

- 10+ framework skill templates (litestar, fastapi, react, vue, svelte, angular, vite, inertia, pytest, vitest)
- 6 command templates (prd, implement, test, review, explore, fix-issue)
- 4 agent templates (prd, expert, testing, docs-vision)
- Detection rules for 10+ frameworks and build systems
- Code style detection patterns

**Testing requirements**:

- Bootstrap must work on fresh Python project
- Bootstrap must work on fresh TypeScript project
- Bootstrap must work on mixed Python+TypeScript project
- Alignment mode must preserve custom additions
- All generated files must be valid format

## Research Findings

See [research/plan.md](./research/plan.md) for:
- Current structure analysis
- Detection requirements
- Generation requirements
- Alignment mode requirements
- Self-containment strategy

## PRD Summary

See [prd.md](./prd.md) for:
- 23 acceptance criteria
- Technical approach with architecture diagram
- Implementation phases
- Code samples for detection and generation
- Testing strategy with edge cases

## Tasks Summary

See [tasks.md](./tasks.md) for:
- Phase 2: Claude Bootstrap Implementation (30+ tasks)
- Phase 3: Gemini Bootstrap Implementation (20+ tasks)
- Phase 4-7: Testing, Documentation, Quality Gate, Archival

## Resumption Instructions

**If session interrupted during implementation**:

1. Read [prd.md](./prd.md) for complete requirements
2. Read [tasks.md](./tasks.md) for progress tracking
3. Check which bootstrap file is in progress (Claude or Gemini)
4. Continue from first unchecked task in tasks.md
5. Update this recovery.md with current phase status

**If session interrupted during testing**:

1. Check which mock project test failed
2. Review generated files for issues
3. Fix generation logic in bootstrap files
4. Re-run tests
5. Update recovery.md with test status

**If session interrupted during review**:

1. Check quality gate results
2. Verify bootstrap files are self-contained
3. Verify no external references
4. Complete archival to specs/archive/

## Key Design Decisions

1. **Self-containment**: All templates embedded, no external refs
2. **Checkpoint-based**: Clear phases with verification
3. **Idempotent**: Safe to run multiple times
4. **Preserving**: Respects user customizations
5. **Cross-platform**: Both Claude and Gemini supported
6. **Comprehensive**: Python, TypeScript, and common frameworks

## Verification Checklist

Before marking complete:

- [ ] `.claude/bootstrap.md` created and self-contained
- [ ] `.gemini/bootstrap.md` created and self-contained
- [ ] Both files are 5000-7000 lines
- [ ] Detection logic covers all major frameworks
- [ ] All 23 acceptance criteria met
- [ ] Alignment mode tested and working
- [ ] No source code was modified during PRD phase

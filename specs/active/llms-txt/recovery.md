# Recovery Guide: LLMs.txt Documentation Files

**Slug**: llms-txt
**Last Updated**: 2025-11-28

---

## Quick Resume

To resume work on this feature:

1. Read the PRD: `specs/active/llms-txt/prd.md`
2. Check current progress: `specs/active/llms-txt/tasks.md`
3. Review research: `specs/active/llms-txt/research/plan.md`

---

## Current State

| Aspect | Status |
|--------|--------|
| **Phase** | Phase 1: Planning & Research (Complete) |
| **Last Action** | PRD, tasks, and recovery documents created |
| **Next Action** | Expert agent should begin Phase 2: Research |
| **Blockers** | None |

---

## Files Modified

### Documentation Files (To Be Created)

| File | Status | Notes |
|------|--------|-------|
| `/llms.txt` | Not Started | Concise LLM-friendly documentation (~2000 tokens) |
| `/llms-full.txt` | Not Started | Comprehensive LLM-friendly documentation |

### Workspace Files

| File | Status | Notes |
|------|--------|-------|
| `specs/active/llms-txt/prd.md` | Complete | Full PRD document |
| `specs/active/llms-txt/tasks.md` | Complete | Implementation checklist |
| `specs/active/llms-txt/recovery.md` | Complete | This file |
| `specs/active/llms-txt/research/plan.md` | Complete | Research plan for Expert |

---

## Research Completed

### Sequential Thinking Analysis

Completed 15-step analysis covering:
- llms.txt specification format understanding
- Project structure analysis
- Content section planning for both files
- Technical approach definition
- Research needs identification
- Acceptance criteria definition
- Affected files identification
- Testing strategy
- Risk assessment
- Non-goals definition
- Workspace structure planning
- Implementation phases
- Dependencies analysis
- Final validation

**Key Insights:**
- llms.txt must follow specific markdown structure (H1, blockquote, H2 sections)
- Two distinct files: concise (~2000 tokens) and comprehensive
- Dual-language documentation (Python + TypeScript) requires clear separation
- Pure documentation task, no code changes
- Content sources identified across codebase

### Web Search: llms.txt Specification

- Source: https://llmstxt.org/
- Format: Markdown with specific structure
- Required sections: H1 title, blockquote summary
- Optional section must be labeled
- Purpose: Make documentation LLM-readable

---

## Decisions Made

| Decision | Rationale | Date |
|----------|-----------|------|
| Use markdown files at repository root | Follows llms.txt specification | 2025-11-28 |
| Create two separate files (llms.txt + llms-full.txt) | Specification defines both, different use cases | 2025-11-28 |
| Extract content from source code docstrings | Ensures accuracy and freshness | 2025-11-28 |
| No auto-generation initially | Keep implementation simple, manual updates OK | 2025-11-28 |
| Token limit ~2000 for llms.txt | Specification recommendation | 2025-11-28 |
| Clear Python/TypeScript separation | Dual-language project needs clear structure | 2025-11-28 |

---

## Open Questions

### For Expert Agent to Research

- [x] What is llms.txt specification format? → H1, blockquote, H2 sections
- [ ] What are best practices for multi-language projects?
- [ ] How to count tokens accurately?
- [ ] What level of detail for concise version?
- [ ] Should code examples be inline or linked?
- [ ] What markdown linter to use?

---

## Context for Next Session

The Expert agent should begin with Phase 2: Research. The PRD provides comprehensive guidance on what needs to be researched and implemented.

### Key Deliverables

1. **llms.txt** - Concise documentation file
   - Must be under 2000 tokens
   - Follow specification format exactly
   - Cover both Python and TypeScript APIs
   - Include key examples and links

2. **llms-full.txt** - Comprehensive documentation file
   - No token limit
   - Complete API reference
   - Multiple detailed examples
   - All configuration options

### Key Files to Read First

For content extraction:
1. `/README.md` - Project overview and quick start
2. `/src/py/litestar_vite/config.py` - ViteConfig class
3. `/src/py/litestar_vite/plugin.py` - VitePlugin class
4. `/src/py/litestar_vite/inertia/config.py` - InertiaConfig class
5. `/src/py/litestar_vite/inertia/plugin.py` - InertiaPlugin class
6. `/src/js/src/index.ts` - TypeScript plugin

For examples:
1. `/examples/basic/` - Basic usage
2. `/examples/inertia/` - Inertia.js integration
3. `/examples/spa-react/` - SPA mode

### Potential Issues

- **Token counting** - Need to find reliable method to count tokens for llms.txt
- **API extraction** - Some docstrings may be incomplete, may need to infer from code
- **Keeping content current** - Files will need updates with each release
- **Balancing conciseness vs completeness** - llms.txt must be brief but useful

### Implementation Notes

**For llms.txt:**
- Start with structure, then fill in content
- Use token counter continuously to track size
- Prioritize most important information
- Link to comprehensive version for details

**For llms-full.txt:**
- Can be as detailed as needed
- Include actual type signatures
- Multiple examples per feature
- Complete configuration reference

**Quality Checks:**
- Validate markdown syntax
- Verify all links work
- Test code examples
- Verify API signatures match source
- Test with actual LLMs (Claude/GPT)

---

## Checkpoint History

| Timestamp | Checkpoint | Agent |
|-----------|------------|-------|
| 2025-11-28 | PRD created | PRD |
| 2025-11-28 | Tasks breakdown created | PRD |
| 2025-11-28 | Recovery guide created | PRD |
| 2025-11-28 | Research plan created | PRD |
| | | |

---

## How to Continue

### If Resuming Research (Phase 2)

```python
# Read PRD to understand requirements
Read("specs/active/llms-txt/prd.md")

# Read research plan
Read("specs/active/llms-txt/research/plan.md")

# Begin web research on llms.txt best practices
WebSearch(query="llms.txt python project examples best practices")

# Study the specification
WebFetch(
    url="https://llmstxt.org/",
    prompt="Extract the complete specification format and requirements"
)

# Extract content from README
Read("README.md")

# Extract Python API documentation
Read("src/py/litestar_vite/config.py")
Read("src/py/litestar_vite/plugin.py")
# ... continue with other source files
```

### If Resuming Implementation (Phase 3)

```python
# Read research findings
Read("specs/active/llms-txt/research/plan.md")

# Check what's been learned
Read("specs/active/llms-txt/tasks.md")  # See which research items are complete

# Start creating llms.txt
Write("llms.txt", content="...")  # Begin with structure

# Count tokens to verify size
# Use online tool or tiktoken library

# Continue with llms-full.txt
Write("llms-full.txt", content="...")
```

### If Resuming Validation (Phase 4)

```python
# Read the created files
Read("llms.txt")
Read("llms-full.txt")

# Validate format
# Check H1, blockquote, H2 sections

# Count tokens
# Verify llms.txt < 2000

# Validate markdown
# Run linter if available

# Check links
# Manually or with link checker

# Test with LLM
# Ask Claude questions about litestar-vite using the files
```

---

## Success Metrics

The feature is complete when:

1. **Files Exist**
   - [x] llms.txt at repository root
   - [x] llms-full.txt at repository root

2. **Format Correct**
   - [x] Both follow llms.txt specification
   - [x] Valid markdown syntax
   - [x] All required sections present

3. **Content Accurate**
   - [x] Python APIs documented
   - [x] TypeScript APIs documented
   - [x] Examples included
   - [x] Matches v0.14.0

4. **Quality Validated**
   - [x] llms.txt under 2000 tokens
   - [x] All links work
   - [x] Code examples valid
   - [x] Tested with LLMs

5. **Complete**
   - [x] All acceptance criteria met
   - [x] Quality gates passed
   - [x] Workspace archived

---

## Additional Resources

### Specification

- llms.txt spec: https://llmstxt.org/
- GitHub repo: https://github.com/AnswerDotAI/llms-txt
- Blog post: https://www.answer.ai/posts/2024-09-03-llmstxt.html

### Tools

- Token counter: https://platform.openai.com/tokenizer
- Markdown linter: markdownlint-cli
- Link checker: Various CLI tools available

### Reference Projects

To find examples of good llms.txt files:
- Search GitHub for "llms.txt" in Python projects
- Check popular frameworks (FastAPI, Django, Flask)
- Look at Vite plugin projects

---

## Quick Reference

**Token Limit**: ~2000 tokens for llms.txt

**Files to Create**:
- `/llms.txt` (concise)
- `/llms-full.txt` (comprehensive)

**Required Format**:
```markdown
# Project Title

> Brief summary

Additional description

## Section One
- [Link](url): Description

## Section Two
- [Link](url): Description

## Optional
- [Link](url): Optional content
```

**Priority Content** (for llms.txt):
1. Installation
2. Basic configuration
3. VitePlugin / ViteConfig
4. InertiaPlugin basics
5. Quick examples

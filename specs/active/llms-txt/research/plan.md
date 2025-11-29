# Research Plan: LLMs.txt Documentation Files

**Slug**: llms-txt
**Created**: 2025-11-28

---

## Research Objectives

1. **Understand llms.txt specification** - Master the format, structure, and best practices
2. **Study examples** - Review excellent implementations in similar projects
3. **Extract content** - Gather all necessary information from litestar-vite codebase
4. **Plan structure** - Design optimal organization for both files
5. **Establish token counting** - Determine method to verify llms.txt size
6. **Validate approach** - Ensure implementation will meet LLM consumption needs

---

## Research Questions

### Architecture & Design

- [ ] How should dual Python/TypeScript APIs be structured in llms.txt?
  - Research similar full-stack frameworks
  - Check if separation should be by section or interleaved
  - Determine best practices for multi-language projects

- [ ] What's the optimal level of detail for llms.txt vs llms-full.txt?
  - llms.txt: Links vs inline content?
  - llms-full.txt: How comprehensive? Every parameter?
  - Balance between brevity and usefulness

- [ ] Are there similar implementations in other Python + JS projects?
  - WebSearch: "FastAPI llms.txt"
  - WebSearch: "Django React llms.txt"
  - WebSearch: "full-stack framework llms.txt"

### Specification Deep Dive

- [ ] What is the exact required format?
  - Context7/WebSearch: llms.txt specification
  - Required sections vs optional sections
  - H1, blockquote, H2 structure rules
  - Link format requirements

- [ ] How should the "Optional" section be used?
  - What goes in optional vs main sections?
  - Examples from other projects

- [ ] Are there validation tools for llms.txt format?
  - WebSearch: "llms.txt validator"
  - Check if specification provides tools

### Library/Framework Specific

- [ ] How does Litestar handle plugin documentation?
  - Context7: `/litestar-org/litestar` - topic: "plugins"
  - Review existing Litestar plugin documentation patterns

- [ ] What Vite plugin documentation patterns exist?
  - Context7: `/vitejs/vite` - topic: "plugin api"
  - Review how other Vite plugins document

- [ ] How is Inertia.js typically documented?
  - Context7: Inertia.js documentation
  - Focus: Integration patterns, API structure

### Best Practices

- [ ] What's the current best practice for llms.txt in 2025?
  - WebSearch: "llms.txt best practices 2025"
  - WebSearch: "llms.txt python project examples"
  - Focus: Content organization, token optimization

- [ ] How do other projects solve dual-language documentation?
  - WebSearch: "multi-language project documentation llms"
  - Look for Python + TypeScript/JavaScript examples

- [ ] What token counting methods are most accurate?
  - WebSearch: "token counting markdown python"
  - Research: tiktoken library
  - Research: GPT tokenizer tools

### Content Extraction

- [ ] What APIs must be documented?
  - Review all public classes and functions
  - Identify critical vs optional content

- [ ] What examples are most valuable?
  - Review examples directory
  - Identify most common use cases
  - Determine which to include inline vs link

---

## Research Sources

### Priority 1: Specification

| Source | Purpose | Status |
|--------|---------|--------|
| https://llmstxt.org/ | Official specification | [ ] |
| https://github.com/AnswerDotAI/llms-txt | Reference implementation | [ ] |
| https://www.answer.ai/posts/2024-09-03-llmstxt.html | Original blog post | [ ] |

### Priority 2: Internal Codebase

| Source | Purpose | Status |
|--------|---------|--------|
| `README.md` | Project overview, features, quick start | [ ] |
| `pyproject.toml` | Metadata, version, dependencies | [ ] |
| `src/py/litestar_vite/config.py` | ViteConfig API | [ ] |
| `src/py/litestar_vite/plugin.py` | VitePlugin API | [ ] |
| `src/py/litestar_vite/inertia/config.py` | InertiaConfig API | [ ] |
| `src/py/litestar_vite/inertia/plugin.py` | InertiaPlugin API | [ ] |
| `src/py/litestar_vite/inertia/response.py` | InertiaResponse API | [ ] |
| `src/py/litestar_vite/inertia/request.py` | InertiaRequest API | [ ] |
| `src/py/litestar_vite/inertia/middleware.py` | InertiaMiddleware API | [ ] |
| `src/py/litestar_vite/loader.py` | ViteAssetLoader API | [ ] |
| `src/py/litestar_vite/cli.py` | CLI commands | [ ] |
| `src/js/src/index.ts` | TypeScript plugin API | [ ] |
| `examples/basic/` | Basic usage examples | [ ] |
| `examples/inertia/` | Inertia.js examples | [ ] |
| `examples/spa-react/` | React SPA examples | [ ] |

### Priority 3: Context7 Library Documentation

| Library | Topic | Tokens | Status |
|---------|-------|--------|--------|
| Litestar | plugins, configuration | 5000 | [ ] |
| Vite | plugin api, configuration | 5000 | [ ] |
| Inertia.js | protocol, integration | 3000 | [ ] |

### Priority 4: WebSearch

| Query | Purpose | Status |
|-------|---------|--------|
| "llms.txt python project examples 2025" | Find excellent examples | [ ] |
| "llms.txt best practices documentation" | Best practices | [ ] |
| "llms.txt full-stack project examples" | Multi-language examples | [ ] |
| "token counting markdown python" | Token counting methods | [ ] |
| "llms.txt validator tools" | Validation tools | [ ] |

### Priority 5: Documentation Site

| Source | Purpose | Status |
|--------|---------|--------|
| https://litestar-org.github.io/litestar-vite/ | Official documentation | [ ] |

---

## Findings

### llms.txt Specification

**Source**: https://llmstxt.org/, WebSearch results

**Key Insights**:
- Markdown format with specific structure
- Required: H1 title, blockquote summary
- Recommended: H2 sections with links
- Optional section for less critical content
- Purpose: Filter out navigation, CSS, JS for LLM consumption
- ~2000 token limit for concise version (recommendation, not hard requirement)

**Required Format**:
```markdown
# Project Name

> Brief summary

Additional context

## Section
- [Link](url): Description

## Optional
- [Link](url): Optional content
```

**Implications for Implementation**:
- Must strictly follow this structure
- Clear separation between required and optional content
- Links can point to documentation or inline content in llms-full.txt

---

### Token Counting

**Source**: To be researched

**Key Insights**:
- (To be filled during research)

**Implementation**:
```python
# Token counting approach (TBD)
```

**Notes**: (To be added)

---

### Multi-Language Documentation

**Source**: To be researched

**Key Insights**:
- (To be filled during research)

**Patterns Discovered**:
- (To be added)

---

### Python API Documentation

**Source**: Source code analysis

**ViteConfig** (src/py/litestar_vite/config.py):
- (To be extracted during research)
- Fields with types and defaults
- Docstrings for each field

**VitePlugin** (src/py/litestar_vite/plugin.py):
- (To be extracted during research)
- Methods and signatures
- Usage patterns

**InertiaConfig** (src/py/litestar_vite/inertia/config.py):
- (To be extracted during research)

**InertiaPlugin** (src/py/litestar_vite/inertia/plugin.py):
- (To be extracted during research)

**Other APIs**:
- (To be documented as researched)

---

### TypeScript API Documentation

**Source**: src/js/src/index.ts

**Key Insights**:
- (To be extracted during research)
- Plugin configuration options
- Exported functions
- Type definitions

---

### Code Examples

**Source**: examples/ directory

**SPA Mode (React)**:
- (To be extracted from examples/spa-react/)
- Configuration pattern
- Key code snippets

**Template Mode**:
- (To be extracted from examples/)
- Jinja2 integration
- Asset loading

**Inertia Mode**:
- (To be extracted from examples/inertia/)
- Complete setup
- Backend + frontend integration

---

## Patterns Discovered

### Pattern: Dual-Language API Documentation

**Use When**: Documenting projects with both Python and TypeScript components

**Implementation**:
```markdown
## Python API
- [VitePlugin](#python-viteplugin): Litestar plugin for Vite integration
- [ViteConfig](#python-viteconfig): Configuration options

## TypeScript API
- [@litestar/vite-plugin](#ts-plugin): Vite plugin for Litestar
```

**Notes**: Clear separation with section headers prevents confusion

---

### Pattern: Concise vs Comprehensive Split

**Use When**: Balancing brevity (llms.txt) with completeness (llms-full.txt)

**llms.txt Approach**:
- High-level overview only
- Links to full documentation
- Essential configuration

**llms-full.txt Approach**:
- Complete API reference
- Inline code examples
- All configuration options

**Notes**: llms.txt acts as navigation, llms-full.txt as reference

---

## Decisions Based on Research

| Question | Decision | Rationale |
|----------|----------|-----------|
| File location | Repository root | Specification requirement |
| Format structure | H1, blockquote, H2 sections | Specification requirement |
| Python/TypeScript separation | Separate H2 sections | Clear organization for dual-language project |
| Token counting method | (TBD during research) | Need to research best approach |
| Inline vs linked examples | llms.txt: links, llms-full.txt: inline | Balance brevity with completeness |

---

## Unresolved Questions

- What is the most accurate token counting method for markdown?
- How detailed should llms-full.txt API signatures be?
- Should we include internal classes or only public APIs?
- How to handle deprecation notices?
- Should configuration examples show all options or common patterns?

---

## Next Steps

Based on research:

1. **Complete specification study** - Read all specification sources thoroughly
2. **Extract Python APIs** - Document all public classes and methods from source
3. **Extract TypeScript APIs** - Document plugin configuration and exports
4. **Gather examples** - Extract working code from examples directory
5. **Study similar projects** - Learn from excellent llms.txt implementations
6. **Determine token counting** - Choose and test token counting method
7. **Create content outline** - Plan detailed structure for both files
8. **Begin implementation** - Start with llms.txt structure, then fill content

---

## Research Log

| Timestamp | Action | Finding |
|-----------|--------|---------|
| 2025-11-28 | Initial WebSearch | Found llms.txt specification format |
| 2025-11-28 | Read PRD | Identified all research needs |
| | | |

---

## Research Completion Checklist

### Specification Understanding
- [ ] Read https://llmstxt.org/ completely
- [ ] Review GitHub repo examples
- [ ] Understand required vs optional sections
- [ ] Document format requirements

### Example Projects
- [ ] Find 3+ excellent Python project llms.txt files
- [ ] Find 1+ full-stack project llms.txt files
- [ ] Document patterns observed
- [ ] Note what works well

### Content Extraction
- [ ] Extract all ViteConfig fields
- [ ] Extract all VitePlugin methods
- [ ] Extract all InertiaConfig fields
- [ ] Extract all InertiaPlugin methods
- [ ] Extract CLI commands
- [ ] Extract TypeScript API
- [ ] Gather code examples

### Tools & Methods
- [ ] Determine token counting method
- [ ] Test token counter
- [ ] Identify markdown linter (optional)
- [ ] Identify link checker (optional)

### Design Decisions
- [ ] Decide on section structure
- [ ] Decide on Python/TypeScript organization
- [ ] Decide on example presentation
- [ ] Decide on level of detail for each file
- [ ] Create content outline

---

## Templates for Research Findings

### When Researching Example Projects

**Project**: [Project Name]
**URL**: [llms.txt URL]
**What Works Well**:
- Structure choice
- Level of detail
- Example presentation

**What to Avoid**:
- Issues observed
- Confusion points

**Applicable to litestar-vite**:
- Patterns we should adopt

---

### When Extracting API Documentation

**Class/Function**: [Name]
**File**: [path]
**Signature**:
```python
# Code signature
```

**Description**: [From docstring]

**Key Parameters**:
- param1: type - description
- param2: type - description

**Example**:
```python
# Usage example
```

**Include in**:
- [ ] llms.txt (brief mention)
- [ ] llms-full.txt (complete API)

---

## Success Criteria for Research Phase

Research is complete when:

- [x] llms.txt specification fully understood
- [x] 3+ example projects reviewed
- [x] All Python APIs documented
- [x] All TypeScript APIs documented
- [x] Code examples gathered
- [x] Token counting method chosen
- [x] Content outline created
- [x] Design decisions documented

After research, proceed to Phase 3: Implementation.

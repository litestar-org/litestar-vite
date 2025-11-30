# PRD: LLMs.txt Documentation Files

## Overview

| Field | Value |
|-------|-------|
| **Slug** | llms-txt |
| **Created** | 2025-11-28 |
| **Status** | Draft |
| **Author** | PRD Agent |

---

## Problem Statement

Large Language Models (LLMs) need structured, easily parseable documentation to understand and assist with codebases. The litestar-vite project currently lacks LLM-optimized documentation files. The [llms.txt specification](https://llmstxt.org/) provides a standard format for making documentation LLM-friendly by filtering out non-essential content (navigation, CSS, JavaScript) and presenting information in a structured markdown format.

Without llms.txt files, LLMs must parse complex documentation sites, READMEs, and source code to understand the project. This is inefficient and can lead to incomplete or inaccurate understanding. Additionally, litestar-vite has a unique dual-language architecture (Python + TypeScript) that requires special attention in documentation structure.

**Current Pain Points:**
- LLMs have to parse multiple sources to understand the project
- No concise overview for quick LLM comprehension
- No comprehensive single-file reference for deep integration work
- Dual Python/TypeScript nature not clearly documented for LLMs
- API documentation scattered across multiple files

---

## Goals

1. **Create llms.txt** - A concise (~2000 tokens) overview following the official specification format
2. **Create llms-full.txt** - A comprehensive reference with complete API documentation
3. **Cover Dual Architecture** - Document both Python (litestar_vite) and TypeScript (@litestar/vite-plugin) components
4. **Follow Specification** - Strictly adhere to llms.txt format (H1, blockquote, H2 sections, links)
5. **Enable LLM Understanding** - Make it easy for LLMs to understand installation, configuration, and usage
6. **Provide Code Examples** - Include practical examples for common use cases
7. **Maintain Accuracy** - Ensure all API signatures and examples match current codebase (v0.14.0)
8. **Create Sync Command** - Provide `/sync-llms-txt` command for both Claude and Gemini agents to maintain files

---

## Deliverable: sync-llms-txt Command

A maintenance command must be created for both Claude (`.claude/commands/sync-llms-txt.md`) and Gemini (`.gemini/commands/sync-llms-txt.toml`) that:

### Command Purpose

The command thoroughly assesses every entry in the existing llms.txt and llms-full.txt files to ensure they remain accurate and complete.

### Command Behavior

1. **Validation Phase**
   - Parse both llms.txt and llms-full.txt
   - Identify all documented APIs, configurations, and patterns
   - Cross-reference against current source code

2. **Removal Phase** - Remove anything no longer valid:
   - Deprecated APIs or methods
   - Removed configuration options
   - Outdated code examples
   - Broken or invalid links
   - References to deleted files or features

3. **Addition Phase** - Add anything missing:
   - New public APIs
   - New configuration options
   - New CLI commands
   - New integration patterns
   - New examples from examples/ directory

4. **Update Phase** - Update anything potentially out of date:
   - Changed API signatures
   - Updated default values
   - Modified behavior descriptions
   - Version references
   - Dependency information

5. **Optimization Phase** (llms.txt only):
   - Optimize for LLM searchability
   - Ensure context optimization (most important info first)
   - Verify token count stays under 2000
   - Improve section organization for discoverability

6. **Pattern Completeness** (llms-full.txt only):
   - Ensure all common patterns are documented
   - Add missing integration examples
   - Complete troubleshooting section
   - Include all configuration combinations

### Output

The command should produce:
- Updated llms.txt (if changes needed)
- Updated llms-full.txt (if changes needed)
- Summary of changes made (additions, removals, updates)
- Validation report

---

## Non-Goals

- Replacing the main documentation site
- Including every configuration option in llms.txt (only key ones; full coverage in llms-full.txt)
- Interactive documentation or tutorials
- Internal implementation details (focus on public APIs)
- Examples for every possible framework combination (focus on most common)
- Version-specific documentation (covers current version only)
- Migration guides from other frameworks

---

## Acceptance Criteria

### Format & Structure
- [ ] llms.txt exists at repository root
- [ ] llms-full.txt exists at repository root
- [ ] Both files follow llms.txt specification format:
  - [ ] H1 title
  - [ ] Blockquote summary
  - [ ] Brief description section
  - [ ] H2 sections with links and descriptions
  - [ ] Optional section clearly marked
- [ ] Valid markdown syntax (no linting errors)

### Content Requirements
- [ ] llms.txt is concise (~2000 tokens maximum)
- [ ] llms-full.txt is comprehensive with complete API reference
- [ ] Both files cover:
  - [ ] Python API (VitePlugin, ViteConfig, InertiaPlugin, InertiaConfig)
  - [ ] TypeScript API (@litestar/vite-plugin)
  - [ ] Installation instructions
  - [ ] Configuration examples
  - [ ] Code examples
- [ ] llms-full.txt includes:
  - [ ] Complete API signatures
  - [ ] All configuration options
  - [ ] Multiple usage examples
  - [ ] Inertia.js integration details
  - [ ] Type generation workflow
  - [ ] Dev proxy architecture
  - [ ] Troubleshooting patterns

### Accuracy & Quality
- [ ] All API signatures match current source code
- [ ] All code examples are syntactically correct
- [ ] All links are valid
- [ ] Content reflects v0.14.0 features
- [ ] No outdated or deprecated information
- [ ] Examples are tested or extracted from working code

### Quality Gates
- [ ] Files are readable by LLMs (manual verification)
- [ ] Token count for llms.txt verified (<2000)
- [ ] Markdown linting passes (if linter added)
- [ ] All links verified
- [ ] Code examples tested

### Sync Command Requirements
- [ ] `.claude/commands/sync-llms-txt.md` exists
- [ ] `.gemini/commands/sync-llms-txt.toml` exists
- [ ] Command validates all documented entries against source code
- [ ] Command identifies and removes invalid/outdated content
- [ ] Command adds missing APIs, configs, and patterns
- [ ] Command optimizes llms.txt for searchability
- [ ] Command ensures llms-full.txt has complete patterns
- [ ] Command produces a change summary

---

## Technical Approach

### Architecture

This is a pure documentation task with no code changes. The implementation involves:

1. **Content Extraction** - Gather documentation from multiple sources:
   - README.md for overview
   - Source code docstrings for API documentation
   - Examples directory for code samples
   - pyproject.toml for metadata

2. **Content Organization** - Structure according to llms.txt specification:
   - llms.txt: High-level overview, links to key sections
   - llms-full.txt: Inline comprehensive documentation

3. **Dual Language Representation** - Clear separation and labeling of:
   - Python APIs (litestar_vite package)
   - TypeScript APIs (@litestar/vite-plugin)

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `llms.txt` | Add | Concise LLM-friendly documentation (~2000 tokens) |
| `llms-full.txt` | Add | Comprehensive LLM-friendly documentation (unlimited) |
| `.claude/commands/sync-llms-txt.md` | Add | Claude command to sync/maintain llms.txt files |
| `.gemini/commands/sync-llms-txt.toml` | Add | Gemini command to sync/maintain llms.txt files |

### Content Structure

#### llms.txt Structure

```markdown
# Litestar Vite

> Brief summary of project in 1-2 sentences

Additional context about dual Python/TypeScript nature

## Quick Start
- [Installation](#installation): pip install litestar-vite
- [Basic Configuration](#config): Python setup examples

## Python API
- [VitePlugin](#viteplugin): Main plugin class
- [ViteConfig](#viteconfig): Configuration options
- [InertiaPlugin](#inertiaplugin): Inertia.js integration

## TypeScript API
- [@litestar/vite-plugin](#ts-plugin): Vite plugin for Litestar

## Examples
- [SPA Mode](#spa): React/Vue/Svelte examples
- [Template Mode](#template): Jinja2 examples
- [Inertia Mode](#inertia): Full-stack SPA examples

## Optional
- [Advanced Topics](#advanced): Type generation, proxy modes
```

#### llms-full.txt Structure

Includes everything from llms.txt PLUS:

1. **Complete Python API Reference**
   - ViteConfig: All fields with types and descriptions
   - VitePlugin: All methods with signatures
   - InertiaConfig: All fields with types and descriptions
   - InertiaPlugin: All methods with signatures
   - InertiaResponse, InertiaRequest, InertiaMiddleware: Complete API
   - ViteAssetLoader: Methods and usage
   - CLI Commands: All commands with options

2. **Complete TypeScript API Reference**
   - Vite plugin configuration options
   - Helper functions
   - Type definitions

3. **Comprehensive Examples**
   - SPA mode with React
   - SPA mode with Vue
   - Template mode with Jinja2
   - Inertia.js integration
   - Type generation workflow
   - Custom configuration

4. **Configuration Guide**
   - All environment variables
   - Dev mode vs production mode
   - Proxy modes (proxy vs direct)
   - Asset loading strategies

5. **Integration Patterns**
   - React integration
   - Vue integration
   - Svelte integration
   - HTMX integration

### Content Sources

| Source | Purpose |
|--------|---------|
| `/README.md` | Overview, quick start, features |
| `/pyproject.toml` | Package metadata, version |
| `/src/py/litestar_vite/config.py` | ViteConfig API |
| `/src/py/litestar_vite/plugin.py` | VitePlugin API |
| `/src/py/litestar_vite/inertia/config.py` | InertiaConfig API |
| `/src/py/litestar_vite/inertia/plugin.py` | InertiaPlugin API |
| `/src/py/litestar_vite/inertia/response.py` | InertiaResponse API |
| `/src/py/litestar_vite/inertia/request.py` | InertiaRequest API |
| `/src/py/litestar_vite/inertia/middleware.py` | InertiaMiddleware API |
| `/src/py/litestar_vite/loader.py` | ViteAssetLoader API |
| `/src/py/litestar_vite/cli.py` | CLI commands |
| `/src/js/src/index.ts` | TypeScript plugin API |
| `/examples/basic/` | Basic usage example |
| `/examples/vue-inertia/` | Inertia.js example |
| Official docs site | Additional patterns and guides |

---

## Testing Strategy

### Manual Verification

1. **Format Validation**
   - Verify llms.txt follows specification structure
   - Verify llms-full.txt follows specification structure
   - Check H1, blockquote, H2 sections are correct

2. **Token Count Validation**
   - Count tokens in llms.txt using token counter
   - Ensure under 2000 token limit
   - Optimize if needed

3. **Markdown Validation**
   - Check for syntax errors
   - Validate code block formatting
   - Ensure proper escaping

4. **Link Validation**
   - Check all external links are accessible
   - Check all internal anchors resolve correctly

5. **Code Example Validation**
   - Verify Python examples are syntactically correct
   - Verify TypeScript examples are syntactically correct
   - Cross-reference with actual working examples

6. **LLM Testing**
   - Test with Claude by asking it questions about litestar-vite
   - Test with GPT by asking it to help with integration
   - Verify LLM can understand and use the documentation

### Automated Validation (Optional Enhancement)

Could add:
- Python script to validate llms.txt format structure
- Token counter to check llms.txt size
- Markdown linter (markdownlint)
- Link checker tool
- Code syntax validator

### Edge Cases

- [ ] Empty sections handling (should not occur)
- [ ] Very long code examples (split if needed)
- [ ] Special characters in markdown (proper escaping)
- [ ] Links to non-existent anchors (validate all)
- [ ] Version references (ensure current)

---

## Research Questions

Questions for Expert agent to investigate:

### llms.txt Best Practices

- [ ] What are examples of excellent llms.txt files in Python projects?
  - WebSearch: "llms.txt python project examples 2025"
- [ ] How do other full-stack projects handle dual-language documentation?
  - WebSearch: "llms.txt multi-language project examples"
- [ ] What level of detail is appropriate for llms.txt vs llms-full.txt?
  - Review existing llms.txt implementations
- [ ] Should code examples be inline or linked?
  - Check specification and best practices

### Content Structure

- [ ] How to structure dual Python/TypeScript API documentation?
  - Review similar projects (FastAPI + JS, Django + React)
- [ ] What sections are most valuable for LLMs?
  - Research LLM documentation consumption patterns
- [ ] How to handle versioning information?
  - Check specification recommendations

### Technical Implementation

- [ ] Best token counting method for markdown?
  - Research: tiktoken, GPT tokenizers
- [ ] How to extract API documentation from Python docstrings?
  - Review existing source code documentation
- [ ] Should we include type hints in API signatures?
  - Check Python documentation standards

### Validation

- [ ] What markdown linters work best for llms.txt?
  - Research: markdownlint, remark-lint
- [ ] How to validate llms.txt format programmatically?
  - Could create simple parser

---

## Dependencies

### No New Dependencies Required

This is a pure documentation task requiring no new packages.

### Optional Dependencies (Future Enhancement)

- `markdownlint-cli` - Markdown linting
- `tiktoken` - Token counting for validation
- Link checker tool - Validate all links

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| llms.txt exceeds 2000 token limit | Medium | Medium | Use token counter during creation, iteratively reduce content, prioritize most important info |
| Content becomes outdated as codebase evolves | High | High | Add version indicator, document in PRD that this needs updates with releases |
| Incorrect API signatures or examples | High | Low | Extract directly from source code, validate against working examples |
| Poor organization makes files hard for LLMs to parse | Medium | Low | Strictly follow llms.txt specification, test with actual LLMs |
| Missing critical information | Medium | Medium | Review against all major features, cross-reference with main documentation |
| Links become broken | Low | Medium | Use relative links where possible, validate all external links |
| Code examples have syntax errors | High | Low | Copy from working examples directory, validate syntax |
| Dual-language structure confuses LLMs | Medium | Low | Clearly label Python vs TypeScript sections, use consistent formatting |

---

## Timeline Estimate

| Phase | Estimated Effort |
|-------|------------------|
| Research | 1-2 hours - Study specification, review examples, extract content |
| llms.txt Creation | 1 hour - Draft concise version, optimize for token limit |
| llms-full.txt Creation | 2-3 hours - Comprehensive API documentation, examples |
| Validation & Testing | 1 hour - Format check, token count, LLM testing, link validation |
| Revisions | 1 hour - Based on validation feedback |
| **Total** | **6-8 hours** |

---

## Open Questions

None at this time. All requirements are clear.

If during implementation we discover ambiguities, they will be documented in the recovery.md file.

---

## References

### Specification

- [llms.txt Official Specification](https://llmstxt.org/)
- [Answer.AI Blog Post on llms.txt](https://www.answer.ai/posts/2024-09-03-llmstxt.html)
- [GitHub: AnswerDotAI/llms-txt](https://github.com/AnswerDotAI/llms-txt)

### Project Documentation

- [Litestar Vite Documentation](https://litestar-org.github.io/litestar-vite/)
- [Litestar Documentation](https://docs.litestar.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [Inertia.js Documentation](https://inertiajs.com/)

### Related

- [Semrush: What Is LLMs.txt](https://www.semrush.com/blog/llms-txt/)
- [Analytics Vidhya: LLMs.txt Explained](https://www.analyticsvidhya.com/blog/2025/03/llms-txt/)

---

## Success Criteria Summary

Before completing this feature:

1. Both files exist and follow specification format
2. llms.txt is under 2000 tokens
3. All content is accurate to v0.14.0
4. Both Python and TypeScript APIs are documented
5. Code examples are validated
6. Files are tested with LLMs
7. All links are validated
8. Markdown is properly formatted

This PRD provides a comprehensive guide for implementing LLM-friendly documentation for the litestar-vite project.

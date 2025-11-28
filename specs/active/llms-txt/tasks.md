# Tasks: LLMs.txt Documentation Files

**Slug**: llms-txt
**PRD**: [prd.md](./prd.md)
**Last Updated**: 2025-11-28

---

## Phase 1: Planning & Research

- [x] Create PRD
- [x] Identify affected components
- [x] Define acceptance criteria
- [x] Set up workspace

---

## Phase 2: Expert Research

### Specification Understanding

- [ ] Study llms.txt specification format in detail
  - Read: https://llmstxt.org/
  - Read: https://github.com/AnswerDotAI/llms-txt
  - Focus: Required structure, token limits, best practices

### Best Practices Research

- [ ] Research llms.txt examples in Python projects
  - WebSearch: "llms.txt python project examples 2025"
  - WebSearch: "llms.txt best practices documentation"
  - Focus: Content structure, level of detail

- [ ] Research multi-language project llms.txt files
  - WebSearch: "llms.txt full-stack project examples"
  - Focus: How to structure dual Python/TypeScript documentation

- [ ] Study token counting for markdown
  - Research: tiktoken library
  - Research: GPT tokenizer tools
  - Focus: Method to verify llms.txt stays under 2000 tokens

### Content Extraction

- [ ] Extract overview content from README.md
  - File: `/README.md`
  - Extract: Features, installation, quick start

- [ ] Extract Python API documentation
  - File: `/src/py/litestar_vite/config.py`
    - Extract: ViteConfig class, all fields, docstrings
  - File: `/src/py/litestar_vite/plugin.py`
    - Extract: VitePlugin class, methods, docstrings
  - File: `/src/py/litestar_vite/inertia/config.py`
    - Extract: InertiaConfig class, all fields
  - File: `/src/py/litestar_vite/inertia/plugin.py`
    - Extract: InertiaPlugin class, methods
  - File: `/src/py/litestar_vite/inertia/response.py`
    - Extract: InertiaResponse class
  - File: `/src/py/litestar_vite/inertia/request.py`
    - Extract: InertiaRequest class
  - File: `/src/py/litestar_vite/inertia/middleware.py`
    - Extract: InertiaMiddleware class
  - File: `/src/py/litestar_vite/loader.py`
    - Extract: ViteAssetLoader class, methods
  - File: `/src/py/litestar_vite/cli.py`
    - Extract: CLI commands, options

- [ ] Extract TypeScript API documentation
  - File: `/src/js/src/index.ts`
    - Extract: Plugin configuration, exports
  - File: `/src/js/src/inertia-helpers/`
    - Extract: Helper functions if relevant

- [ ] Gather code examples
  - Review: `/examples/basic/`
  - Review: `/examples/inertia/`
  - Review: `/examples/spa-react/`
  - Extract: Configuration patterns, usage examples

### Documentation Review

- [ ] Review official documentation site
  - Visit: https://cofin.github.io/litestar-vite/
  - Note: Key patterns, common configurations
  - Extract: Any critical information not in source

---

## Phase 3: Core Implementation

### Create llms.txt (Concise Version)

- [ ] Draft llms.txt structure
  - H1: Project title
  - Blockquote: 1-2 sentence summary
  - Brief description: Project overview, dual-language note

- [ ] Add Quick Start section (H2)
  - Installation command
  - Basic Python configuration example
  - Link to full documentation

- [ ] Add Python API section (H2)
  - VitePlugin overview + link
  - ViteConfig overview + link
  - InertiaPlugin overview + link
  - InertiaConfig overview + link

- [ ] Add TypeScript API section (H2)
  - @litestar/vite-plugin overview + link
  - Basic configuration example

- [ ] Add Examples section (H2)
  - SPA mode example (brief)
  - Template mode example (brief)
  - Inertia mode example (brief)

- [ ] Add Optional section (H2)
  - Advanced topics links
  - Type generation
  - Proxy modes

- [ ] Optimize for token count
  - Count tokens using tool/script
  - Ensure under 2000 tokens
  - Remove non-essential content if needed
  - Prioritize most important information

### Create llms-full.txt (Comprehensive Version)

- [ ] Copy llms.txt as base
  - Start with same structure
  - Expand each section

- [ ] Expand Quick Start section
  - Detailed installation instructions
  - Complete configuration examples
  - All supported modes (SPA, Template, Inertia)

- [ ] Expand Python API section
  - **ViteConfig**
    - All fields with types
    - Description for each field
    - Default values
    - Example configurations
  - **VitePlugin**
    - Class signature
    - Methods with signatures
    - Usage examples
  - **InertiaConfig**
    - All fields with types
    - Description for each field
    - Default values
  - **InertiaPlugin**
    - Class signature
    - Methods with signatures
    - Integration example
  - **InertiaResponse**
    - Constructor signature
    - Methods
    - Usage patterns
  - **InertiaRequest**
    - Available properties
    - Helper methods
  - **InertiaMiddleware**
    - How it works
    - Configuration
  - **ViteAssetLoader**
    - Methods
    - Asset loading patterns
  - **CLI Commands**
    - All commands with full options
    - Examples for each command

- [ ] Expand TypeScript API section
  - Plugin configuration options
  - All parameters with types
  - Helper functions
  - Integration examples

- [ ] Add comprehensive examples
  - SPA mode with React (complete)
  - SPA mode with Vue (complete)
  - Template mode with Jinja2 (complete)
  - Inertia.js integration (complete)
  - Type generation workflow (complete)

- [ ] Add configuration reference
  - All environment variables
  - Dev mode vs production
  - Proxy mode options (proxy vs direct)
  - Asset loading strategies
  - Hot module replacement (HMR)

- [ ] Add integration patterns
  - React integration details
  - Vue integration details
  - Svelte integration details
  - HTMX integration details

- [ ] Add troubleshooting section
  - Common issues and solutions
  - Debugging tips
  - FAQ items

---

## Phase 4: Integration & Validation

### Format Validation

- [ ] Validate llms.txt format
  - Verify H1 title exists
  - Verify blockquote summary exists
  - Verify H2 sections are structured correctly
  - Verify Optional section is present and labeled

- [ ] Validate llms-full.txt format
  - Same format checks as llms.txt

### Token Count Validation

- [ ] Count tokens in llms.txt
  - Use token counter tool
  - Verify under 2000 tokens
  - Document actual count

- [ ] Optimize if over limit
  - Remove least important content
  - Condense examples
  - Use more links, less inline content

### Markdown Validation

- [ ] Check markdown syntax
  - No syntax errors
  - Code blocks properly formatted
  - Links properly formatted
  - Proper escaping of special characters

- [ ] Optional: Run markdown linter
  - Install markdownlint-cli if desired
  - Fix any linting issues

### Link Validation

- [ ] Check all external links
  - llmstxt.org
  - Documentation site
  - GitHub links
  - Litestar docs
  - Vite docs

- [ ] Check all internal anchors
  - Ensure all section references work
  - Test in markdown viewer

### Code Example Validation

- [ ] Validate Python examples
  - Check syntax
  - Cross-reference with working examples
  - Ensure imports are correct

- [ ] Validate TypeScript examples
  - Check syntax
  - Cross-reference with working examples
  - Ensure types are correct

### Content Accuracy Validation

- [ ] Verify API signatures match source
  - ViteConfig fields
  - VitePlugin methods
  - InertiaConfig fields
  - InertiaPlugin methods
  - CLI commands

- [ ] Verify examples match current version
  - Check against v0.14.0 codebase
  - Ensure no deprecated features

### LLM Testing

- [ ] Test with Claude
  - Ask questions about litestar-vite
  - Ask for integration help
  - Verify it can use llms.txt effectively

- [ ] Test with GPT (if available)
  - Ask similar questions
  - Compare understanding quality

---

## Phase 4.5: Create Sync Commands

### Create Claude Command

- [ ] Create `.claude/commands/sync-llms-txt.md`
  - Define command purpose and workflow
  - Include validation phase instructions
  - Include removal phase for outdated content
  - Include addition phase for missing content
  - Include update phase for stale content
  - Include optimization instructions for llms.txt
  - Include pattern completeness checks for llms-full.txt
  - Define output format and change summary

### Create Gemini Command

- [ ] Create `.gemini/commands/sync-llms-txt.toml`
  - Mirror Claude command functionality
  - Follow Gemini TOML command format
  - Include all phases: validate, remove, add, update, optimize
  - Define expected outputs

### Sync Command Validation

- [ ] Test Claude command manually
  - Verify it parses existing files correctly
  - Verify it identifies test discrepancies
  - Verify output format is clear

- [ ] Test Gemini command manually
  - Same validations as Claude command

---

## Phase 5: Testing (Auto-invoked)

### Validation Tests

- [ ] Format validation test
  - Python script to verify llms.txt structure
  - Check H1, blockquote, H2 sections programmatically

- [ ] Token count test
  - Script to count tokens
  - Assert llms.txt < 2000 tokens
  - Document token count in test output

- [ ] Link validation test
  - Check all external URLs return 200
  - Validate all internal anchors exist

- [ ] Markdown syntax test
  - Parse markdown successfully
  - No parsing errors

### Manual Verification

- [ ] Human review of content
  - Accuracy check
  - Completeness check
  - Clarity check

- [ ] LLM comprehension test
  - Manual testing with Claude/GPT
  - Verify useful responses

---

## Phase 6: Documentation (Auto-invoked)

### Project Documentation

- [ ] Update CLAUDE.md if needed
  - Note: llms.txt files exist
  - Note: How to update them

- [ ] Update README.md if needed
  - Add note about llms.txt support
  - Link to llms.txt specification

- [ ] Consider adding to docs site
  - Link to llms.txt and llms-full.txt
  - Explain their purpose

### Maintenance Documentation

- [ ] Document update process
  - When to update llms.txt files
  - How to verify token count
  - How to validate format

- [ ] Add version indicator
  - Note current version in files
  - Document that updates are needed with releases

---

## Phase 7: Quality Gate & Archive

### Quality Checks

- [ ] Both files exist at repository root
- [ ] llms.txt follows specification format
- [ ] llms-full.txt follows specification format
- [ ] llms.txt is under 2000 tokens
- [ ] All links are valid
- [ ] All code examples are syntactically correct
- [ ] Content matches v0.14.0
- [ ] Markdown syntax is valid
- [ ] Files tested with LLMs

### Sync Command Quality Checks

- [ ] `.claude/commands/sync-llms-txt.md` exists
- [ ] `.gemini/commands/sync-llms-txt.toml` exists
- [ ] Commands cover all phases (validate, remove, add, update, optimize)
- [ ] Commands produce clear change summaries
- [ ] Commands tested and functional

### Anti-Pattern Scan

- [ ] No broken links
- [ ] No syntax errors in code examples
- [ ] No outdated version references
- [ ] No missing sections per specification
- [ ] Proper markdown escaping

### Completion

- [ ] All acceptance criteria met
- [ ] Token count documented
- [ ] LLM testing completed successfully
- [ ] Files are accurate and complete
- [ ] Workspace archived to `specs/archive/llms-txt/`

---

## Progress Log

| Date | Phase | Status | Notes |
|------|-------|--------|-------|
| 2025-11-28 | Planning | Complete | PRD created, workspace set up |
| | | | |

---

## Blockers

| Blocker | Status | Resolution |
|---------|--------|------------|
| None | N/A | N/A |

---

## Notes

### Token Counting Strategy

For token counting, we can use one of:
1. Online tool: OpenAI tokenizer
2. Python library: `tiktoken`
3. Approximate: ~4 characters per token (rough estimate)

### Content Priority for llms.txt

If we need to optimize for token limit, priority order:
1. Installation and basic config (must have)
2. VitePlugin and ViteConfig (must have)
3. InertiaPlugin basics (must have)
4. TypeScript plugin basics (should have)
5. Detailed examples (nice to have - can link instead)
6. Advanced features (nice to have - can link instead)

### Maintenance Plan

After initial creation:
- Review llms.txt files with each major release
- Update API changes
- Update version references
- Re-validate token count
- Consider adding CI check for token count

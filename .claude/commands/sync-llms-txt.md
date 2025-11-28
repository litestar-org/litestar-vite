# Sync LLMs.txt Documentation

You are an LLM documentation synchronization agent. Your mission is to thoroughly assess and update the `llms.txt` and `llms-full.txt` files to ensure they remain accurate, complete, and optimized for any repository.

## Files to Sync

- `llms.txt` - Concise overview (~2000 tokens max)
- `llms-full.txt` - Comprehensive documentation

## Your Workflow

Execute these phases in order:

---

## Phase 0: Project Discovery - Detect Project Structure

Before syncing, you must understand the project. Automatically detect the project type, languages, and structure.

### Detect Project Type and Languages

**Check for Python projects:**

```
- pyproject.toml → Modern Python project (check [project] or [tool.poetry])
- setup.py → Legacy Python project
- requirements.txt → Python dependencies
- Pipfile → Pipenv project
- poetry.lock → Poetry project
- uv.lock → uv project
```

**Check for JavaScript/TypeScript projects:**

```
- package.json → Node.js project (check "type", "main", "module", dependencies)
- tsconfig.json → TypeScript project
- bun.lockb → Bun project
- pnpm-lock.yaml → pnpm project
- yarn.lock → Yarn project
- package-lock.json → npm project
```

**Check for other languages:**

```
- Cargo.toml → Rust project
- go.mod → Go project
- Gemfile → Ruby project
- pom.xml / build.gradle → Java project
- *.csproj / *.sln → .NET project
- mix.exs → Elixir project
- pubspec.yaml → Dart/Flutter project
```

### Detect Frameworks

**Python frameworks (check imports and dependencies):**

```
- litestar, starlette, fastapi → ASGI frameworks
- django → Django
- flask → Flask
- aiohttp → aiohttp
- pytest → Testing framework
- click, typer → CLI frameworks
```

**JavaScript frameworks (check package.json dependencies):**

```
- react, next → React ecosystem
- vue, nuxt → Vue ecosystem
- svelte, sveltekit → Svelte ecosystem
- angular → Angular
- express, fastify, hono → Node.js servers
- vite, webpack, esbuild → Build tools
```

### Map Source Code Structure

**Find source directories:**

```
Common patterns:
- src/, lib/, app/ → Source code
- tests/, test/, __tests__/ → Test code
- examples/, samples/ → Example code
- docs/, documentation/ → Documentation
- scripts/, bin/ → Utility scripts
```

**Identify public APIs:**

```
Python:
- Classes without underscore prefix
- Functions without underscore prefix
- __all__ exports
- Public modules (not _private.py)

JavaScript/TypeScript:
- export statements
- module.exports
- Named exports in index files
```

### Extract Project Metadata

**From pyproject.toml:**

```
- name, version, description
- dependencies
- optional-dependencies
- scripts/commands
```

**From package.json:**

```
- name, version, description
- dependencies, devDependencies
- scripts
- main, module, exports
```

### Build Project Inventory

Create a mental map of:

1. **Languages**: Python, TypeScript, JavaScript, etc.
2. **Frameworks**: What frameworks are in use
3. **Source Structure**: Where code lives
4. **Public APIs**: Classes, functions, types to document
5. **CLI Commands**: Any command-line interfaces
6. **Configuration**: Config classes, options, env vars
7. **Examples**: Example projects or code samples
8. **Documentation**: Existing docs to reference

---

## Phase 1: Validation - Parse and Inventory

### Read Current Documentation

1. Read `llms.txt` and extract all documented items:
   - API classes and methods mentioned
   - Configuration options listed
   - Code examples provided
   - Links referenced

2. Read `llms-full.txt` and extract all documented items:
   - Complete API signatures
   - All configuration fields
   - All code examples
   - All patterns and integrations

### Cross-Reference Against Source

For each documented item, verify it exists in the current source code using the project inventory from Phase 0.

**For Python APIs:**

- Grep for class definitions: `class ClassName`
- Grep for function definitions: `def function_name`
- Check if public (no underscore prefix)
- Verify method signatures match

**For JavaScript/TypeScript APIs:**

- Grep for exports: `export function`, `export class`, `export const`
- Check index files for re-exports
- Verify type definitions match

**For Examples:**

- Verify referenced example directories exist
- Check example code matches current patterns
- Ensure examples are runnable

---

## Phase 2: Removal - Clean Invalid Content

Remove any content that is no longer valid:

### Items to Remove

- [ ] **Deprecated APIs**: Methods or classes that no longer exist
- [ ] **Removed Options**: Configuration fields that were deleted
- [ ] **Outdated Examples**: Code that no longer works
- [ ] **Broken Links**: URLs that return 404 or redirect incorrectly
- [ ] **Deleted Features**: References to removed functionality
- [ ] **Old Version Info**: Outdated version numbers or requirements

### Document Removals

For each removal, note:

```
REMOVED: [item name]
REASON: [why it was removed]
LOCATION: [where it was in the file]
```

---

## Phase 3: Addition - Add Missing Content

Add any content that should be documented but isn't:

### Sources to Check for New Content

1. **New APIs** (based on detected languages):
   - Scan source directories for public classes/functions
   - Look for exported types and interfaces
   - Check docstrings/JSDoc for documentation

2. **New CLI Commands**:
   - Check for click/typer decorators (Python)
   - Check for commander/yargs usage (Node.js)
   - Review package.json scripts

3. **New Examples**:
   - List all directories in examples/
   - Ensure each example type is represented

4. **New Configuration Options**:
   - Check dataclass/pydantic fields (Python)
   - Check TypeScript interfaces for config
   - Look for environment variable support

### Document Additions

For each addition, note:

```
ADDED: [item name]
SOURCE: [where it was found]
SECTION: [where it was added in llms.txt/llms-full.txt]
```

---

## Phase 4: Update - Refresh Stale Content

Update any content that may be out of date:

### Items to Check and Update

- [ ] **API Signatures**: Ensure method signatures match source code
- [ ] **Default Values**: Verify default values are current
- [ ] **Type Annotations**: Confirm types are accurate
- [ ] **Behavior Descriptions**: Update if functionality changed
- [ ] **Version References**: Update version numbers (check pyproject.toml/package.json)
- [ ] **Dependency Info**: Update required dependencies
- [ ] **Code Examples**: Ensure examples use current syntax

### Document Updates

For each update, note:

```
UPDATED: [item name]
OLD: [previous content]
NEW: [updated content]
REASON: [why it changed]
```

---

## Phase 5: Optimize llms.txt

Optimize the concise `llms.txt` for LLM searchability and context efficiency:

### Searchability Optimization

1. **Keywords First**: Ensure important keywords appear early in descriptions
2. **Action Verbs**: Use clear action verbs (configure, install, integrate)
3. **Common Queries**: Anticipate what users will ask LLMs about:
   - "How do I install [project]?"
   - "How do I configure [project]?"
   - "How do I use [feature]?"
   - "What are the main APIs?"

### Context Optimization

1. **Priority Order**: Most important information first
2. **Quick Start Prominent**: Installation and basic setup easily findable
3. **Links vs Inline**: Use links for details, inline for essentials
4. **Section Headers**: Clear, descriptive H2 headers

### Token Budget

1. Count approximate tokens (rough: 4 chars = 1 token)
2. Ensure total is under 2000 tokens
3. If over budget, prioritize:
   - Installation (must have)
   - Basic configuration (must have)
   - Core APIs overview (must have)
   - Examples (can link instead)
   - Advanced features (move to llms-full.txt)

---

## Phase 6: Ensure Pattern Completeness (llms-full.txt)

Ensure `llms-full.txt` has all necessary patterns based on detected project type:

### Universal Patterns

- [ ] **Installation**: All installation methods (pip, npm, etc.)
- [ ] **Configuration**: All configuration options with types and defaults
- [ ] **Core APIs**: Complete API reference with signatures
- [ ] **CLI Commands**: All commands with options and examples
- [ ] **Error Handling**: Common errors and solutions
- [ ] **Environment Variables**: All supported env vars

### Language-Specific Patterns

**Python Projects:**

- [ ] Type hints and annotations
- [ ] Async/await patterns (if applicable)
- [ ] Plugin/extension patterns
- [ ] Testing patterns

**JavaScript/TypeScript Projects:**

- [ ] ESM vs CommonJS usage
- [ ] Type definitions
- [ ] Build configuration
- [ ] Framework integration

### Integration Examples

Based on detected frameworks, ensure examples for:

- [ ] Each major use case
- [ ] Each supported framework integration
- [ ] Development vs production setup
- [ ] Common customization patterns

### Troubleshooting Section

- [ ] Common configuration errors
- [ ] Build issues and solutions
- [ ] Development environment problems
- [ ] Production deployment issues

---

## Phase 7: Generate Report

Produce a summary of all changes:

```markdown
# LLMs.txt Sync Report

**Date**: [current date]
**Project**: [project name from metadata]
**Version**: [version from pyproject.toml/package.json]

## Project Detection Summary

- **Languages**: [detected languages]
- **Frameworks**: [detected frameworks]
- **Source Structure**: [source directories found]

## Sync Summary

- **Removals**: [count]
- **Additions**: [count]
- **Updates**: [count]

## Detailed Changes

### Removed
[list all removals with reasons]

### Added
[list all additions with sources]

### Updated
[list all updates with before/after]

## Validation

- [ ] llms.txt under 2000 tokens: [actual count]
- [ ] All links verified
- [ ] All code examples validated
- [ ] Pattern coverage complete

## Recommendations

[Any suggestions for future improvements]
```

---

## Important Guidelines

1. **Be Thorough**: Check every single documented item
2. **Be Conservative**: Only remove items you're certain are invalid
3. **Be Accurate**: Verify all additions against source code
4. **Be Concise**: Keep llms.txt within token budget
5. **Be Complete**: Ensure llms-full.txt covers all patterns
6. **Document Everything**: Produce a clear change report
7. **Be Generic**: Don't assume project structure - discover it

## Start the Sync

1. First, run Phase 0 to discover the project structure
2. Read both llms.txt and llms-full.txt (if they exist)
3. If files don't exist, create them based on the project inventory
4. Systematically work through each phase
5. Generate the final report

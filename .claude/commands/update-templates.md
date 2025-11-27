# Update Framework Templates

You are a framework template auditor for litestar-vite. Your mission is to review each frontend framework template and ensure it complies with the latest standards and best practices for that framework.

## Templates Location

All templates are in `src/py/litestar_vite/templates/`:

- **react/** - React with Vite
- **react-inertia/** - React with Inertia.js
- **vue/** - Vue 3 with Vite
- **vue-inertia/** - Vue 3 with Inertia.js
- **svelte/** - Svelte 5 with Vite
- **svelte-inertia/** - Svelte 5 with Inertia.js
- **sveltekit/** - SvelteKit
- **nuxt/** - Nuxt 3
- **astro/** - Astro
- **htmx/** - HTMX with Vite
- **base/** - Shared base templates (package.json, tsconfig.json)
- **addons/** - Optional addons (TailwindCSS)

## Your Workflow

For EACH framework template:

### 1. Research Current Standards

Use WebSearch to find the latest:
- Official documentation for the framework
- Current recommended project structure
- Latest package versions
- Best practices and patterns
- Breaking changes in recent versions

### 2. Review Template Files

Read all template files for the framework:
- Configuration files (vite.config.ts, tsconfig.json, framework-specific configs)
- Entry points (main.ts/tsx, index.html)
- Component files
- Style files

### 3. Compare Against Standards

Check for:
- Outdated dependencies or version ranges
- Deprecated APIs or patterns
- Missing recommended configurations
- Incorrect file structures
- Non-standard naming conventions

### 4. Report Findings

For each framework, provide a summary:

```
## [Framework Name]

**Status**: [Up to date | Needs updates]

**Current State**:
- [Brief description of what the template provides]

**Findings**:
- [List any issues found, or "No issues found - template follows current best practices"]

**Recommended Changes** (if any):
- [Specific changes needed with rationale]
```

### 5. Apply Updates (if needed)

If changes are needed:
1. Make the minimal necessary changes
2. Preserve Jinja2 template variables ({{ variable }})
3. Test that templates still render correctly
4. Update any version numbers in base/package.json.j2 if needed

## Important Guidelines

- **DO NOT** update templates that are already compliant
- **DO NOT** make changes just for style preferences
- **ONLY** update for actual compatibility issues, deprecations, or security concerns
- **PRESERVE** all Jinja2 templating syntax
- **DOCUMENT** the rationale for any changes made

## Frameworks to Check

Process these in order:
1. React (react/, react-inertia/)
2. Vue (vue/, vue-inertia/)
3. Svelte (svelte/, svelte-inertia/, sveltekit/)
4. Nuxt (nuxt/)
5. Astro (astro/)
6. HTMX (htmx/)
7. Base templates (base/)
8. Addons (addons/)

## Final Summary

After reviewing all templates, provide a consolidated summary:

```
# Template Audit Summary

**Templates Up to Date**: [list]
**Templates Updated**: [list with brief description of changes]
**No Action Needed**: [list]

## Changes Made
[Detailed list of all file changes with rationale]
```

Begin the audit now. Be thorough but conservative - only make changes that are truly necessary.

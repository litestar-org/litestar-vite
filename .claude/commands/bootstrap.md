---
description: Bootstrap AI development infrastructure for any project (Intelligent Edition)
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, mcp__sequential-thinking__sequentialthinking, mcp__pal__planner, mcp__pal__thinkdeep
---

# Project Bootstrap Command - Intelligent Edition

**Version**: 2.0 | **Bootstrap Framework**: litestar-vite

You are bootstrapping AI development infrastructure for this project. This command creates an **intelligent, adaptive agent system** that:

- **Context-Aware Analysis** - Agents understand project patterns before acting
- **Adaptive Checkpoints** - Workflow depth adjusts to task complexity
- **Knowledge Synthesis** - Automatic pattern extraction and documentation
- **Intelligent Tool Selection** - MCP tool usage based on task requirements
- **Quality Enforcement** - Multi-tier validation with graceful degradation
- **Self-Documenting** - Captures learnings for future agent sessions
- **Cross-Agent Memory** - Shared knowledge base evolves over time

**Philosophy**: Agents should learn from the codebase, not just execute commands.

---

## Table of Contents

1. [Bootstrap Philosophy](#part-1-bootstrap-philosophy)
2. [Intelligent Project Analysis](#part-2-intelligent-project-analysis)
3. [MCP Tool Detection](#part-3-mcp-tool-detection)
4. [Adaptive Infrastructure](#part-4-adaptive-infrastructure)
5. [Generation Phase](#part-5-generation-phase)
6. [Alignment Mode](#part-6-alignment-mode)
7. [Verification](#part-7-verification)
8. [Embedded Templates](#part-8-embedded-templates)
9. [Framework Knowledge Base](#part-9-framework-knowledge-base)

---

## Part 1: Bootstrap Philosophy

### Intelligence Principles

1. **Context First, Code Second**
   - Read existing patterns before creating new ones
   - Understand project conventions from actual code
   - Adapt to project's unique architectural style

2. **Adaptive Complexity**
   - Simple tasks get streamlined workflows
   - Complex features trigger deep analysis
   - Checkpoint count scales with complexity

3. **Knowledge Accumulation**
   - Every feature adds to project guides
   - Patterns become reusable templates
   - Future agents inherit all learnings

4. **Graceful Degradation**
   - Missing tools trigger fallback strategies
   - Optional features don't block progress
   - Clear communication when capabilities limited

---

## Part 2: Intelligent Project Analysis

### Step 2.1: Deep Codebase Understanding

**Don't just detect - understand WHY patterns exist:**

```bash
# Detect project structure
ls -la
find . -type f \( -name "*.py" -o -name "*.ts" -o -name "*.go" -o -name "*.rs" \) | head -30

# Read configuration to understand philosophy
cat pyproject.toml package.json Cargo.toml go.mod 2>/dev/null | head -100
```

**Key questions to answer:**

1. **Architecture Philosophy**:
   - Is this a monolith or microservices?
   - Does it use domain-driven design?
   - What's the layering strategy (controller → service → repository)?

2. **Type System Approach**:
   - Strict typing or dynamic?
   - Type hints usage patterns?
   - Validation strategy (runtime vs compile-time)?

3. **Testing Philosophy**:
   - TDD or test-after?
   - Unit vs integration test ratio?
   - Coverage expectations?

4. **Code Organization**:
   - Feature-based or layer-based folders?
   - Naming conventions (verb_noun vs noun_verb)?
   - File size preferences?

### Step 2.2: Extract Existing Patterns

**Read actual code to discover patterns:**

```bash
# Find adapter/plugin patterns
find src/ -type f \( -name "*adapter*" -o -name "*plugin*" -o -name "*extension*" \) 2>/dev/null

# Find service patterns
find src/ -type f \( -name "*service*" -o -name "*manager*" -o -name "*handler*" \) 2>/dev/null

# Find configuration patterns
find src/ -type f \( -name "*config*" -o -name "*settings*" \) 2>/dev/null

# Find error handling patterns
grep -r "class.*Error" src/ 2>/dev/null | head -10
grep -r "raise.*from" src/ 2>/dev/null | head -10

# Find async patterns
grep -r "async def" src/ 2>/dev/null | wc -l
grep -r "await" src/ 2>/dev/null | wc -l
```

**Pattern Analysis**:

1. **Read 3-5 example files** for each pattern type
2. **Identify common structure** (class hierarchy, decorators, mixins)
3. **Note naming conventions** (verbs, prefixes, suffixes)
4. **Extract docstring style** (Google, NumPy, reStructuredText)
5. **Understand error handling** (custom exceptions, context managers)

### Step 2.3: Language & Framework Detection

**Python Detection:**

```bash
# Web frameworks
grep -i "litestar" pyproject.toml 2>/dev/null && echo "PY_LITESTAR=true"
grep -i "fastapi" pyproject.toml 2>/dev/null && echo "PY_FASTAPI=true"
grep -i "flask" pyproject.toml 2>/dev/null && echo "PY_FLASK=true"
grep -i "django" pyproject.toml 2>/dev/null && echo "PY_DJANGO=true"

# Database/ORM
grep -i "sqlalchemy" pyproject.toml 2>/dev/null && echo "PY_SQLALCHEMY=true"
grep -i "advanced-alchemy" pyproject.toml 2>/dev/null && echo "PY_ADVANCED_ALCHEMY=true"

# Testing
grep -i "pytest" pyproject.toml 2>/dev/null && echo "PY_PYTEST=true"
grep -i "pytest-asyncio" pyproject.toml 2>/dev/null && echo "PY_PYTEST_ASYNCIO=true"

# Linting
grep -i "ruff" pyproject.toml 2>/dev/null && echo "PY_RUFF=true"
grep -i "mypy" pyproject.toml 2>/dev/null && echo "PY_MYPY=true"
```

**JavaScript/TypeScript Detection:**

```bash
# UI Frameworks
grep '"react"' package.json 2>/dev/null && echo "JS_REACT=true"
grep '"vue"' package.json 2>/dev/null && echo "JS_VUE=true"
grep '"svelte"' package.json 2>/dev/null && echo "JS_SVELTE=true"
grep '"@angular/core"' package.json 2>/dev/null && echo "JS_ANGULAR=true"

# Build tools
grep '"vite"' package.json 2>/dev/null && echo "JS_VITE=true"

# Integration
grep '"@inertiajs"' package.json 2>/dev/null && echo "JS_INERTIA=true"
grep '"htmx.org"' package.json 2>/dev/null && echo "JS_HTMX=true"

# Testing
grep '"vitest"' package.json 2>/dev/null && echo "JS_VITEST=true"
grep '"jest"' package.json 2>/dev/null && echo "JS_JEST=true"

# Linting
grep '"biome"' package.json 2>/dev/null && echo "JS_BIOME=true"
grep '"eslint"' package.json 2>/dev/null && echo "JS_ESLINT=true"
```

### Step 2.4: Domain-Specific Pattern Detection

**Multi-Adapter/Driver Pattern Detection:**

```bash
# Look for adapter or driver patterns
adapters_found=$(grep -r "class.*Adapter" src/ 2>/dev/null | wc -l)
drivers_found=$(grep -r "class.*Driver" src/ 2>/dev/null | wc -l)

# Common adapter directory patterns
test -d src/adapters && echo "HAS_ADAPTERS_DIR=true"
test -d src/drivers && echo "HAS_DRIVERS_DIR=true"
test -d src/backends && echo "HAS_BACKENDS_DIR=true"
```

**Service Layer Pattern Detection:**

```bash
services_found=$(grep -r "class.*Service" src/ 2>/dev/null | wc -l)
repositories_found=$(grep -r "class.*Repository" src/ 2>/dev/null | wc -l)
```

### Step 2.5: Code Style Detection

```bash
# Python type hint style
grep -r "Optional\[" src/ 2>/dev/null | head -5 && echo "STYLE_OPTIONAL=true"
grep -r "| None" src/ 2>/dev/null | head -5 && echo "STYLE_PEP604=true"

# Future annotations
grep -r "from __future__ import annotations" src/ 2>/dev/null && echo "STYLE_FUTURE_ANNOTATIONS=true"

# Test style
grep -r "class Test" tests/ 2>/dev/null | head -3 && echo "STYLE_CLASS_TESTS=true"
grep -r "^def test_" tests/ 2>/dev/null | head -3 && echo "STYLE_FUNC_TESTS=true"

# Docstring style (sample first docstring)
grep -A2 '"""' src/*.py 2>/dev/null | head -10
```

### Step 2.6: CI/CD Detection

```bash
# Detect CI/CD systems
test -d .github/workflows && echo "CI_GITHUB_ACTIONS=true"
test -f .gitlab-ci.yml && echo "CI_GITLAB=true"
test -f .circleci/config.yml && echo "CI_CIRCLECI=true"
test -f Jenkinsfile && echo "CI_JENKINS=true"
```

### Step 2.7: Build Detection Profile

Compile all detections into a profile document.

---

## Part 3: MCP Tool Detection

### Step 3.1: Create MCP Tool Detection Script

```bash
mkdir -p .claude/tools
cat > .claude/tools/detect_mcp.py << 'EOF'
#!/usr/bin/env python3
"""Intelligent MCP tool detection with capability mapping."""

from dataclasses import dataclass
from enum import Enum


class ToolCapability(Enum):
    """MCP tool capability categories."""
    REASONING = "reasoning"
    RESEARCH = "research"
    PLANNING = "planning"
    ANALYSIS = "analysis"
    DEBUG = "debug"


@dataclass
class MCPTool:
    """MCP tool with capability metadata."""
    name: str
    available: bool
    capability: ToolCapability
    fallback: str | None = None
    use_cases: list[str] | None = None


def detect_mcp_tools() -> dict[str, MCPTool]:
    """Detect available MCP tools with intelligent fallback mapping."""

    tools = {
        'sequential_thinking': MCPTool(
            name='sequential_thinking',
            available=True,  # Usually available
            capability=ToolCapability.REASONING,
            fallback=None,
            use_cases=[
                'Linear problem breakdown',
                'Step-by-step analysis',
                'Complex feature planning',
            ]
        ),
        'context7': MCPTool(
            name='context7',
            available=True,
            capability=ToolCapability.RESEARCH,
            fallback='web_search',
            use_cases=[
                'Library documentation lookup',
                'API reference retrieval',
                'Best practices research',
            ]
        ),
        'web_search': MCPTool(
            name='web_search',
            available=True,
            capability=ToolCapability.RESEARCH,
            fallback=None,
            use_cases=[
                'Latest framework updates',
                'Community best practices',
                'Fallback documentation lookup',
            ]
        ),
        'zen_planner': MCPTool(
            name='zen_planner',
            available=True,
            capability=ToolCapability.PLANNING,
            use_cases=[
                'Multi-phase project planning',
                'Migration strategy design',
                'Complex feature breakdown',
            ]
        ),
        'zen_thinkdeep': MCPTool(
            name='zen_thinkdeep',
            available=True,
            capability=ToolCapability.ANALYSIS,
            use_cases=[
                'Architecture review',
                'Performance analysis',
                'Security assessment',
            ]
        ),
        'zen_analyze': MCPTool(
            name='zen_analyze',
            available=True,
            capability=ToolCapability.ANALYSIS,
            use_cases=[
                'Code quality analysis',
                'Pattern detection',
                'Tech debt assessment',
            ]
        ),
        'zen_debug': MCPTool(
            name='zen_debug',
            available=True,
            capability=ToolCapability.DEBUG,
            use_cases=[
                'Root cause investigation',
                'Bug reproduction',
                'Performance debugging',
            ]
        ),
    }

    return tools


def generate_tool_strategy(tools: dict[str, MCPTool]) -> str:
    """Generate intelligent tool usage strategy."""

    strategy = ["# MCP Tool Strategy\\n\\n"]
    strategy.append("## Tool Selection Guide\\n\\n")

    strategy.append("### Reasoning Tools\\n")
    strategy.append("- **Primary**: sequential_thinking\\n")
    strategy.append("- **Use for**: Complex analysis, step-by-step planning\\n\\n")

    strategy.append("### Research Tools\\n")
    strategy.append("- **Primary**: context7\\n")
    strategy.append("- **Fallback**: web_search\\n")
    strategy.append("- **Use for**: Library docs, best practices\\n\\n")

    strategy.append("### Planning Tools\\n")
    strategy.append("- **Primary**: zen_planner\\n")
    strategy.append("- **Use for**: Multi-phase projects, migrations\\n\\n")

    strategy.append("### Analysis Tools\\n")
    strategy.append("- **Primary**: zen_thinkdeep, zen_analyze\\n")
    strategy.append("- **Use for**: Architecture review, code quality\\n\\n")

    return "".join(strategy)


if __name__ == "__main__":
    tools = detect_mcp_tools()
    strategy = generate_tool_strategy(tools)

    print("MCP Tool Detection Complete")
    print(strategy)
EOF

chmod +x .claude/tools/detect_mcp.py
```

### Step 3.2: Create MCP Strategy Document

```bash
cat > .claude/mcp-strategy.md << 'EOF'
# MCP Tool Strategy

## Tool Selection by Task Type

### Complex Architectural Decisions
1. **Primary**: mcp__pal__thinkdeep
2. **Fallback**: mcp__sequential-thinking__sequentialthinking

### Library Documentation Lookup
1. **Primary**: mcp__context7__get-library-docs
2. **Fallback**: WebSearch

### Multi-Phase Planning
1. **Primary**: mcp__pal__planner
2. **Fallback**: Manual structured thinking

### Code Analysis
1. **Primary**: mcp__pal__analyze
2. **Fallback**: Manual code review

### Debugging
1. **Primary**: mcp__pal__debug
2. **Fallback**: Manual investigation

## Complexity-Based Selection

### Simple Features (6 checkpoints)
- Use basic tools
- Manual analysis acceptable
- Focus on speed

### Medium Features (8 checkpoints)
- Use sequential_thinking (12 steps)
- Include pattern analysis
- Moderate depth

### Complex Features (10+ checkpoints)
- Use zen_thinkdeep or zen_planner
- Deep pattern analysis
- Comprehensive research
EOF
```

---

## Part 4: Adaptive Infrastructure

### Step 4.1: Create Intelligent Directory Structure

```bash
# Create Claude directories
mkdir -p .claude/commands
mkdir -p .claude/agents
mkdir -p .claude/skills
mkdir -p .claude/tools

# Create specs directories with pattern library
mkdir -p specs/guides/patterns
mkdir -p specs/guides/workflows
mkdir -p specs/guides/examples
mkdir -p specs/active
mkdir -p specs/archive
mkdir -p specs/template-spec/research
mkdir -p specs/template-spec/tmp
mkdir -p specs/template-spec/patterns

# Create .gitkeep files
touch specs/active/.gitkeep
touch specs/archive/.gitkeep
touch specs/guides/patterns/.gitkeep
touch specs/guides/examples/.gitkeep
```

### Step 4.2: Create Adaptive Quality Gates

```bash
cat > specs/guides/quality-gates.yaml << 'EOF'
metadata:
  version: "2.0"
  adaptive: true
  description: "Quality gates that adapt to project conventions"

implementation_gates:
  - name: local_tests_pass
    command: "make test"
    fallback: "pytest tests/"
    required: true
    adaptive: true
    description: "All tests must pass before proceeding"

  - name: linting_clean
    command: "make lint"
    fallback: "ruff check ."
    required: true
    description: "Zero linting errors allowed"

  - name: type_checking_pass
    command: "mypy src/"
    required: true
    adaptive: true
    description: "Type checking must pass"

testing_gates:
  - name: coverage_threshold
    threshold: 90
    scope: "modified_modules"
    adaptive: true
    description: "Modified modules must achieve configured coverage"

  - name: test_isolation
    required: true
    description: "Tests must work in parallel execution"

  - name: n_plus_one_detection
    type: "custom"
    applicable_when: "database_operations"
    description: "Database operations must include N+1 query detection tests"

documentation_gates:
  - name: anti_pattern_scan
    adaptive: true
    rules:
      - pattern: "from __future__ import annotations"
        severity: "error"
        message: "Use explicit stringification instead"

      - pattern: "Optional\\["
        severity: "error"
        message: "Use T | None (PEP 604) instead"

      - pattern: "class Test"
        severity: "warning"
        message: "Prefer function-based tests"

  - name: pattern_documentation
    description: "New patterns must be captured in specs/guides/patterns/"
    required: true
EOF
```

### Step 4.3: Create Pattern Library README

```bash
cat > specs/guides/patterns/README.md << 'EOF'
# Pattern Library

This directory contains reusable patterns extracted from completed features.

## How Patterns Are Captured

1. During implementation, new patterns are documented in `tmp/new-patterns.md`
2. During review, patterns are extracted to this directory
3. Future PRD phases consult this library first

## Pattern Categories

### Architectural Patterns
- Plugin patterns
- Service patterns
- Adapter patterns

### Type Handling Patterns
- Type converters
- Schema mappings
- Validation patterns

### Testing Patterns
- Fixture patterns
- Mock strategies
- Integration test setups

### Error Handling Patterns
- Exception hierarchies
- Recovery strategies
- Logging patterns

## Using Patterns

When starting a new feature:

1. Search this directory for similar patterns
2. Read pattern documentation before implementation
3. Follow established conventions
4. Add new patterns during review phase
EOF
```

---

## Part 5: Generation Phase

### Step 5.1: Generate CLAUDE.md

Create the main Claude instructions file using detected project information.

### Step 5.2: Generate Intelligent Commands

Generate 6 core slash commands with intelligence enhancements:

1. **prd.md** - PRD creation with pattern learning
2. **implement.md** - Pattern-guided implementation
3. **test.md** - Testing with pattern compliance
4. **review.md** - Quality gate and pattern extraction
5. **explore.md** - Codebase exploration
6. **fix-issue.md** - GitHub issue fixing

### Step 5.3: Generate Agents

Generate 4 subagent definitions with intelligence layers:

1. **prd.md** - PRD specialist with pattern recognition
2. **expert.md** - Implementation with pattern compliance
3. **testing.md** - Test creation with coverage targets
4. **docs-vision.md** - Documentation and pattern extraction

### Step 5.4: Generate Skills

For each detected framework, generate a skill file with:
- Quick reference code examples
- Project-specific patterns (from detection)
- Context7 lookup references
- Related files in project

### Step 5.5: Generate Settings

Create `.claude/settings.local.json` with permissions based on detected build system.

---

## Part 6: Alignment Mode

When existing bootstrap is detected, use alignment mode.

### Step 6.1: Inventory Existing Configuration

```bash
# List existing commands
ls .claude/commands/*.md 2>/dev/null

# List existing skills
ls -d .claude/skills/*/ 2>/dev/null

# List existing agents
ls .claude/agents/*.md 2>/dev/null

# Check CLAUDE.md version
head -5 CLAUDE.md 2>/dev/null | grep "Version"

# Check pattern library
ls specs/guides/patterns/*.md 2>/dev/null
```

### Step 6.2: Identify Missing Components

Compare existing vs expected:

**Core commands (must exist)**:
- prd.md, implement.md, test.md, review.md, explore.md, fix-issue.md

**Core agents (must exist)**:
- prd.md, expert.md, testing.md, docs-vision.md

**Pattern library (should exist)**:
- specs/guides/patterns/README.md
- Quality gates: specs/guides/quality-gates.yaml

### Step 6.3: Preserve Custom Content

Before updating:
1. Read existing content
2. Identify custom sections
3. Store for preservation
4. Merge into updated file

### Step 6.4: Update Report

```markdown
## Alignment Report

### New Components to Add
- [ ] Skill: {new detected framework}
- [ ] Command: {missing core command}
- [ ] Pattern library structure

### Updates Available
- [ ] CLAUDE.md version {old} → {new}
- [ ] Intelligence enhancements
- [ ] Pattern library setup

### Custom Content Preserved
- Command: {custom command name}
- Skill: {custom skill name}

Proceed with updates? [Y/n]
```

---

## Part 7: Verification

### Step 7.1: Validate Generated Files

```bash
# Check all expected files exist
test -f CLAUDE.md && echo "✓ CLAUDE.md"
test -d .claude/commands && echo "✓ .claude/commands/"
test -d .claude/agents && echo "✓ .claude/agents/"
test -d .claude/skills && echo "✓ .claude/skills/"
test -f .claude/settings.local.json && echo "✓ settings.local.json"
test -d specs/guides && echo "✓ specs/guides/"
test -d specs/guides/patterns && echo "✓ specs/guides/patterns/"
test -f specs/guides/quality-gates.yaml && echo "✓ quality-gates.yaml"
test -d specs/active && echo "✓ specs/active/"

# Count generated files
echo "Commands: $(ls .claude/commands/*.md 2>/dev/null | wc -l)"
echo "Agents: $(ls .claude/agents/*.md 2>/dev/null | wc -l)"
echo "Skills: $(ls -d .claude/skills/*/ 2>/dev/null | wc -l)"
```

### Step 7.2: Summary Report

```markdown
## Bootstrap Complete ✓ (Intelligent Edition)

### Generated Configuration

**CLAUDE.md**: Main AI instructions
- Tech Stack: {detected stack}
- Commands: {count}
- Skills: {count}
- Intelligence Layer: Enabled

**Commands Created**:
- /prd - Create PRD with pattern learning (adaptive checkpoints)
- /implement - Pattern-guided implementation
- /test - Testing with coverage targets (90%+)
- /review - Quality gate and pattern extraction
- /explore - Explore codebase
- /fix-issue - Fix GitHub issue
- /bootstrap - Re-bootstrap (alignment mode)

**Agents Created**:
- prd - PRD creation with pattern recognition
- expert - Implementation with pattern compliance
- testing - Test creation specialist
- docs-vision - Documentation and pattern extraction

**Skills Created**:
{list of framework skills}

**Intelligence Infrastructure**:
- specs/guides/patterns/ - Pattern library
- specs/guides/quality-gates.yaml - Adaptive quality gates
- .claude/mcp-strategy.md - Tool selection guide
- .claude/tools/detect_mcp.py - MCP detection script

### Intelligence Features

✓ **Pattern-First Implementation**: Agents identify similar implementations before coding
✓ **Adaptive Checkpoints**: Simple=6, Medium=8, Complex=10+ checkpoints
✓ **Knowledge Accumulation**: Patterns extracted to library after each feature
✓ **Quality Gate Adaptation**: Standards adjust to project norms
✓ **Tool Strategy**: MCP tools selected based on task requirements

### Next Steps

1. Review generated CLAUDE.md
2. Run `/explore` to test configuration
3. Start development with `/prd [feature]`
4. Patterns accumulate in specs/guides/patterns/
```

---

## Part 8: Embedded Templates

### Template: CLAUDE.md (Intelligent Edition)

```markdown
# AI Agent Guidelines for {PROJECT_NAME}

**Version**: 2.0 (Intelligent Edition) | **Updated**: {DATE}

{PROJECT_DESCRIPTION}

---

## Intelligence Layer

This project uses an **intelligent agent system** that:

1. **Learns from codebase** before making changes
2. **Adapts workflow depth** based on feature complexity
3. **Accumulates knowledge** in pattern library
4. **Selects tools** based on task requirements

### Pattern Library

Reusable patterns in `specs/guides/patterns/`:
- Consult before implementing similar features
- Add new patterns during review phase

### Complexity-Based Checkpoints

| Complexity | Checkpoints | Triggers |
|------------|-------------|----------|
| Simple | 6 | CRUD, config change, single file |
| Medium | 8 | New service, API endpoint, 2-3 files |
| Complex | 10+ | Architecture change, multi-component |

---

## Quick Reference

### Technology Stack

| Backend | Frontend |
|---------|----------|
| {BACKEND_TECH} | {FRONTEND_TECH} |
| {BACKEND_TEST} | {FRONTEND_TEST} |
| {BACKEND_LINT} | {FRONTEND_LINT} |
| {BACKEND_PKG} | {FRONTEND_PKG} |

### Essential Commands

```bash
{INSTALL_CMD}    # Install all dependencies
{TEST_CMD}       # Run all tests
{LINT_CMD}       # Run linting
{FIX_CMD}        # Auto-format code
```

---

## Code Standards (Critical)

### {PRIMARY_LANGUAGE}

| Rule | Standard |
|------|----------|
| Type hints | {TYPE_HINT_STYLE} |
| Docstrings | {DOCSTRING_STYLE} |
| Tests | {TEST_STYLE} |
| Line length | {LINE_LENGTH} characters |

---

## Slash Commands

| Command | Description |
|---------|-------------|
| `/prd [feature]` | Create PRD with pattern learning |
| `/implement [slug]` | Pattern-guided implementation |
| `/test [slug]` | Testing with 90%+ coverage |
| `/review [slug]` | Quality gate and pattern extraction |
| `/explore [topic]` | Explore codebase |
| `/fix-issue [#]` | Fix GitHub issue |
| `/bootstrap` | Re-bootstrap (alignment mode) |

---

## Subagents

| Agent | Mission |
|-------|---------|
| `prd` | PRD creation with pattern recognition |
| `expert` | Implementation with pattern compliance |
| `testing` | Test creation (90%+ coverage) |
| `docs-vision` | Quality gates and pattern extraction |

---

## Development Workflow

### For New Features (Pattern-First)

1. **PRD**: `/prd [feature]` - Analyzes 3-5 similar features first
2. **Implement**: `/implement [slug]` - Follows identified patterns
3. **Test**: Auto-invoked - Tests pattern compliance
4. **Review**: Auto-invoked - Extracts new patterns to library

### Quality Gates

All code must pass:
- [ ] `{TEST_CMD}` passes
- [ ] `{LINT_CMD}` passes
- [ ] 90%+ coverage for modified modules
- [ ] Pattern compliance verified
- [ ] No anti-patterns

---

## MCP Tools

### Tool Selection

Consult `.claude/mcp-strategy.md` for task-based tool selection.

### Context7 (Library Docs)

```python
mcp__context7__resolve-library-id(libraryName="{PRIMARY_FRAMEWORK}")
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="{CONTEXT7_ID}",
    topic="...",
    mode="code"
)
```

### Sequential Thinking (Analysis)

```python
mcp__sequential-thinking__sequentialthinking(
    thought="Step 1: ...",
    thought_number=1,
    total_thoughts=15,  # Adapt to complexity
    next_thought_needed=True
)
```

### Zen Tools

- `mcp__pal__planner` - Multi-phase planning
- `mcp__pal__thinkdeep` - Deep analysis
- `mcp__pal__analyze` - Code analysis
- `mcp__pal__debug` - Debugging

---

## Anti-Patterns (Must Avoid)

{ANTI_PATTERNS_TABLE}

---

## Pattern Library

Location: `specs/guides/patterns/`

### Using Patterns

1. Search pattern library before implementation
2. Follow established conventions
3. Document deviations with rationale

### Adding Patterns

1. Document in `tmp/new-patterns.md` during implementation
2. Extract to pattern library during review
3. Update this guide if architectural patterns
```

### Template: Intelligent prd.md Command

```markdown
---
description: Create a PRD with pattern learning and adaptive complexity
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch, mcp__context7__resolve-library-id, mcp__context7__get-library-docs, mcp__sequential-thinking__sequentialthinking, mcp__pal__planner
---

# Intelligent PRD Creation Workflow

You are creating a Product Requirements Document for: **$ARGUMENTS**

## Intelligence Layer (ACTIVATE FIRST)

Before starting checkpoints:

1. **Read MCP Strategy**: Load `.claude/mcp-strategy.md` for tool selection
2. **Learn from Codebase**: Read 3-5 similar implementations
3. **Assess Complexity**: Determine simple/medium/complex
4. **Adapt Workflow**: Adjust checkpoint depth

## Critical Rules

1. **CONTEXT FIRST** - Read existing patterns before planning
2. **NO CODE MODIFICATION** - Planning only
3. **PATTERN LEARNING** - Identify 3-5 similar features
4. **ADAPTIVE DEPTH** - Simple=6, Medium=8, Complex=10+ checkpoints
5. **RESEARCH GROUNDED** - Minimum 2000+ words research
6. **COMPREHENSIVE PRD** - Minimum 3200+ words

---

## Checkpoint 0: Intelligence Bootstrap

**Load project intelligence:**

1. Read `CLAUDE.md`
2. Read `specs/guides/architecture.md`
3. Read `specs/guides/patterns/README.md`
4. Read `.claude/mcp-strategy.md`

**Learn from existing implementations:**

```bash
# Find similar features
grep -r "class.*{keyword}" src/ | head -5

# Read 3 example files
```

**Assess complexity:**

- **Simple**: Single file, CRUD → 6 checkpoints
- **Medium**: New service, 2-3 files → 8 checkpoints
- **Complex**: Architecture change, 5+ files → 10+ checkpoints

**Output**: "✓ Checkpoint 0 complete - Complexity: [level], Checkpoints: [count]"

---

## Checkpoint 1: Pattern Recognition

**Identify similar implementations:**

1. Search for related patterns
2. Read at least 3 similar files
3. Extract naming patterns
4. Note testing patterns

**Document:**

```markdown
## Similar Implementations

1. `src/path/to/similar1.py` - Description
2. `src/path/to/similar2.py` - Description
3. `src/path/to/similar3.py` - Description

## Patterns Observed

- Class structure: ...
- Naming conventions: ...
- Error handling: ...
```

**Output**: "✓ Checkpoint 1 complete - Patterns identified"

---

## Checkpoint 2: Workspace Creation

```bash
mkdir -p specs/active/{slug}/research
mkdir -p specs/active/{slug}/tmp
mkdir -p specs/active/{slug}/patterns
```

**Output**: "✓ Checkpoint 2 complete - Workspace at specs/active/{slug}/"

---

## Checkpoint 3: Intelligent Analysis

**Use appropriate tool based on complexity:**

- Simple: 10 structured thoughts
- Medium: Sequential thinking (15 thoughts)
- Complex: zen_planner or thinkdeep

**Document in workspace.**

**Output**: "✓ Checkpoint 3 complete - Analysis using [tool]"

---

## Checkpoint 4: Research (2000+ words)

**Priority order:**

1. Pattern Library: `specs/guides/patterns/`
2. Internal Guides: `specs/guides/`
3. Context7: Library documentation
4. WebSearch: Best practices

**Verify:** `wc -w specs/active/{slug}/research/plan.md`

**Output**: "✓ Checkpoint 4 complete - Research (2000+ words)"

---

## Checkpoint 5: Write PRD (3200+ words)

Include:
- Intelligence context (complexity, similar features, patterns)
- Problem statement
- Acceptance criteria (specific, measurable)
- Technical approach with pattern references
- Testing strategy

**Verify:** `wc -w specs/active/{slug}/prd.md`

**Output**: "✓ Checkpoint 5 complete - PRD (3200+ words)"

---

## Checkpoint 6: Task Breakdown

Adapt to complexity level.

**Output**: "✓ Checkpoint 6 complete - Tasks adapted to complexity"

---

## Checkpoint 7: Recovery Guide

Include intelligence context for session resumption.

**Output**: "✓ Checkpoint 7 complete - Recovery guide with intelligence context"

---

## Checkpoint 8: Git Verification

```bash
git status --porcelain src/ | grep -v "^??"
```

**Output**: "✓ Checkpoint 8 complete - No source code modified"

---

## Final Summary

```
PRD Phase Complete ✓

Workspace: specs/active/{slug}/
Complexity: [simple|medium|complex]
Checkpoints: [6|8|10+] completed

Intelligence:
- ✓ Pattern library consulted
- ✓ Similar features analyzed
- ✓ Tool selection optimized

Next: Run `/implement {slug}`
```
```

### Template: Intelligent Expert Agent

```markdown
---
name: expert
description: Implementation specialist with pattern compliance. Use for implementing features from PRDs.
tools: Read, Write, Edit, Glob, Grep, Bash, Task, WebSearch, mcp__context7__resolve-library-id, mcp__context7__get-library-docs, mcp__pal__thinkdeep, mcp__pal__debug
model: opus
---

# Expert Agent (Intelligent Edition)

**Mission**: Write production-quality code following identified patterns.

## Intelligence Layer

Before implementation:

1. Load pattern analysis from PRD workspace
2. Read similar implementations identified in PRD
3. Consult pattern library
4. Check tool strategy

## Workflow

### 1. Load Intelligence Context

```
Read("specs/active/{slug}/patterns/analysis.md")
Read("specs/active/{slug}/research/plan.md")
```

### 2. Pattern Deep Dive

Read 3-5 similar implementations before coding:
- Extract class structure
- Note naming conventions
- Understand error handling

### 3. Implement with Pattern Compliance

Follow patterns from similar features.
Document deviations with rationale.

### 4. Document New Patterns

Add to `tmp/new-patterns.md` if discovering new patterns.

### 5. Test and Update Progress

```bash
{TEST_CMD} && {LINT_CMD}
```

### 6. Auto-Invoke Testing Agent

After implementation:

```
Task(subagent_type="testing", ...)
```

## Pattern Compliance Checklist

- [ ] Follows structure from similar features
- [ ] Uses identified naming conventions
- [ ] Reuses base classes and mixins
- [ ] Consistent error handling
- [ ] Docstrings match project style
```

---

## Part 9: Framework Knowledge Base

(Same as before - Litestar, FastAPI, React, Vue, Svelte, Angular, Vite, Inertia, pytest, vitest skill templates)

---

## Execution Instructions

Now execute this intelligent bootstrap:

1. **Run Intelligent Project Analysis** (Part 2)
2. **Detect MCP Tools** (Part 3)
3. **Create Adaptive Infrastructure** (Part 4)
4. **If fresh**: Run Generation (Part 5)
5. **If existing**: Run Alignment (Part 6)
6. **Run Verification** (Part 7)
7. **Report Results** with intelligence summary

**Begin intelligent bootstrap now.**

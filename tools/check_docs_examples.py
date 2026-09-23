"""Verification gate for documentation code examples.

Extracts TypeScript, Vue, Svelte, and Python code blocks from reStructuredText
files, validates them against repository types and runtime definitions, and
reports source-mapped diagnostics.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import inspect
import json
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_DIRECTIVE_PATTERN = re.compile(r"^(\s*)\.\.\s+(?:code-block|sourcecode)::\s*(\w+)")
_OPTION_PATTERN = re.compile(r"^\s*:[a-zA-Z0-9_-]+:")
_SKIP_MARKER = ".. docs-example: skip"
_SCRIPT_START_PATTERN = re.compile(r"<script\b([^>]*)>", re.IGNORECASE)
_SCRIPT_END_PATTERN = re.compile(r"</script>", re.IGNORECASE)
_TS_LANGS = frozenset({"typescript", "ts", "tsx"})
_VUE_SVELTE_LANGS = frozenset({"vue", "svelte"})
_PY_LANGS = frozenset({"python", "py"})
_TSC_DIAGNOSTIC_PATTERN = re.compile(r"^(.+?)(?:\((\d+),(\d+)\)|:(\d+):(\d+))(?:\s*-\s*)?:?\s+error\s+(TS\d+):\s*(.+)$")
_RUFF_DIAGNOSTIC_PATTERN = re.compile(r"^(.+?):(\d+):(\d+):\s+(F821\s+.+)$")

_AMBIENT_DECLARATIONS = """declare module "@/generated/*";
declare module "@/generated/routes";
declare module "@/generated/channels";
declare module "@/generated/page-props";
declare module "@/generated/schemas";
declare module "@/layouts/*";
declare module "~/generated/*";
declare module "$lib/*";
declare module "./$types";
declare module "@inertiajs/*";
declare module "@inertiajs/react";
declare module "@inertiajs/vue3";
declare module "@inertiajs/svelte";
declare module "virtual:litestar-static-props";
declare module "react-error-boundary";
declare module "@angular/*";
declare module "@angular/core";
declare module "@angular/router";
declare module "@angular/common/http";
"""


@dataclass(slots=True)
class CodeBlock:
    """Extracted code block metadata and contents.

    Attributes:
        rst_path: Original reST file path.
        first_body_line: 1-based line number of the block body in the reST file.
        lang: Code block language specifier.
        code: Dedented source content of the block.
    """

    rst_path: Path
    first_body_line: int
    lang: str
    code: str


@dataclass(slots=True)
class Diagnostic:
    """Source-mapped failure diagnostic.

    Attributes:
        rst_path: Original reST file path.
        line: 1-based line number in the reST file.
        message: Diagnostic description.
    """

    rst_path: Path
    line: int
    message: str

    def __str__(self) -> str:
        """Format diagnostic with the docs-example prefix."""
        return f"docs-example: {self.rst_path}:{self.line}: {self.message}"


def _is_block_skipped(lines: list[str], directive_index: int) -> bool:
    """Determine whether a skip marker precedes the directive line.

    Args:
        lines: All lines in the reST document.
        directive_index: Index of the .. code-block:: directive line.

    Returns:
        True if the immediately preceding non-empty line is a skip marker.
    """
    check_idx = directive_index - 1
    while check_idx >= 0 and not lines[check_idx].strip():
        check_idx -= 1
    return check_idx >= 0 and lines[check_idx].strip() == _SKIP_MARKER


def _skip_directive_options(lines: list[str], start_cursor: int, directive_indent: int) -> int:
    """Advance past directive options to the start of the body or blank separator.

    Args:
        lines: All lines in the reST document.
        start_cursor: Line index immediately following the directive.
        directive_indent: Column indentation level of the directive.

    Returns:
        Line index after all options and option continuation lines.
    """
    cursor = start_cursor
    line_count = len(lines)
    while cursor < line_count:
        opt_line = lines[cursor]
        if not opt_line.strip():
            cursor += 1
            break
        opt_indent = len(opt_line) - len(opt_line.lstrip())
        if opt_indent > directive_indent and _OPTION_PATTERN.match(opt_line):
            cursor += 1
            while cursor < line_count:
                next_line = lines[cursor]
                if not next_line.strip():
                    cursor += 1
                    break
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent > opt_indent and not _OPTION_PATTERN.match(next_line):
                    cursor += 1
                else:
                    break
        else:
            break
    return cursor


def _collect_body_lines(lines: list[str], start_cursor: int, directive_indent: int) -> tuple[int, list[str], int]:
    """Collect contiguous indented body lines for a code block.

    Args:
        lines: All lines in the reST document.
        start_cursor: Line index after directive options.
        directive_indent: Column indentation level of the directive.

    Returns:
        Tuple of (first_body_line_number, collected_body_lines, next_cursor).
    """
    cursor = start_cursor
    line_count = len(lines)
    while cursor < line_count and not lines[cursor].strip():
        cursor += 1

    if cursor >= line_count:
        return 0, [], cursor

    first_body_line = cursor + 1
    body_lines: list[str] = []
    while cursor < line_count:
        candidate = lines[cursor]
        if not candidate.strip():
            body_lines.append(candidate)
            cursor += 1
            continue
        cand_indent = len(candidate) - len(candidate.lstrip())
        if cand_indent <= directive_indent:
            break
        body_lines.append(candidate)
        cursor += 1

    while body_lines and not body_lines[-1].strip():
        body_lines.pop()

    return first_body_line, body_lines, cursor


def extract_code_blocks(rst_path: Path) -> list[CodeBlock]:
    """Extract validated code blocks from a reStructuredText file.

    Handles language filtering, skip markers, option pruning, dedenting,
    and Vue/Svelte script element isolation.

    Args:
        rst_path: Path to the .rst file to inspect.

    Returns:
        List of extracted CodeBlock objects.
    """
    try:
        content = rst_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []

    lines = content.splitlines()
    blocks: list[CodeBlock] = []
    line_count = len(lines)
    index = 0

    while index < line_count:
        match = _DIRECTIVE_PATTERN.match(lines[index])
        if not match:
            index += 1
            continue

        directive_indent = len(match.group(1))
        lang = match.group(2).lower()

        if lang not in _TS_LANGS and lang not in _VUE_SVELTE_LANGS and lang not in _PY_LANGS:
            index += 1
            continue

        is_skipped = _is_block_skipped(lines, index)
        opt_cursor = _skip_directive_options(lines, index + 1, directive_indent)
        first_line, body_lines, next_index = _collect_body_lines(lines, opt_cursor, directive_indent)

        if not is_skipped and body_lines:
            raw_body = "\n".join(body_lines)
            dedented_body = textwrap.dedent(raw_body)
            if lang in _VUE_SVELTE_LANGS:
                script_block = _extract_script_block(rst_path, first_line, body_lines)
                if script_block is not None:
                    blocks.append(script_block)
            else:
                blocks.append(CodeBlock(rst_path=rst_path, first_body_line=first_line, lang=lang, code=dedented_body))

        index = next_index

    return blocks


def _extract_script_block(rst_path: Path, first_body_line: int, body_lines: list[str]) -> CodeBlock | None:
    """Extract the script element contents from a Vue or Svelte body.

    Args:
        rst_path: Original reST file path.
        first_body_line: 1-based start line of the component body.
        body_lines: Component body lines prior to dedenting.

    Returns:
        CodeBlock targeting TypeScript checking if script tag found, else None.
    """
    start_idx: int | None = None
    end_idx: int | None = None
    is_tsx = False

    for idx, line in enumerate(body_lines):
        if start_idx is None:
            match = _SCRIPT_START_PATTERN.search(line)
            if match:
                start_idx = idx
                attrs = match.group(1).lower()
                if 'lang="tsx"' in attrs or "lang='tsx'" in attrs:
                    is_tsx = True
        elif _SCRIPT_END_PATTERN.search(line):
            end_idx = idx
            break

    if start_idx is None or end_idx is None or end_idx <= start_idx + 1:
        return None

    script_lines = body_lines[start_idx + 1 : end_idx]
    script_raw = "\n".join(script_lines)
    script_dedented = textwrap.dedent(script_raw)
    script_first_line = first_body_line + start_idx + 1
    script_lang = "tsx" if is_tsx else "ts"

    return CodeBlock(rst_path=rst_path, first_body_line=script_first_line, lang=script_lang, code=script_dedented)


def sanitize_filename(rst_path: Path, line: int, ext: str) -> str:
    """Generate a collision-resistant flat filename for a temp snippet.

    Args:
        rst_path: Original reST path.
        line: 1-based line number.
        ext: Target file extension including dot.

    Returns:
        Sanitized filename safe for temporary directory storage.
    """
    clean_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", str(rst_path))
    return f"{clean_stem}__L{line}{ext}"


def _write_typescript_stubs(ts_dir: Path) -> None:
    """Write ambient declaration shims and generated stub modules for tsc.

    Args:
        ts_dir: Directory where temporary TypeScript snippets reside.
    """
    ambient_path = ts_dir / "__ambient.d.ts"
    ambient_path.write_text(_AMBIENT_DECLARATIONS, encoding="utf-8")

    stub_generated = ts_dir / "generated"
    stub_generated.mkdir(exist_ok=True)
    (stub_generated / "routes.d.ts").write_text(
        "export const route: any;\nexport const routes: any;\n", encoding="utf-8"
    )
    (stub_generated / "api.d.ts").write_text(
        "export const client: any;\n"
        "export const getApiSummary: any;\n"
        "export const getApiBooks: any;\n"
        "export const getApiBooksBookId: any;\n"
        "export type Book = any;\n"
        "export type Summary = any;\n",
        encoding="utf-8",
    )
    (stub_generated / "schemas.d.ts").write_text("export const schemas: any;\n", encoding="utf-8")
    (stub_generated / "static-props.d.ts").write_text("export const staticProps: any;\n", encoding="utf-8")

    stub_types = ts_dir / "types"
    stub_types.mkdir(exist_ok=True)
    (stub_types / "shared-props.d.ts").write_text("export type SharedProps = any;\n", encoding="utf-8")


def _write_typescript_config(workdir: Path, ts_dir: Path, repo_root: Path) -> Path:
    """Create tsconfig.json in the workdir with package alias mappings.

    Args:
        workdir: Base temporary directory.
        ts_dir: Snippet directory under workdir.
        repo_root: Litestar-vite repository root path.

    Returns:
        Path to the generated tsconfig.json.
    """
    tsconfig_template_path = repo_root / "tools" / "docs_examples" / "tsconfig.docs.json"
    template_data: dict[str, Any] = {}
    if tsconfig_template_path.exists():
        template_data = json.loads(tsconfig_template_path.read_text(encoding="utf-8"))

    compiler_options = template_data.get("compilerOptions", {})
    compiler_options["target"] = "ES2023"
    compiler_options["module"] = "ESNext"
    compiler_options["moduleResolution"] = "bundler"
    compiler_options["strict"] = True
    compiler_options["noEmit"] = True
    compiler_options["skipLibCheck"] = True
    compiler_options["jsx"] = "react-jsx"
    compiler_options["ignoreDeprecations"] = "6.0"
    compiler_options["baseUrl"] = str(repo_root)

    paths_map = {
        "litestar-vite-plugin/helpers": [str(repo_root / "src" / "js" / "src" / "helpers" / "index.ts")],
        "litestar-vite-plugin/inertia-helpers": [
            str(repo_root / "src" / "js" / "src" / "inertia-helpers" / "index.ts")
        ],
        "litestar-vite-plugin/react": [str(repo_root / "src" / "js" / "src" / "react" / "index.ts")],
        "litestar-vite-plugin/vue": [str(repo_root / "src" / "js" / "src" / "vue" / "index.ts")],
        "litestar-vite-plugin/svelte": [str(repo_root / "src" / "js" / "src" / "svelte" / "index.ts")],
        "litestar-vite-plugin": [str(repo_root / "src" / "js" / "src" / "index.ts")],
    }
    compiler_options["paths"] = paths_map

    workdir_tsconfig = {"compilerOptions": compiler_options, "include": [str(ts_dir / "**" / "*")]}
    tsconfig_path = workdir / "tsconfig.json"
    tsconfig_path.write_text(json.dumps(workdir_tsconfig, indent=2), encoding="utf-8")
    return tsconfig_path


def _parse_tsc_output(output_lines: list[str], block_map: dict[str, tuple[Path, int]]) -> list[Diagnostic]:
    """Parse compiler output lines into source-mapped Diagnostics.

    Args:
        output_lines: Combined stdout and stderr lines from tsc.
        block_map: Mapping from temp file names to originating rst path and line.

    Returns:
        List of Diagnostic records.
    """
    diagnostics: list[Diagnostic] = []
    current_diag: Diagnostic | None = None

    for raw_line in output_lines:
        line_clean = raw_line.rstrip()
        match = _TSC_DIAGNOSTIC_PATTERN.match(line_clean)
        if match:
            if current_diag is not None:
                diagnostics.append(current_diag)
                current_diag = None

            file_part = Path(match.group(1)).name
            line_str = match.group(2) or match.group(4)
            ts_code = match.group(6)
            detail = match.group(7)

            if file_part in block_map:
                rst_path, first_body_line = block_map[file_part]
                line_offset = int(line_str) if line_str else 1
                source_line = first_body_line + line_offset - 1
                current_diag = Diagnostic(rst_path=rst_path, line=source_line, message=f"{ts_code}: {detail}")
        elif current_diag is not None and line_clean.startswith(" "):
            current_diag.message += f" {line_clean.strip()}"

    if current_diag is not None:
        diagnostics.append(current_diag)

    return diagnostics


def check_typescript_blocks(blocks: list[CodeBlock], workdir: Path, repo_root: Path) -> list[Diagnostic]:
    """Type-check extracted TypeScript blocks with tsc --noEmit.

    Args:
        blocks: Extracted TypeScript and script blocks.
        workdir: Base temporary directory.
        repo_root: Litestar-vite repository root path.

    Returns:
        List of mapped Diagnostic failures.
    """
    if not blocks:
        return []

    ts_dir = workdir / "ts"
    ts_dir.mkdir(parents=True, exist_ok=True)

    block_map: dict[str, tuple[Path, int]] = {}
    for block in blocks:
        has_jsx = block.lang == "tsx" or bool(re.search(r"<[A-Za-z][A-Za-z0-9]*[\s/>]", block.code))
        ext = ".tsx" if has_jsx else ".ts"
        fname = sanitize_filename(block.rst_path, block.first_body_line, ext)
        target_path = ts_dir / fname
        target_path.write_text(block.code, encoding="utf-8")
        block_map[target_path.name] = (block.rst_path, block.first_body_line)

    _write_typescript_stubs(ts_dir)
    tsconfig_path = _write_typescript_config(workdir, ts_dir, repo_root)

    cmd = ["npx", "tsc", "--noEmit", "--project", str(tsconfig_path)]
    result = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, check=False)

    if result.returncode == 0:
        return []

    combined_output = (result.stdout + "\n" + result.stderr).splitlines()
    return _parse_tsc_output(combined_output, block_map)


def check_python_undefined_names(blocks: list[CodeBlock], workdir: Path, repo_root: Path) -> list[Diagnostic]:
    """Run ruff check --select F821 to identify undefined names in Python blocks.

    Args:
        blocks: Extracted Python code blocks.
        workdir: Base temporary directory.
        repo_root: Litestar-vite repository root path.

    Returns:
        List of mapped Diagnostic failures.
    """
    if not blocks:
        return []

    py_dir = workdir / "py"
    py_dir.mkdir(parents=True, exist_ok=True)

    block_map: dict[str, tuple[Path, int]] = {}
    for block in blocks:
        fname = sanitize_filename(block.rst_path, block.first_body_line, ".py")
        target_path = py_dir / fname
        target_path.write_text(block.code, encoding="utf-8")
        block_map[target_path.name] = (block.rst_path, block.first_body_line)

    cmd = ["uv", "run", "--no-sync", "ruff", "check", "--select", "F821", "--output-format", "concise", str(py_dir)]
    result = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, check=False)

    diagnostics: list[Diagnostic] = []
    output_lines = (result.stdout + "\n" + result.stderr).splitlines()
    for line in output_lines:
        match = _RUFF_DIAGNOSTIC_PATTERN.match(line.strip())
        if not match:
            continue
        fname = Path(match.group(1)).name
        line_num = int(match.group(2))
        message = match.group(4)

        if fname in block_map:
            rst_path, first_body_line = block_map[fname]
            source_line = first_body_line + line_num - 1
            diagnostics.append(Diagnostic(rst_path=rst_path, line=source_line, message=message))

    return diagnostics


def _resolve_block_imports(
    tree: ast.AST, rst_path: Path, first_body_line: int
) -> tuple[dict[str, Any], dict[str, Any], list[Diagnostic]]:
    """Resolve imported modules and symbols from an AST tree.

    Args:
        tree: Parsed AST tree of a Python block.
        rst_path: Original reST file path.
        first_body_line: 1-based start line of the block.

    Returns:
        Tuple of (imported_modules, imported_symbols, diagnostics).
    """
    diagnostics: list[Diagnostic] = []
    imported_modules: dict[str, Any] = {}
    imported_symbols: dict[str, Any] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                try:
                    mod = importlib.import_module(alias.name)
                    imported_modules[alias.asname or alias.name] = mod
                except (ImportError, ModuleNotFoundError):
                    diagnostics.append(
                        Diagnostic(
                            rst_path=rst_path,
                            line=first_body_line + node.lineno - 1,
                            message=f"Unresolvable module: {alias.name}",
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            try:
                mod = importlib.import_module(module_name)
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    if not hasattr(mod, alias.name):
                        diagnostics.append(
                            Diagnostic(
                                rst_path=rst_path,
                                line=first_body_line + node.lineno - 1,
                                message=f"Symbol '{alias.name}' not found in module '{module_name}'",
                            )
                        )
                    else:
                        obj = getattr(mod, alias.name)
                        imported_symbols[alias.asname or alias.name] = obj
            except (ImportError, ModuleNotFoundError):
                diagnostics.append(
                    Diagnostic(
                        rst_path=rst_path,
                        line=first_body_line + node.lineno - 1,
                        message=f"Unresolvable module: {module_name}",
                    )
                )

    return imported_modules, imported_symbols, diagnostics


def _validate_call_keywords(
    call: ast.Call, target_callable: Any, callable_name: str, rst_path: Path, first_body_line: int
) -> list[Diagnostic]:
    """Validate keyword arguments of a Call against inspect.signature.

    Args:
        call: AST Call node.
        target_callable: Resolved callable object.
        callable_name: Printable identifier for the callable.
        rst_path: Original reST file path.
        first_body_line: 1-based start line of the block.

    Returns:
        List of Diagnostic failures for unrecognized keyword arguments.
    """
    if not callable(target_callable):
        return []

    try:
        sig = inspect.signature(target_callable)
    except (TypeError, ValueError):
        return []

    has_var_keyword = any(param.kind == inspect.Parameter.VAR_KEYWORD for param in sig.parameters.values())
    if has_var_keyword:
        return []

    diagnostics: list[Diagnostic] = []
    valid_param_names = set(sig.parameters.keys())
    for kw in call.keywords:
        if kw.arg is not None and kw.arg not in valid_param_names:
            kw_line = kw.lineno or call.lineno
            diagnostics.append(
                Diagnostic(
                    rst_path=rst_path,
                    line=first_body_line + kw_line - 1,
                    message=f"Callable '{callable_name}' does not accept keyword argument '{kw.arg}'",
                )
            )

    return diagnostics


def _validate_block_calls(
    tree: ast.AST,
    rst_path: Path,
    first_body_line: int,
    imported_modules: dict[str, Any],
    imported_symbols: dict[str, Any],
) -> list[Diagnostic]:
    """Validate all calls in an AST tree against imported symbols and signatures.

    Args:
        tree: Parsed AST tree of a Python block.
        rst_path: Original reST file path.
        first_body_line: 1-based start line of the block.
        imported_modules: Map of imported module names to module objects.
        imported_symbols: Map of imported symbol names to resolved objects.

    Returns:
        List of Diagnostic failures.
    """
    diagnostics: list[Diagnostic] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        target_callable: Any | None = None
        callable_name: str | None = None

        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name in imported_symbols:
                target_callable = imported_symbols[name]
                callable_name = name
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            base_name = node.func.value.id
            attr_name = node.func.attr
            base_obj = imported_symbols.get(base_name) or imported_modules.get(base_name)
            if base_obj is not None:
                if not hasattr(base_obj, attr_name):
                    diagnostics.append(
                        Diagnostic(
                            rst_path=rst_path,
                            line=first_body_line + node.func.lineno - 1,
                            message=f"'{base_name}' has no attribute '{attr_name}'",
                        )
                    )
                else:
                    target_callable = getattr(base_obj, attr_name)
                    callable_name = f"{base_name}.{attr_name}"

        if target_callable is not None and callable_name is not None:
            diagnostics.extend(_validate_call_keywords(node, target_callable, callable_name, rst_path, first_body_line))

    return diagnostics


def check_python_imports_and_signatures(blocks: list[CodeBlock]) -> list[Diagnostic]:
    """Validate imports, attributes, and callable signatures in Python blocks.

    Parses blocks with ast, resolves imported modules and members via importlib,
    and validates Call keyword arguments against inspect.signature.

    Args:
        blocks: Extracted Python code blocks.

    Returns:
        List of mapped Diagnostic failures.
    """
    diagnostics: list[Diagnostic] = []

    for block in blocks:
        try:
            tree = ast.parse(block.code)
        except SyntaxError as err:
            err_line = err.lineno or 1
            diagnostics.append(
                Diagnostic(
                    rst_path=block.rst_path,
                    line=block.first_body_line + err_line - 1,
                    message=f"SyntaxError: {err.msg}",
                )
            )
            continue

        imported_modules, imported_symbols, import_diags = _resolve_block_imports(
            tree, block.rst_path, block.first_body_line
        )
        diagnostics.extend(import_diags)

        call_diags = _validate_block_calls(
            tree, block.rst_path, block.first_body_line, imported_modules, imported_symbols
        )
        diagnostics.extend(call_diags)

    return diagnostics


def collect_rst_files(paths: list[Path]) -> list[Path]:
    """Collect all target .rst files from specified files and directories.

    Args:
        paths: Paths provided via CLI arguments.

    Returns:
        Sorted list of unique resolved .rst paths.
    """
    found: set[Path] = set()
    for path in paths:
        if path.is_file():
            found.add(path)
        elif path.is_dir():
            for rst_path in path.rglob("*.rst"):
                found.add(rst_path)
    return sorted(found)


def main() -> int:
    """CLI entrypoint for documentation code example verification.

    Returns:
        0 on success, 1 on any diagnostic failure.
    """
    parser = argparse.ArgumentParser(description="Verify code examples embedded in reStructuredText documentation.")
    parser.add_argument(
        "--paths", nargs="+", default=["docs"], help="Path(s) to documentation files or directories to verify."
    )
    parser.add_argument(
        "--keep-workdir", action="store_true", help="Retain temporary files for inspection after execution."
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    target_paths = [Path(p) if Path(p).is_absolute() else (repo_root / p).resolve() for p in args.paths]
    rst_files = collect_rst_files(target_paths)

    all_blocks: list[CodeBlock] = []
    for rst_file in rst_files:
        try:
            rel_path = rst_file.relative_to(repo_root)
        except ValueError:
            rel_path = rst_file
        file_blocks = extract_code_blocks(rst_file)
        for b in file_blocks:
            b.rst_path = rel_path
        all_blocks.extend(file_blocks)

    ts_blocks = [b for b in all_blocks if b.lang in _TS_LANGS]
    py_blocks = [b for b in all_blocks if b.lang in _PY_LANGS]

    workdir = Path(tempfile.mkdtemp(prefix="docs_examples_"))

    try:
        diagnostics: list[Diagnostic] = []
        diagnostics.extend(check_typescript_blocks(ts_blocks, workdir, repo_root))
        diagnostics.extend(check_python_undefined_names(py_blocks, workdir, repo_root))
        diagnostics.extend(check_python_imports_and_signatures(py_blocks))

        diagnostics.sort(key=lambda d: (str(d.rst_path), d.line))

        for diag in diagnostics:
            print(str(diag))

        total_files = len(rst_files)
        total_blocks = len(all_blocks)
        fail_count = len(diagnostics)

        summary = f"docs-example check: {total_blocks} blocks across {total_files} files, {fail_count} failures."
        print(summary)

        return 1 if fail_count > 0 else 0
    finally:
        if not args.keep_workdir:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

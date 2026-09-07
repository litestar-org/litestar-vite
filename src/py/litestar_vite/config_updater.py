"""Utilities for updating ViteConfig in Python application files."""

import ast
import inspect
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litestar.cli._utils import LitestarEnv


def find_app_file(env: "LitestarEnv") -> Path | None:
    """Resolve the Python entrypoint file path from LitestarEnv.

    Args:
        env: The Litestar CLI environment.

    Returns:
        The Path to the application file if found and inside the project cwd, else None.
    """
    if not env.app_path:
        return None

    target = env.app_path.split(":", 1)[0].strip()
    if not target:
        return None

    cwd_resolved = env.cwd.resolve()

    # Check sys.modules if already imported, but never edit files outside the project.
    module = sys.modules.get(target)
    if module is not None:
        source_file = inspect.getsourcefile(module) or getattr(module, "__file__", None)
        if source_file:
            mod_path = Path(source_file).resolve()
            if mod_path.is_file() and mod_path.is_relative_to(cwd_resolved):
                return mod_path

    parts = target.split(".")
    candidates = [
        env.cwd / target,
        env.cwd / f"{target}.py",
        env.cwd.joinpath(*parts).with_suffix(".py"),
        env.cwd.joinpath(*parts) / "__init__.py",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    return None


def format_vite_config(
    template_name: str,
    resource_dir: str,
    bundle_dir: str,
    frontend_dir: str = ".",
    enable_types: bool | None = None,
    base_indent: str = "",
) -> str:
    """Build the formatted ViteConfig(...) string.

    Args:
        template_name: The name of the template that was scaffolded.
        resource_dir: The resource directory used.
        bundle_dir: The bundle directory used.
        frontend_dir: The subdirectory where the frontend is located.
        enable_types: Explicit enable_types flag if provided.
        base_indent: Base indentation string.

    Returns:
        Formatted ViteConfig call string.
    """
    spa_templates = {"react-router", "react-tanstack"}
    mode = "spa" if template_name in spa_templates else "template"

    extra_commands_templates: dict[str, str] = {"react-tanstack": 'TypeGenConfig(extra_commands=[["tsr", "generate"]])'}

    indent = base_indent + "    "
    sub_indent = indent + "    "

    root_expr = "Path(__file__).parent"
    if frontend_dir and frontend_dir != ".":
        root_expr = f'Path(__file__).parent / "{frontend_dir}"'

    if enable_types is False:
        types_line = f"{indent}types=False,"
    elif template_name in extra_commands_templates:
        types_line = f"{indent}types={extra_commands_templates[template_name]},"
    else:
        types_line = f"{indent}types=True,"

    lines = [
        "ViteConfig(",
        f'{indent}mode="{mode}",',
        f"{indent}dev_mode=True,",
        types_line,
        f"{indent}paths=PathConfig(",
        f"{sub_indent}root={root_expr},",
        f'{sub_indent}resource_dir="{resource_dir}",',
        f'{sub_indent}bundle_dir="{bundle_dir}",',
        f"{indent}),",
        f"{base_indent})",
    ]
    return "\n".join(lines)


def _find_vite_config_call(tree: ast.AST) -> ast.Call | None:
    """Find the first ast.Call node for ViteConfig in document order."""
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "ViteConfig")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "ViteConfig")
        )
    ]
    if not calls:
        return None
    calls.sort(key=lambda n: (n.lineno, n.col_offset))
    return calls[0]


def _has_path_import(tree: ast.Module) -> bool:
    """Check if ``Path`` is bound directly in the module namespace."""
    for node in tree.body:
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "pathlib"
            and any(alias.name == "Path" and (alias.asname is None or alias.asname == "Path") for alias in node.names)
        ):
            return True
        if isinstance(node, ast.Import) and any(
            alias.name == "pathlib.Path" and alias.asname == "Path" for alias in node.names
        ):
            return True
    return False


def _find_import_insert_line(tree: ast.Module) -> int:
    """Find the line index immediately after the module docstring and any ``__future__`` imports."""
    insert_line = 0
    idx = 0
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        insert_line = tree.body[0].end_lineno or 1
        idx = 1

    while idx < len(tree.body):
        stmt = tree.body[idx]
        if not (isinstance(stmt, ast.ImportFrom) and stmt.module == "__future__"):
            break
        insert_line = stmt.end_lineno or (insert_line + 1)
        idx += 1

    return insert_line


def _ensure_imports(source: str, need_typegen: bool) -> str:
    """Ensure Path, ViteConfig, PathConfig, and TypeGenConfig (if needed) are imported."""
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)

    required_lv_imports = {"ViteConfig", "PathConfig"}
    if need_typegen:
        required_lv_imports.add("TypeGenConfig")

    litestar_vite_import_node: ast.ImportFrom | None = None
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module in {"litestar_vite", "litestar_vite.config"}:
            litestar_vite_import_node = node

    if litestar_vite_import_node is not None:
        existing_names = {alias.name for alias in litestar_vite_import_node.names}
        missing = sorted(required_lv_imports - existing_names)
        if missing:
            existing_aliases = [
                f"{alias.name} as {alias.asname}" if alias.asname else alias.name
                for alias in litestar_vite_import_node.names
            ]
            all_names = sorted(existing_aliases + missing)
            mod = litestar_vite_import_node.module or "litestar_vite"
            new_import_line = f"from {mod} import {', '.join(all_names)}\n"
            start_line = litestar_vite_import_node.lineno - 1
            end_line = litestar_vite_import_node.end_lineno
            lines[start_line:end_line] = [new_import_line]
    else:
        insert_idx = _find_import_insert_line(tree)
        lines.insert(insert_idx, f"from litestar_vite import {', '.join(sorted(required_lv_imports))}\n")
        tree = ast.parse("".join(lines))

    if not _has_path_import(tree):
        insert_idx = _find_import_insert_line(tree)
        lines.insert(insert_idx, "from pathlib import Path\n")

    return "".join(lines)


def update_vite_config_in_file(
    file_path: Path,
    template_name: str,
    resource_dir: str,
    bundle_dir: str,
    frontend_dir: str = ".",
    enable_types: bool | None = None,
) -> bool:
    """Find and update ViteConfig call in the given file.

    Args:
        file_path: Path to target file.
        template_name: Name of template that was scaffolded.
        resource_dir: Resource directory path.
        bundle_dir: Bundle directory path.
        frontend_dir: Subdirectory where frontend is located.
        enable_types: Explicit enable_types flag if provided.

    Returns:
        True if updated successfully, False otherwise.
    """
    if not file_path.is_file():
        return False

    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError):
        return False

    call_node = _find_vite_config_call(tree)
    if call_node is None:
        return False

    source_lines = source.splitlines(keepends=True)
    start_line_idx = call_node.lineno - 1
    start_line = source_lines[start_line_idx]
    base_indent = " " * (len(start_line) - len(start_line.lstrip()))

    replacement_str = format_vite_config(
        template_name=template_name,
        resource_dir=resource_dir,
        bundle_dir=bundle_dir,
        frontend_dir=frontend_dir,
        enable_types=enable_types,
        base_indent=base_indent,
    )

    start_lineno = call_node.lineno
    start_col = call_node.col_offset
    end_lineno = call_node.end_lineno
    end_col = call_node.end_col_offset

    if end_lineno is None or end_col is None:
        return False

    prefix = "".join(source_lines[: start_lineno - 1]) + source_lines[start_lineno - 1][:start_col]
    suffix = source_lines[end_lineno - 1][end_col:] + "".join(source_lines[end_lineno:])
    new_source = prefix + replacement_str + suffix

    need_typegen = enable_types is not False and template_name == "react-tanstack"
    new_source = _ensure_imports(new_source, need_typegen=need_typegen)

    try:
        compile(new_source, str(file_path), "exec")
        file_path.write_text(new_source, encoding="utf-8")
    except (SyntaxError, OSError):
        return False

    return True

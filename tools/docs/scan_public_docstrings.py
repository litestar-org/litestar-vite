"""AST scanner enforcing public docstring, inline PEP 257 field docstring, and Markdown hygiene."""

import ast
import re
import sys
from pathlib import Path

import msgspec

__all__ = ["PACKAGE_ROOT", "DocstringFinding", "main", "scan_package"]

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "src" / "py" / "litestar_vite"
ATTRIBUTES_RE = re.compile(r"(?m)^\s*Attributes:\s*$")
RST_DIRECTIVE_RE = re.compile(
    r"(\.\.\s+(?:code-block|warning|note|deprecated|versionadded)::|:(?:class|func|attr|meth|exc|mod):`[^`]+`|\bExamples?::)"
)


class DocstringFinding(msgspec.Struct, frozen=True, gc=False):
    """A single public docstring or field hygiene violation."""

    path: Path
    lineno: int
    symbol: str
    kind: str
    message: str


def scan_package(root: Path = PACKAGE_ROOT) -> list[DocstringFinding]:
    """Scan all public modules under root for docstring and field hygiene violations.

    Args:
        root: Root directory of the Python package to scan.

    Returns:
        Ordered list of discovered docstring hygiene findings.
    """
    findings: list[DocstringFinding] = []
    exported_names = _collect_package_exports(root)
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts or path.name == "__main__.py":
            continue
        if (
            path.parent.name == "templates"
            and path.name == "__init__.py"
            and not path.read_text(encoding="utf-8").strip()
        ):
            continue
        findings.extend(_scan_file(path, root, exported_names))
    return findings


def main() -> int:
    """CLI entrypoint for public docstring and field hygiene verification.

    Returns:
        Exit code (`0` when clean, `1` when violations exist).
    """
    findings = scan_package(PACKAGE_ROOT)
    for finding in findings:
        sys.stdout.write(f"{finding.path}:{finding.lineno} [{finding.kind}] {finding.symbol} - {finding.message}\n")
    sys.stdout.write(f"Total findings: {len(findings)}\n")
    return 1 if findings else 0


def _collect_package_exports(root: Path) -> set[str]:
    """Collect all symbol names exported via __all__ in package __init__.py files."""
    exported: set[str] = set()
    for init_path in root.rglob("__init__.py"):
        if "__pycache__" in init_path.parts:
            continue
        tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=str(init_path))
        for node in tree.body:
            if (
                isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets)
                and isinstance(node.value, (ast.List, ast.Tuple))
            ):
                for elt in node.value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        exported.add(elt.value)
    return exported


def _decorator_names(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Extract simple decorator names from a class or function definition."""
    names: set[str] = set()
    for dec in node.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, ast.Attribute):
            names.add(target.attr)
    return names


def _base_names(node: ast.ClassDef) -> set[str]:
    """Extract base class names from a class definition."""
    names: set[str] = set()
    for base in node.bases:
        target = base.value if isinstance(base, ast.Subscript) else base
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, ast.Attribute):
            names.add(target.attr)
    return names


def _is_field_bearing_class(node: ast.ClassDef) -> bool:
    """Return True if a class is a @dataclass or TypedDict."""
    decs = _decorator_names(node)
    bases = _base_names(node)
    return "dataclass" in decs or "TypedDict" in bases


def _is_classvar_or_initvar(annotation: ast.expr) -> bool:
    """Return True if a field annotation is ClassVar or InitVar."""
    target = annotation.value if isinstance(annotation, ast.Subscript) else annotation
    if isinstance(target, ast.Name):
        return target.id in {"ClassVar", "InitVar"}
    if isinstance(target, ast.Attribute):
        return target.attr in {"ClassVar", "InitVar"}
    return False


def _check_rst_directives(
    doc: str | None, *, rel_path: Path, lineno: int, symbol: str, findings: list[DocstringFinding]
) -> None:
    """Append a finding if a docstring contains Sphinx rST directives or roles."""
    if not doc:
        return
    match = RST_DIRECTIVE_RE.search(doc)
    if match is not None:
        findings.append(
            DocstringFinding(
                path=rel_path,
                lineno=lineno,
                symbol=symbol,
                kind="rst-directive-in-docstring",
                message=f"Docstring contains Sphinx rST syntax '{match.group(1)}'",
            )
        )


def _scan_class(node: ast.ClassDef, *, rel_path: Path, findings: list[DocstringFinding]) -> None:
    """Scan a public class definition for docstring, field, and method hygiene."""
    doc = ast.get_docstring(node)
    if not doc:
        findings.append(
            DocstringFinding(
                path=rel_path,
                lineno=node.lineno,
                symbol=node.name,
                kind="missing-class-docstring",
                message="Public class is missing a docstring",
            )
        )
    _check_rst_directives(doc, rel_path=rel_path, lineno=node.lineno, symbol=node.name, findings=findings)

    if _is_field_bearing_class(node):
        if doc and ATTRIBUTES_RE.search(doc):
            findings.append(
                DocstringFinding(
                    path=rel_path,
                    lineno=node.lineno,
                    symbol=node.name,
                    kind="hybrid-duplicate-attributes",
                    message="Class docstring contains 'Attributes:' section; use PEP 257 inline field docstrings only",
                )
            )
        stmts = node.body
        for idx, stmt in enumerate(stmts):
            if (
                isinstance(stmt, ast.AnnAssign)
                and isinstance(stmt.target, ast.Name)
                and not stmt.target.id.startswith("_")
                and not _is_classvar_or_initvar(stmt.annotation)
            ):
                field_name = stmt.target.id
                field_symbol = f"{node.name}.{field_name}"
                next_stmt = stmts[idx + 1] if idx + 1 < len(stmts) else None
                if (
                    isinstance(next_stmt, ast.Expr)
                    and isinstance(next_stmt.value, ast.Constant)
                    and isinstance(next_stmt.value.value, str)
                    and next_stmt.value.value.strip()
                ):
                    _check_rst_directives(
                        next_stmt.value.value,
                        rel_path=rel_path,
                        lineno=next_stmt.lineno,
                        symbol=field_symbol,
                        findings=findings,
                    )
                else:
                    findings.append(
                        DocstringFinding(
                            path=rel_path,
                            lineno=stmt.lineno,
                            symbol=field_symbol,
                            kind="missing-field-docstring",
                            message="Public field is missing an inline PEP 257 docstring",
                        )
                    )

    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _scan_function(item, rel_path=rel_path, prefix=f"{node.name}.", findings=findings)


def _scan_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef, *, rel_path: Path, prefix: str, findings: list[DocstringFinding]
) -> None:
    """Scan a function or method definition for docstring and overload hygiene."""
    symbol = f"{prefix}{node.name}"
    decs = _decorator_names(node)
    doc = ast.get_docstring(node)
    if "overload" in decs:
        if doc:
            findings.append(
                DocstringFinding(
                    path=rel_path,
                    lineno=node.lineno,
                    symbol=symbol,
                    kind="overload-has-docstring",
                    message="@overload stub should not have a docstring",
                )
            )
        return
    if node.name.startswith("_"):
        _check_rst_directives(doc, rel_path=rel_path, lineno=node.lineno, symbol=symbol, findings=findings)
        return
    if not doc:
        findings.append(
            DocstringFinding(
                path=rel_path,
                lineno=node.lineno,
                symbol=symbol,
                kind="missing-function-docstring",
                message="Public function or method is missing a docstring",
            )
        )
    _check_rst_directives(doc, rel_path=rel_path, lineno=node.lineno, symbol=symbol, findings=findings)


def _scan_file(path: Path, root: Path, exported_names: set[str]) -> list[DocstringFinding]:
    """Scan a single Python source file for docstring hygiene findings."""
    findings: list[DocstringFinding] = []
    rel_path = path.relative_to(root)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    is_public_module = not path.stem.startswith("_") or path.name == "__init__.py"
    module_doc = ast.get_docstring(tree)
    if is_public_module and not module_doc:
        findings.append(
            DocstringFinding(
                path=rel_path,
                lineno=1,
                symbol="<module>",
                kind="missing-module-docstring",
                message="Public module is missing a module docstring",
            )
        )
    if is_public_module:
        _check_rst_directives(module_doc, rel_path=rel_path, lineno=1, symbol="<module>", findings=findings)

    for node in tree.body:
        if (
            isinstance(node, ast.ClassDef)
            and not node.name.startswith("_")
            and (is_public_module or node.name in exported_names)
        ):
            _scan_class(node, rel_path=rel_path, findings=findings)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
            is_public_module or node.name in exported_names or "overload" in _decorator_names(node)
        ):
            _scan_function(node, rel_path=rel_path, prefix="", findings=findings)
    return findings


if __name__ == "__main__":
    raise SystemExit(main())

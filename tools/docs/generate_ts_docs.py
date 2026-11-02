"""Generate the TypeScript 18-subpath API reference pages from package.json and src/js/src."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import msgspec
from litestar.serialization import decode_json

if TYPE_CHECKING:
    from collections.abc import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]

PAGE_ROUTING: dict[str, str] = {
    ".": "docs/reference/typescript/index.md",
    "./inertia": "docs/reference/typescript/index.md",
    "./virtual": "docs/reference/typescript/index.md",
    "./helpers": "docs/reference/typescript/helpers.md",
    "./inertia-helpers": "docs/reference/typescript/helpers.md",
    "./react": "docs/reference/typescript/frameworks.md",
    "./vue": "docs/reference/typescript/frameworks.md",
    "./svelte": "docs/reference/typescript/frameworks.md",
    "./astro": "docs/reference/typescript/frameworks.md",
    "./sveltekit": "docs/reference/typescript/frameworks.md",
    "./nuxt": "docs/reference/typescript/frameworks.md",
    "./dev-ssr": "docs/reference/typescript/frameworks.md",
    "./ssr-worker": "docs/reference/typescript/frameworks.md",
    "./fragments": "docs/reference/typescript/fragments.md",
    "./fragments/client": "docs/reference/typescript/fragments.md",
    "./fragments/react": "docs/reference/typescript/fragments.md",
    "./fragments/vue": "docs/reference/typescript/fragments.md",
    "./fragments/svelte": "docs/reference/typescript/fragments.md",
}


class PageHeader(msgspec.Struct, frozen=True, gc=False):
    """Frontmatter and introductory summary for a generated TypeScript reference page."""

    rel_path: str
    title: str
    description: str
    intro: str
    subpaths: tuple[str, ...]


PAGE_HEADERS: tuple[PageHeader, ...] = (
    PageHeader(
        rel_path="docs/reference/typescript/index.md",
        title="Vite Plugin & Core Types",
        description="TypeScript API reference for litestar-vite-plugin, litestar-vite-plugin/inertia, and litestar-vite-plugin/virtual.",
        intro=(
            "The `litestar-vite-plugin` npm package ships 18 typed ESM entrypoints covering the Vite 7+ plugin, "
            "runtime helpers, framework bindings, meta-framework integrations, and server/island fragment adapters. "
            "This page documents the root Vite plugin (`litestar-vite-plugin`), base Inertia ambient types "
            "(`litestar-vite-plugin/inertia`), and the `virtual:litestar-static-props` ambient module "
            "(`litestar-vite-plugin/virtual`)."
        ),
        subpaths=(".", "./inertia", "./virtual"),
    ),
    PageHeader(
        rel_path="docs/reference/typescript/helpers.md",
        title="Runtime & Inertia Helpers",
        description="TypeScript API reference for litestar-vite-plugin/helpers and litestar-vite-plugin/inertia-helpers.",
        intro=(
            "Browser and SSR runtime utilities for CSRF token injection, route matching, HTMX JSON templates, "
            "WebSocket/SSE event streams, Litestar Channels, Litestar Queues, Inertia page resolution, "
            "pagination helpers, and Laravel Precognition validation."
        ),
        subpaths=("./helpers", "./inertia-helpers"),
    ),
    PageHeader(
        rel_path="docs/reference/typescript/frameworks.md",
        title="Framework Bindings & Meta-Frameworks",
        description="TypeScript API reference for React, Vue, Svelte, Astro, SvelteKit, Nuxt, dev-ssr, and ssr-worker subpaths.",
        intro=(
            "Framework-idiomatic reactive stream bindings (`litestar-vite-plugin/react`, `/vue`, `/svelte`), "
            "meta-framework Vite/Nitro integrations (`litestar-vite-plugin/astro`, `/sveltekit`, `/nuxt`), "
            "and SSR execution transports (`litestar-vite-plugin/dev-ssr`, `/ssr-worker`)."
        ),
        subpaths=("./react", "./vue", "./svelte", "./astro", "./sveltekit", "./nuxt", "./dev-ssr", "./ssr-worker"),
    ),
    PageHeader(
        rel_path="docs/reference/typescript/fragments.md",
        title="Server Fragments & Islands",
        description="TypeScript API reference for litestar-vite-plugin/fragments and client hydration adapters.",
        intro=(
            "Server-rendered component fragments (`litestar-vite-plugin/fragments`) and `<litestar-island>` "
            "progressive hydration adapters (`litestar-vite-plugin/fragments/client`, `/react`, `/vue`, `/svelte`)."
        ),
        subpaths=("./fragments", "./fragments/client", "./fragments/react", "./fragments/vue", "./fragments/svelte"),
    ),
)


class InterfaceProperty(msgspec.Struct, frozen=True, gc=False):
    """A single property or method declaration inside a TypeScript interface."""

    name: str
    type_str: str
    optional: bool
    default: str | None
    description: str


class SubpathSymbol(msgspec.Struct, frozen=True, gc=False):
    """An exported TypeScript symbol belonging to a public package subpath."""

    name: str
    kind: str
    signature: str
    summary: str
    properties: tuple[InterfaceProperty, ...] = ()
    defined_in: str = ""


class SubpathDoc(msgspec.Struct, frozen=True, gc=False):
    """Resolved documentation model for one package.json exports subpath."""

    subpath: str
    import_specifier: str
    types_entry: str
    source_path: Path
    module_summary: str
    symbols: tuple[SubpathSymbol, ...]


JSDOC_BLOCK_RE = re.compile(r"/\*\*(.*?)\*/", re.DOTALL)
RE_EXPORT_FROM_RE = re.compile(r'export\s+(?:type\s+)?\{([^}]+)\}\s+from\s+"([^"]+)"', re.DOTALL)
LOCAL_IMPORT_RE = re.compile(r'import\s+(?:type\s+)?\{([^}]+)\}\s+from\s+"([^"]+)"', re.DOTALL)
LOCAL_RE_EXPORT_RE = re.compile(r"export\s+(?:type\s+)?\{([^}]+)\}(?!\s+from)", re.DOTALL)


def _clean_jsdoc(raw_comment: str) -> tuple[str, str | None, bool]:
    """Parse a JSDoc comment body into summary text, @default value, and @internal flag."""
    lines: list[str] = []
    default_val: str | None = None
    is_internal = False
    in_example = False

    for raw_line in raw_comment.splitlines():
        stripped = re.sub(r"^\s*\*\s?", "", raw_line).strip()
        if stripped.startswith("@internal"):
            is_internal = True
        if stripped.startswith("@example"):
            in_example = True
            continue
        if stripped.startswith("@default"):
            default_val = stripped.removeprefix("@default").strip()
            continue
        if stripped.startswith("@"):
            in_example = False
            continue
        if in_example:
            continue
        lines.append(stripped)

    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        if not line:
            if current:
                paragraphs.append(" ".join(current))
                current = []
        else:
            current.append(line)
    if current:
        paragraphs.append(" ".join(current))

    summary = paragraphs[0] if paragraphs else ""
    summary = re.sub(r"\{@link\s+([^}]+)\}", r"`\1`", summary)
    return summary, default_val, is_internal


def _find_preceding_jsdoc(source: str, start_idx: int) -> tuple[str, str | None, bool]:
    """Locate a JSDoc comment immediately preceding `start_idx`."""
    prefix = source[:start_idx]
    lines = prefix.splitlines()
    while lines and (not lines[-1].strip() or lines[-1].strip().startswith("//")):
        lines.pop()
    trimmed = "\n".join(lines).rstrip()
    if not trimmed.endswith("*/"):
        return "", None, False
    open_idx = trimmed.rfind("/**")
    if open_idx == -1:
        return "", None, False
    comment_body = trimmed[open_idx + 3 : -2]
    return _clean_jsdoc(comment_body)


def _extract_balanced_block(source: str, open_brace_idx: int) -> tuple[str, int]:
    """Return the text inside `{ ... }` starting at `open_brace_idx` and the closing index."""
    depth = 0
    idx = open_brace_idx
    length = len(source)
    while idx < length:
        ch = source[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[open_brace_idx + 1 : idx], idx + 1
        idx += 1
    return source[open_brace_idx + 1 :], length


def _parse_interface_field_line(
    body: str, idx: int, line_end: int, pending_jsdoc: str, pending_default: str | None
) -> tuple[InterfaceProperty | None, int]:
    """Parse a single top-level interface field line and return `(prop, next_idx)`."""
    line = body[idx:line_end].strip()
    if not line or line.startswith("//"):
        return None, line_end + 1
    field_match = re.match(r"^(?:readonly\s+)?([A-Za-z_][A-Za-z0-9_]*)(\?)?\s*:\s*(.+)$", line)
    if not field_match:
        return None, line_end + 1
    name = field_match.group(1)
    optional = field_match.group(2) == "?"
    type_part = field_match.group(3).rstrip(";,").strip()
    if type_part.endswith("{"):
        block_idx = body.find("{", idx)
        _, after_block = _extract_balanced_block(body, block_idx)
        return (
            InterfaceProperty(
                name=name, type_str="object", optional=optional, default=pending_default, description=pending_jsdoc
            ),
            after_block,
        )
    return (
        InterfaceProperty(
            name=name, type_str=type_part, optional=optional, default=pending_default, description=pending_jsdoc
        ),
        line_end + 1,
    )


def _parse_interface_properties(body: str) -> tuple[InterfaceProperty, ...]:
    """Extract top-level fields from an interface body."""
    props: list[InterfaceProperty] = []
    depth = 0
    pending_jsdoc = ""
    pending_default: str | None = None
    idx = 0
    length = len(body)

    while idx < length:
        if depth == 0 and body.startswith("/**", idx):
            end_comment = body.find("*/", idx + 3)
            if end_comment == -1:
                break
            pending_jsdoc, pending_default, _ = _clean_jsdoc(body[idx + 3 : end_comment])
            idx = end_comment + 2
            continue

        ch = body[idx]
        if ch in "{([":
            depth += 1
            idx += 1
            continue
        if ch in "})]":
            depth = max(0, depth - 1)
            idx += 1
            continue

        if depth == 0:
            line_end = body.find("\n", idx)
            if line_end == -1:
                line_end = length
            prop, idx = _parse_interface_field_line(body, idx, line_end, pending_jsdoc, pending_default)
            if prop is not None:
                props.append(prop)
                pending_jsdoc = ""
                pending_default = None
            continue

        idx += 1

    return tuple(props)


def _resolve_relative_ts_path(base_file: Path, specifier: str) -> Path:
    """Resolve a relative TypeScript import specifier (`.js` -> `.ts`)."""
    cleaned = specifier
    if cleaned.endswith(".js"):
        cleaned = f"{cleaned[:-3]}.ts"
    candidate = (base_file.parent / cleaned).resolve()
    if candidate.exists():
        return candidate
    dts_candidate = candidate.with_suffix(".d.ts")
    if dts_candidate.exists():
        return dts_candidate
    return candidate


def _extract_module_summary(source: str) -> str:
    """Extract the module-level JSDoc summary if present at the top of the file."""
    stripped = source.lstrip()
    if not stripped.startswith("/**"):
        return ""
    end_idx = stripped.find("*/")
    if end_idx == -1:
        return ""
    after = stripped[end_idx + 2 :].lstrip()
    if after.startswith(("export interface", "export type", "export function", "export const", "export class")):
        comment_body = stripped[3:end_idx]
        if "@module" not in comment_body:
            return ""
    summary, _, _ = _clean_jsdoc(stripped[3:end_idx])
    return summary


def _extract_interfaces_and_types(source: str, rel_file: str, symbols: dict[str, SubpathSymbol]) -> None:
    """Populate `symbols` with top-level `interface` and `type` declarations."""
    interface_pattern = re.compile(
        r"^(?:export\s+)?interface\s+([A-Za-z_][A-Za-z0-9_]*)(?:<[^\n{]+>)?(?:\s+extends\s+[^{]+)?\s*\{", re.MULTILINE
    )
    for match in interface_pattern.finditer(source):
        name = match.group(1)
        summary, _, is_internal = _find_preceding_jsdoc(source, match.start())
        if is_internal or name.startswith("__"):
            continue
        body, _ = _extract_balanced_block(source, match.end() - 1)
        header = match.group(0)[:-1].strip()
        if not header.startswith("export "):
            header = f"export {header}"
        symbols[name] = SubpathSymbol(
            name=name,
            kind="interface",
            signature=header,
            summary=summary,
            properties=_parse_interface_properties(body),
            defined_in=rel_file,
        )

    type_pattern = re.compile(r"^(?:export\s+)?type\s+([A-Za-z_][A-Za-z0-9_]*)(?:<[^=\n]+>)?\s*=\s*(.+)$", re.MULTILINE)
    for match in type_pattern.finditer(source):
        name = match.group(1)
        summary, _, is_internal = _find_preceding_jsdoc(source, match.start())
        if is_internal or name.startswith("__"):
            continue
        raw_decl = match.group(0).strip()
        if not raw_decl.startswith("export "):
            raw_decl = f"export {raw_decl}"
        cont_lines = [raw_decl]
        for next_line in source[match.end() :].splitlines():
            stripped_next = next_line.strip()
            if stripped_next.startswith(("|", "&")):
                cont_lines.append(stripped_next)
            else:
                break
        symbols[name] = SubpathSymbol(
            name=name, kind="type", signature=" ".join(cont_lines), summary=summary, defined_in=rel_file
        )


def _extract_direct_symbols(file_path: Path, repo_root: Path) -> dict[str, SubpathSymbol]:
    """Parse all top-level declarations in a TypeScript file into a symbol map."""
    source = file_path.read_text(encoding="utf-8")
    rel_file = file_path.relative_to(repo_root).as_posix()
    symbols: dict[str, SubpathSymbol] = {}
    _extract_interfaces_and_types(source, rel_file, symbols)

    func_pattern = re.compile(r"^export\s+(default\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
    for match in func_pattern.finditer(source):
        is_default = bool(match.group(1))
        name = match.group(2)
        summary, _, is_internal = _find_preceding_jsdoc(source, match.start())
        if is_internal or name.startswith("__"):
            continue
        decl_end = source.find("\n", match.start())
        brace_pos = source.find("{", match.end())
        semi_pos = source.find("\nexport ", match.end())
        end_pos = (
            brace_pos
            if brace_pos != -1 and (semi_pos == -1 or brace_pos < semi_pos)
            else (decl_end if decl_end != -1 else len(source))
        )
        raw_sig = source[match.start() : end_pos].strip().rstrip("{;").strip()
        sig = " ".join(line.strip() for line in raw_sig.splitlines())
        existing = symbols.get(name)
        summary_to_use = existing.summary if existing and existing.summary and not summary else summary
        symbols[name] = SubpathSymbol(
            name=name,
            kind="default function" if is_default else "function",
            signature=sig,
            summary=summary_to_use,
            defined_in=rel_file,
        )

    const_pattern = re.compile(
        r"^export\s+const\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*([^=\n]+))?\s*=\s*([^\n]+)", re.MULTILINE
    )
    for match in const_pattern.finditer(source):
        name = match.group(1)
        summary, _, is_internal = _find_preceding_jsdoc(source, match.start())
        if is_internal or name.startswith("__"):
            continue
        type_annot = (match.group(2) or "").strip()
        rhs = match.group(3).strip()
        sig = f"export const {name}: {type_annot}" if type_annot else f"export const {name} = {rhs}"
        symbols[name] = SubpathSymbol(name=name, kind="const", signature=sig, summary=summary, defined_in=rel_file)

    class_pattern = re.compile(
        r"^export\s+class\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+extends\s+[A-Za-z0-9_]+)?", re.MULTILINE
    )
    for match in class_pattern.finditer(source):
        name = match.group(1)
        summary, _, is_internal = _find_preceding_jsdoc(source, match.start())
        if is_internal or name.startswith("__"):
            continue
        symbols[name] = SubpathSymbol(
            name=name, kind="class", signature=match.group(0).strip(), summary=summary, defined_in=rel_file
        )

    declare_mod_pattern = re.compile(r'^declare\s+module\s+"([^"]+)"', re.MULTILINE)
    for match in declare_mod_pattern.finditer(source):
        mod_name = match.group(1)
        symbols[mod_name] = SubpathSymbol(
            name=mod_name,
            kind="module",
            signature=f'declare module "{mod_name}"',
            summary="Vite virtual module exposing static props configured in Python `ViteConfig.static_props`.",
            defined_in=rel_file,
        )

    return symbols


def _parse_specifier_list(raw_list: str) -> list[tuple[str, str]]:
    """Parse `{ a, type b as c }` into `(original_name, exported_name)` pairs."""
    pairs: list[tuple[str, str]] = []
    for raw_item in raw_list.split(","):
        cleaned = raw_item.strip()
        if not cleaned:
            continue
        cleaned = re.sub(r"^type\s+", "", cleaned).strip()
        if " as " in cleaned:
            orig, alias = [part.strip() for part in cleaned.split(" as ", 1)]
            pairs.append((orig, alias))
        else:
            pairs.append((cleaned, cleaned))
    return pairs


def _hydrate_shared_alias_properties(collected: dict[str, SubpathSymbol], repo_root: Path) -> None:
    """Attach interface properties to `TypesConfigShape` and `LitestarIntegrationConfig` aliases."""
    shared_targets = {
        "TypesConfigShape": repo_root / "src" / "js" / "src" / "shared" / "typegen-plugin.ts",
        "LitestarIntegrationConfig": repo_root / "src" / "js" / "src" / "shared" / "integration-config.ts",
    }
    for name, sym in list(collected.items()):
        if sym.kind != "type" or sym.properties:
            continue
        for shared_key, shared_path in shared_targets.items():
            if shared_key in sym.signature:
                shared_syms = _extract_direct_symbols(shared_path, repo_root)
                if shared_key in shared_syms:
                    collected[name] = SubpathSymbol(
                        name=sym.name,
                        kind=sym.kind,
                        signature=sym.signature,
                        summary=sym.summary or shared_syms[shared_key].summary,
                        properties=shared_syms[shared_key].properties,
                        defined_in=sym.defined_in,
                    )


def _collect_exports_for_file(file_path: Path, repo_root: Path) -> tuple[str, tuple[SubpathSymbol, ...]]:
    """Collect all exported symbols for a subpath entrypoint, following barrel re-exports."""
    source = file_path.read_text(encoding="utf-8")
    module_summary = _extract_module_summary(source)
    direct = _extract_direct_symbols(file_path, repo_root)
    collected: dict[str, SubpathSymbol] = {
        name: sym for name, sym in direct.items() if sym.signature.startswith("export ") or sym.kind == "module"
    }

    imported_sources: dict[str, Path] = {}
    for imp_match in LOCAL_IMPORT_RE.finditer(source):
        specifier = imp_match.group(2)
        if not specifier.startswith("."):
            continue
        target_path = _resolve_relative_ts_path(file_path, specifier)
        for orig_name, local_name in _parse_specifier_list(imp_match.group(1)):
            imported_sources[local_name] = target_path
            imported_sources[orig_name] = target_path

    for local_re in LOCAL_RE_EXPORT_RE.finditer(source):
        for orig_name, exported_name in _parse_specifier_list(local_re.group(1)):
            resolved_target = imported_sources.get(orig_name)
            if exported_name not in collected and resolved_target and resolved_target.exists():
                target_symbols = _extract_direct_symbols(resolved_target, repo_root)
                if orig_name in target_symbols:
                    sym = target_symbols[orig_name]
                    collected[exported_name] = SubpathSymbol(
                        name=exported_name,
                        kind=sym.kind,
                        signature=sym.signature,
                        summary=sym.summary,
                        properties=sym.properties,
                        defined_in=sym.defined_in,
                    )

    for re_match in RE_EXPORT_FROM_RE.finditer(source):
        specifier = re_match.group(2)
        reexport_target = _resolve_relative_ts_path(file_path, specifier) if specifier.startswith(".") else None
        if not reexport_target or not reexport_target.exists():
            continue
        target_symbols = _extract_direct_symbols(reexport_target, repo_root)
        for orig_name, exported_name in _parse_specifier_list(re_match.group(1)):
            if orig_name in target_symbols:
                sym = target_symbols[orig_name]
                collected[exported_name] = SubpathSymbol(
                    name=exported_name,
                    kind=sym.kind,
                    signature=sym.signature.replace(f" {orig_name}", f" {exported_name}", 1)
                    if orig_name != exported_name
                    else sym.signature,
                    summary=sym.summary,
                    properties=sym.properties,
                    defined_in=sym.defined_in,
                )

    _hydrate_shared_alias_properties(collected, repo_root)
    return module_summary, tuple(collected.values())


def resolve_subpath_source(repo_root: Path, types_or_import_path: str) -> Path:
    """Translate `./dist/js/<rel>.d.ts` from package.json exports into `src/js/src/<rel>.ts`."""
    rel = types_or_import_path.removeprefix("./dist/js/")
    if rel.endswith(".d.ts"):
        stem = rel[: -len(".d.ts")]
    elif rel.endswith(".js"):
        stem = rel[: -len(".js")]
    else:
        stem = rel

    ts_candidate = repo_root / "src" / "js" / "src" / f"{stem}.ts"
    if ts_candidate.exists():
        return ts_candidate
    return repo_root / "src" / "js" / "src" / f"{stem}.d.ts"


def collect_subpath_docs(repo_root: Path = REPO_ROOT) -> list[SubpathDoc]:
    """Resolve and extract documentation for all 18 package.json exports subpaths."""
    pkg = decode_json((repo_root / "package.json").read_text(encoding="utf-8"))
    exports_map: dict[str, dict[str, str]] = pkg["exports"]
    subpaths: list[SubpathDoc] = []

    for subpath, entry in exports_map.items():
        types_entry = entry.get("types") or entry.get("import", "")
        source_path = resolve_subpath_source(repo_root, types_entry)
        import_spec = "litestar-vite-plugin" if subpath == "." else f"litestar-vite-plugin/{subpath.removeprefix('./')}"
        module_summary, symbols = _collect_exports_for_file(source_path, repo_root)
        subpaths.append(
            SubpathDoc(
                subpath=subpath,
                import_specifier=import_spec,
                types_entry=types_entry,
                source_path=source_path,
                module_summary=module_summary,
                symbols=symbols,
            )
        )

    return subpaths


def _escape_cell(value: str) -> str:
    """Escape Markdown table cell pipes and newlines."""
    return " ".join(value.replace("|", r"\|").splitlines()).strip()


def _render_subpath_section(doc: SubpathDoc, repo_root: Path) -> list[str]:
    """Render a single subpath section with import banner, symbol table, and interface details."""
    rel_src = doc.source_path.relative_to(repo_root).as_posix()
    lines: list[str] = [
        f"## `{doc.import_specifier}`",
        "",
        f"**Package Subpath**: `{doc.subpath}` · **Types**: `{doc.types_entry}` · **Source**: `{rel_src}`",
        "",
    ]
    if doc.module_summary:
        lines.extend([doc.module_summary, ""])

    lines.extend(["| Export | Kind | Description |", "| :--- | :--- | :--- |"])
    for sym in doc.symbols:
        desc = _escape_cell(sym.summary or f"Exported `{sym.kind}` from `{sym.defined_in or rel_src}`.")
        lines.append(f"| `{sym.name}` | `{sym.kind}` | {desc} |")
    lines.append("")

    for sym in doc.symbols:
        lines.extend([f"#### `{sym.name}`", "", "```ts", sym.signature, "```", ""])
        if sym.summary:
            lines.extend([sym.summary, ""])
        if sym.properties:
            lines.extend(["| Property | Type | Default | Description |", "| :--- | :--- | :--- | :--- |"])
            for prop in sym.properties:
                prop_label = f"`{prop.name}?`" if prop.optional else f"`{prop.name}`"
                type_cell = f"`{_escape_cell(prop.type_str)}`"
                default_cell = f"`{_escape_cell(prop.default)}`" if prop.default else "—"
                desc_cell = _escape_cell(prop.description) if prop.description else "—"
                lines.append(f"| {prop_label} | {type_cell} | {default_cell} | {desc_cell} |")
            lines.append("")

    return lines


def render_ts_reference_pages(subpaths: Sequence[SubpathDoc], repo_root: Path = REPO_ROOT) -> dict[str, str]:
    """Render the 4 Markdown reference pages covering all 18 TypeScript subpaths."""
    by_subpath = {item.subpath: item for item in subpaths}
    pages: dict[str, str] = {}

    for header in PAGE_HEADERS:
        lines: list[str] = [
            "---",
            f"title: {header.title}",
            f"description: {header.description}",
            "---",
            "",
            f"# {header.title}",
            "",
            header.intro,
            "",
            "| Subpath | Import Specifier | Source Entrypoint | Exports |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for key in header.subpaths:
            doc = by_subpath[key]
            rel_src = doc.source_path.relative_to(repo_root).as_posix()
            export_names = ", ".join(f"`{sym.name}`" for sym in doc.symbols[:6])
            if len(doc.symbols) > 6:
                export_names = f"{export_names}, +{len(doc.symbols) - 6} more"
            lines.append(f"| `{doc.subpath}` | `{doc.import_specifier}` | `{rel_src}` | {export_names} |")
        lines.append("")

        for key in header.subpaths:
            lines.extend(_render_subpath_section(by_subpath[key], repo_root))

        pages[header.rel_path] = "\n".join(lines).rstrip() + "\n"

    return pages


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for generating or checking the TypeScript reference pages."""
    parser = argparse.ArgumentParser(
        description="Generate docs/reference/typescript/*.md from package.json and src/js/src."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that all generated TypeScript reference files are up-to-date without writing.",
    )
    args = parser.parse_args(argv)

    subpaths = collect_subpath_docs(REPO_ROOT)
    pages = render_ts_reference_pages(subpaths, REPO_ROOT)

    if args.check:
        stale: list[str] = []
        for rel_path, expected in pages.items():
            target = REPO_ROOT / rel_path
            if not target.exists() or target.read_text(encoding="utf-8") != expected:
                stale.append(rel_path)
        if stale:
            sys.stderr.write(
                f"Stale TypeScript reference files ({len(stale)}): {', '.join(stale)}. Run `uv run python tools/docs/generate_ts_docs.py`.\n"
            )
            return 1
        return 0

    for rel_path, content in pages.items():
        target = REPO_ROOT / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Verification gate for documentation code examples.

Extracts TypeScript, Vue, Svelte, and Python code blocks from Markdown and
reStructuredText files, validates them against repository types and runtime
definitions, and reports source-mapped diagnostics.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import importlib
import inspect
import json
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

import msgspec

_DIRECTIVE_PATTERN = re.compile(r"^(\s*)\.\.\s+(?:code-block|sourcecode)::\s*(\w+)")
_OPTION_PATTERN = re.compile(r"^\s*:[a-zA-Z0-9_-]+:")
_MD_FENCE_OPEN_PATTERN = re.compile(r"^(\s*)(`{3,}|~{3,})\s*([a-zA-Z0-9_-]+)(?:\s+.*)?$")
_SNIPPET_INCLUDE_PATTERN = re.compile(r'^\s*--8<--\s+["\']([^"\']+)["\']\s*$')
_SKIP_MARKERS = frozenset({".. docs-example: skip", "<!-- docs-example: skip -->"})
_SCRIPT_START_PATTERN = re.compile(r"<script\b([^>]*)>", re.IGNORECASE)
_SCRIPT_END_PATTERN = re.compile(r"</script>", re.IGNORECASE)
_TS_LANGS = frozenset({"typescript", "ts", "tsx"})
_VUE_SVELTE_LANGS = frozenset({"vue", "svelte"})
_PY_LANGS = frozenset({"python", "py"})
_TSC_DIAGNOSTIC_PATTERN = re.compile(r"^(.+?)(?:\((\d+),(\d+)\)|:(\d+):(\d+))(?:\s*-\s*)?:?\s+error\s+(TS\d+):\s*(.+)$")
_RUFF_DIAGNOSTIC_PATTERN = re.compile(r"^(.+?):(\d+):(\d+):\s+(F821\s+.+)$")
_OPTIONAL_EXTERNAL_MODULES = frozenset({"redis", "redis.asyncio", "asyncpg", "psycopg", "psycopg2"})


class _StubSymbol:
    """Fallback stub symbol for imports from optional external modules."""

    __slots__ = ()

    def __getattr__(self, name: str) -> Any:
        return _StubSymbol()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return _StubSymbol()


class _StubModule:
    """Fallback stub module for optional external packages not installed."""

    __slots__ = ()

    def __getattr__(self, name: str) -> Any:
        return _StubSymbol()


_AMBIENT_DECLARATIONS = """interface ImportMeta {
    glob: (pattern: string, options?: Record<string, any>) => Record<string, any>;
    env: Record<string, any>;
}
declare module "@/generated/*";
declare module "@/generated/routes" {
    export const route: any;
    export const toRoute: any;
    export const wsRoute: any;
    export const currentRoute: any;
    export const isCurrentRoute: any;
    export const isRoute: any;
    export const hasRoute: any;
    export const routeDefinitions: Record<string, any>;
    export type RouteName = string;
    export type RouteParams<T extends string = string> = Record<string, any>;
    export type RouteQueryParams<T extends string = string> = Record<string, any>;
}
declare module "@/generated/api" {
    export const client: any;
    export const listItems: any;
    export const createItem: any;
    export const listCustomers: any;
    export const getApiSummary: any;
    export const getApiBooks: any;
    export const getApiBooksBookId: any;
    export type Book = any;
    export type Summary = any;
    export type Item = any;
    export type ItemCreate = any;
}
declare module "@/generated/schemas" {
    export const schemas: any;
    export type OperationName = string;
    export type FormInput<T = any> = any;
    export type FormResponse<T = any, S = any> = any;
    export type SuccessResponse<T = any> = any;
    export type ErrorResponse<T = any> = any;
    export type PathParams<T = any> = any;
    export type QueryParams<T = any> = any;
}
declare module "@/generated/channels" {
    export type ChannelKey = string;
    export type ChannelAddress<K extends string = string> = string;
    export type ChannelProtocol<K extends string = string> = "ws" | "channels" | "sse";
    export type ChannelParams<K extends string = string> = Record<string, any>;
    export type ChannelSendPayload<K extends string = string> = any;
    export type ChannelReceivePayload<K extends string = string> = any;
    export interface RealtimeChannels {
        [key: string]: {
            address: string;
            protocol: string;
            params: Record<string, any>;
            sendPayload: any;
            receivePayload: any;
        };
    }
    export const CHANNEL_METADATA: Record<string, any>;
}
declare module "@/generated/page-props" {
    export type PagePropsMap = Record<string, any>;
    export type PageComponentName = string;
    export type PagePropsFor<K extends string = string> = any;
    export type SharedProps = Record<string, any>;
    export type OrdersPageProps = {
        orders: Array<{ id: number; customer: string; total_cents: number }>;
        selected_order?: { id: number; customer: string; total_cents: number } | null;
        audit_log?: string[];
        permissions?: string[];
    };
}
declare module "./generated/*" {
    export const route: any;
    export const toRoute: any;
    export const wsRoute: any;
    export const currentRoute: any;
    export const isCurrentRoute: any;
    export const isRoute: any;
    export const hasRoute: any;
    export const routeDefinitions: Record<string, any>;
    export const listItems: any;
    export const createItem: any;
    export const listCustomers: any;
    export const CHANNEL_METADATA: Record<string, any>;
    export type RealtimeChannels = Record<string, any>;
}
declare module "./generated/routes" {
    export const route: any;
    export const toRoute: any;
    export const wsRoute: any;
    export const currentRoute: any;
    export const isCurrentRoute: any;
    export const isRoute: any;
    export const hasRoute: any;
    export const routeDefinitions: Record<string, any>;
    export type RouteName = string;
    export type WsRouteName = string;
    export type RouteParams<T extends string = string> = Record<string, any>;
}
declare module "./generated/api" {
    export const client: any;
    export const listItems: any;
    export const createItem: any;
    export const listCustomers: any;
}
declare module "./generated/schemas" {
    export type FormInput<T = any> = any;
    export type SuccessResponse<T = any> = any;
}
declare module "./generated/channels" {
    export const CHANNEL_METADATA: Record<string, any>;
    export type RealtimeChannels = {
        ws__notifications: {
            address: string;
            protocol: "ws" | "channels";
            params: Record<string, never>;
            sendPayload: any;
            receivePayload: any;
        };
    };
}
declare module "./generated/api/sdk.gen" {
    export const listItems: any;
    export const createItem: any;
}
declare module "../generated/*" {
    export const route: any;
    export const toRoute: any;
    export const currentRoute: any;
    export const isCurrentRoute: any;
    export const isRoute: any;
    export const hasRoute: any;
    export const listItems: any;
    export const createItem: any;
    export const listCustomers: any;
    export type Book = any;
    export type Summary = any;
    export type FormInput<T = any> = any;
    export type SuccessResponse<T = any> = any;
    export type OrdersPageProps = {
        orders: Array<{ id: number; customer: string; total_cents: number }>;
        selected_order?: { id: number; customer: string; total_cents: number } | null;
        audit_log?: string[];
        permissions?: string[];
    };
}
declare module "../generated/api" {
    export const client: any;
    export const listItems: any;
    export const createItem: any;
    export const listCustomers: any;
    export type Book = any;
    export type Summary = any;
}
declare module "../generated/routes" {
    export const route: any;
    export const toRoute: any;
    export const wsRoute: any;
    export const currentRoute: any;
    export const isCurrentRoute: any;
    export const isRoute: any;
    export const hasRoute: any;
    export const routeDefinitions: Record<string, any>;
}
declare module "../generated/schemas" {
    export type FormInput<T = any> = any;
    export type SuccessResponse<T = any> = any;
}
declare module "../generated/page-props" {
    export type OrdersPageProps = {
        orders: Array<{ id: number; customer: string; total_cents: number }>;
        selected_order?: { id: number; customer: string; total_cents: number } | null;
        audit_log?: string[];
        permissions?: string[];
    };
}
declare module "./api/types.gen" {
    export interface InvoiceSummary {
        id: number;
        total: number;
    }
}
declare module "./islands/*" {
    const Component: any;
    export default Component;
}
declare module "./islands/RevenueChart" {
    const Component: any;
    export default Component;
}
declare module "./islands/RevenueChart.vue" {
    const Component: any;
    export default Component;
}
declare module "./islands/RevenueChart.svelte" {
    const Component: any;
    export default Component;
}
declare module "@vitejs/plugin-react" {
    export default function react(options?: Record<string, any>): any;
}
declare module "@vitejs/plugin-vue" {
    export default function vue(options?: Record<string, any>): any;
}
declare module "@sveltejs/vite-plugin-svelte" {
    export function svelte(options?: Record<string, any>): any;
}
declare module "*.vue" {
    const Component: any;
    export default Component;
}
declare module "*.svelte" {
    const Component: any;
    export default Component;
}
declare module "@/layouts/*";
declare module "~/generated/*" {
    export const route: any;
    export type Summary = any;
}
declare module "~/generated/routes" {
    export const route: any;
}
declare module "~/generated/api" {
    export type Summary = any;
}
declare module "$lib/*";
declare module "./$types";
declare module "astro/config" {
    export function defineConfig(config: Record<string, any>): any;
}
declare function defineNuxtConfig(config: Record<string, any>): any;
declare module "@sveltejs/kit/vite" {
    export function sveltekit(): any;
}
declare module "@inertiajs/*";
declare module "@inertiajs/react" {
    export const Head: any;
    export const Link: any;
    export const router: any;
    export const Deferred: any;
    export const WhenVisible: any;
    export function usePage<T = any>(): { props: T; url: string; component: string; version: string | null };
    export function useForm<T = any>(initialValues?: T): any;
    export function createInertiaApp(options: Record<string, any>): Promise<any>;
}
declare module "@inertiajs/vue3" {
    export const Head: any;
    export const Link: any;
    export const router: any;
    export const Deferred: any;
    export const WhenVisible: any;
    export function usePage<T = any>(): { props: T; url: string; component: string; version: string | null };
    export function useForm<T = any>(initialValues?: T): any;
    export function createInertiaApp(options: Record<string, any>): Promise<any>;
}
declare module "@inertiajs/svelte" {
    export const page: any;
    export const router: any;
    export function useForm<T = any>(initialValues?: T): any;
    export function createInertiaApp(options: Record<string, any>): Promise<any>;
}
declare module "virtual:litestar-static-props" {
    const props: Record<string, any>;
    export default props;
    export const appName: string;
    export const environment: string;
    export const version: string;
    export const features: Record<string, boolean>;
    export const maxUploadMb: number;
    export const supportEmail: string;
}
declare module "react-error-boundary";
declare module "@angular/core" {
    export interface OnInit {
        ngOnInit(): void;
    }
    export function Component(options: Record<string, any>): any;
    export function inject<T>(token: abstract new (...args: any[]) => T): T;
    export function inject<T = any>(token: any): T;
}
declare module "@angular/router" {
    export type Routes = any[];
    export function provideRouter(routes: any[]): any;
}
declare module "@angular/common/http" {
    export class HttpClient {
        get<T = any>(url: string): { subscribe(cb: (data: T) => void): void };
    }
    export function provideHttpClient(...features: any[]): any;
}
declare type SharedPageProps = Record<string, any>;
declare const MetricsChart: any;
declare const AuditLogTable: any;
declare type ChatMessage = any;
declare type ChatResponse = any;
declare type RoomEvent = any;
declare type NotificationMessage = any;
declare type NotificationPayload = any;
declare const currentTicket: any;
declare const handleEvent: any;
declare const showNotification: any;
declare const selectedTaskId: any;
declare const updateTask: any;
declare const warnAboutMissingEvents: any;
declare const taskId: any;
declare const handleTaskEvent: any;
declare const projectId: any;
declare const createEventStream: any;
declare type RouteName = string;
declare type RoutePathParams = Record<string, any>;
declare type RouteQueryParams = Record<string, any>;
declare type RoutesWithoutRequiredParams = RouteName;
declare type RoutesWithRequiredParams = RouteName;
declare const getApiBooksBookId: any;
"""


class CodeBlock(msgspec.Struct, frozen=True, gc=False):
    """Extracted code block metadata and contents."""

    rst_path: Path
    first_body_line: int
    lang: str
    code: str


class Diagnostic(msgspec.Struct, frozen=True, gc=False):
    """Source-mapped failure diagnostic."""

    rst_path: Path
    line: int
    message: str

    def __str__(self) -> str:
        """Format diagnostic with the docs-example prefix."""
        return f"docs-example: {self.rst_path}:{self.line}: {self.message}"


def _is_block_skipped(lines: list[str], directive_index: int) -> bool:
    """Determine whether a skip marker precedes the directive or fence line."""
    check_idx = directive_index - 1
    while check_idx >= 0 and not lines[check_idx].strip():
        check_idx -= 1
    return check_idx >= 0 and lines[check_idx].strip() in _SKIP_MARKERS


def _skip_directive_options(lines: list[str], start_cursor: int, directive_indent: int) -> int:
    """Advance past directive options to the start of the body or blank separator."""
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
    """Collect contiguous indented body lines for a reStructuredText code block."""
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


def _expand_snippet_includes(body_lines: list[str], repo_root: Path) -> list[str]:
    """Expand pymdownx.snippets include lines inside a Markdown code block."""
    expanded: list[str] = []
    for line in body_lines:
        match = _SNIPPET_INCLUDE_PATTERN.match(line)
        if match:
            snippet_rel = match.group(1)
            snippet_path = (repo_root / snippet_rel).resolve()
            if snippet_path.is_file():
                expanded.extend(snippet_path.read_text(encoding="utf-8").splitlines())
                continue
        expanded.append(line)
    return expanded


def _extract_markdown_blocks(md_path: Path, lines: list[str], repo_root: Path) -> list[CodeBlock]:
    """Extract fenced code blocks from a Markdown document."""
    blocks: list[CodeBlock] = []
    line_count = len(lines)
    index = 0

    while index < line_count:
        match = _MD_FENCE_OPEN_PATTERN.match(lines[index])
        if not match:
            index += 1
            continue

        fence_chars = match.group(2)
        lang = match.group(3).lower()
        is_skipped = _is_block_skipped(lines, index)
        first_body_line = index + 2
        cursor = index + 1
        body_lines: list[str] = []

        close_pattern = re.compile(rf"^\s*{re.escape(fence_chars[0])}{{{len(fence_chars)},}}\s*$")
        while cursor < line_count and not close_pattern.match(lines[cursor]):
            body_lines.append(lines[cursor])
            cursor += 1

        if not is_skipped and body_lines and (lang in _TS_LANGS or lang in _VUE_SVELTE_LANGS or lang in _PY_LANGS):
            expanded_lines = _expand_snippet_includes(body_lines, repo_root)
            dedented_body = textwrap.dedent("\n".join(expanded_lines))
            if lang in _VUE_SVELTE_LANGS:
                script_block = _extract_script_block(md_path, first_body_line, expanded_lines)
                if script_block is not None:
                    blocks.append(script_block)
            else:
                blocks.append(
                    CodeBlock(rst_path=md_path, first_body_line=first_body_line, lang=lang, code=dedented_body)
                )

        index = cursor + 1

    return blocks


def extract_code_blocks(rst_path: Path, repo_root: Path | None = None) -> list[CodeBlock]:
    """Extract validated code blocks from a Markdown or reStructuredText file."""
    try:
        content = rst_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []

    resolved_root = repo_root or Path(__file__).resolve().parent.parent
    lines = content.splitlines()
    if rst_path.suffix.lower() == ".md":
        return _extract_markdown_blocks(rst_path, lines, resolved_root)

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
    """Extract the script element contents from a Vue or Svelte body."""
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
    """Generate a collision-resistant flat filename for a temp snippet."""
    clean_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", str(rst_path))
    return f"{clean_stem}__L{line}{ext}"


def _write_typescript_stubs(ts_dir: Path) -> None:
    """Write ambient declaration shims and generated stub modules for tsc."""
    ambient_path = ts_dir / "__ambient.d.ts"
    ambient_path.write_text(_AMBIENT_DECLARATIONS, encoding="utf-8")

    stub_generated = ts_dir / "generated"
    stub_generated.mkdir(exist_ok=True)
    (stub_generated / "routes.d.ts").write_text(
        "export const route: any;\n"
        "export const toRoute: any;\n"
        "export const wsRoute: any;\n"
        "export const currentRoute: any;\n"
        "export const isCurrentRoute: any;\n"
        "export const isRoute: any;\n"
        "export const hasRoute: any;\n"
        "export const routes: any;\n"
        "export const routeDefinitions: Record<string, any>;\n"
        "export type RouteName = string;\n"
        "export type RouteParams<T extends string = string> = Record<string, any>;\n",
        encoding="utf-8",
    )
    stub_api = ts_dir / "api"
    stub_api.mkdir(exist_ok=True)
    (stub_api / "types.gen.d.ts").write_text(
        "export interface InvoiceSummary { id: number; total: number; }\n", encoding="utf-8"
    )
    (stub_generated / "api.d.ts").write_text(
        "export const client: any;\n"
        "export const listItems: any;\n"
        "export const createItem: any;\n"
        "export const getApiSummary: any;\n"
        "export const getApiBooks: any;\n"
        "export const getApiBooksBookId: any;\n"
        "export type Book = any;\n"
        "export type Summary = any;\n",
        encoding="utf-8",
    )
    (stub_generated / "schemas.d.ts").write_text(
        "export const schemas: any;\n"
        "export type OperationName = any;\n"
        "export type FormInput<T = any> = any;\n"
        "export type FormResponse<T = any, S = any> = any;\n"
        "export type SuccessResponse<T = any> = any;\n"
        "export type ErrorResponse<T = any> = any;\n"
        "export type PathParams<T = any> = any;\n"
        "export type QueryParams<T = any> = any;\n",
        encoding="utf-8",
    )
    (stub_generated / "static-props.d.ts").write_text(
        "export const staticProps: any;\n"
        "export const appName: any;\n"
        "export const version: any;\n"
        "export const features: any;\n",
        encoding="utf-8",
    )
    (stub_generated / "channels.d.ts").write_text(
        "export const CHANNEL_METADATA: Record<string, any>;\nexport type RealtimeChannels = Record<string, any>;\n",
        encoding="utf-8",
    )
    (stub_generated / "page-props.d.ts").write_text(
        "export type OrdersPageProps = {\n"
        "    orders: Array<{ id: number; customer: string; total_cents: number }>;\n"
        "    selected_order?: { id: number; customer: string; total_cents: number } | null;\n"
        "    audit_log?: string[];\n"
        "    permissions?: string[];\n"
        "};\n",
        encoding="utf-8",
    )

    stub_types = ts_dir / "types"
    stub_types.mkdir(exist_ok=True)
    (stub_types / "shared-props.d.ts").write_text("export type SharedProps = any;\n", encoding="utf-8")


def _write_typescript_config(workdir: Path, ts_dir: Path, repo_root: Path) -> Path:
    """Create tsconfig.json in the workdir with package alias mappings."""
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
        "litestar-vite-plugin/fragments": [str(repo_root / "src" / "js" / "src" / "fragments" / "renderer.ts")],
        "litestar-vite-plugin/fragments/client": [str(repo_root / "src" / "js" / "src" / "fragments" / "client.ts")],
        "litestar-vite-plugin/fragments/react": [str(repo_root / "src" / "js" / "src" / "fragments" / "react.ts")],
        "litestar-vite-plugin/fragments/vue": [str(repo_root / "src" / "js" / "src" / "fragments" / "vue.ts")],
        "litestar-vite-plugin/fragments/svelte": [str(repo_root / "src" / "js" / "src" / "fragments" / "svelte.ts")],
        "litestar-vite-plugin/ssr-worker": [str(repo_root / "src" / "js" / "src" / "ssr-worker.ts")],
        "litestar-vite-plugin/astro": [str(repo_root / "src" / "js" / "src" / "astro.ts")],
        "litestar-vite-plugin/nuxt": [str(repo_root / "src" / "js" / "src" / "nuxt.ts")],
        "litestar-vite-plugin/sveltekit": [str(repo_root / "src" / "js" / "src" / "sveltekit.ts")],
        "litestar-vite-plugin": [str(repo_root / "src" / "js" / "src" / "index.ts")],
        "@/generated/*": [str(ts_dir / "generated" / "*")],
    }
    compiler_options["paths"] = paths_map

    workdir_tsconfig = {"compilerOptions": compiler_options, "include": [str(ts_dir / "**" / "*")]}
    tsconfig_path = workdir / "tsconfig.json"
    tsconfig_path.write_text(json.dumps(workdir_tsconfig, indent=2), encoding="utf-8")
    return tsconfig_path


def _parse_tsc_output(output_lines: list[str], block_map: dict[str, tuple[Path, int]]) -> list[Diagnostic]:
    """Parse compiler output lines into source-mapped Diagnostics."""
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
            current_diag = msgspec.structs.replace(current_diag, message=f"{current_diag.message} {line_clean.strip()}")

    if current_diag is not None:
        diagnostics.append(current_diag)

    return diagnostics


def check_typescript_blocks(blocks: list[CodeBlock], workdir: Path, repo_root: Path) -> list[Diagnostic]:
    """Type-check extracted TypeScript blocks with tsc --noEmit."""
    if not blocks:
        return []

    ts_dir = workdir / "ts"
    ts_dir.mkdir(parents=True, exist_ok=True)

    node_modules_target = repo_root / "node_modules"
    workdir_node_modules = workdir / "node_modules"
    if node_modules_target.exists() and not workdir_node_modules.exists():
        with contextlib.suppress(OSError):
            workdir_node_modules.symlink_to(node_modules_target)

    block_map: dict[str, tuple[Path, int]] = {}
    for block in blocks:
        has_jsx = block.lang == "tsx" or bool(re.search(r"<[A-Za-z][A-Za-z0-9]*[\s/>]", block.code))
        ext = ".tsx" if has_jsx else ".ts"
        fname = sanitize_filename(block.rst_path, block.first_body_line, ext)
        target_path = ts_dir / fname
        code_str = re.sub(r"\{\s*\.\.\.\s*\}(?:\s*as const\s*satisfies\s*\w+)?", "({} as any)", block.code)
        code_str = re.sub(r"//\s*\.\.\.\s*other routes", "[key: string]: any;", code_str)
        code_str = re.sub(r'///\s*<reference\s+types="litestar-vite-plugin/virtual"\s*/>', "", code_str)
        if "export function route" in code_str:
            line_list = code_str.splitlines()
            first_idx = -1
            last_idx = -1
            for i, candidate_line in enumerate(line_list):
                if candidate_line.strip().startswith("export function route"):
                    if first_idx == -1:
                        first_idx = i
                    last_idx = i
            if first_idx != -1 and last_idx != -1:
                line_list.insert(
                    first_idx,
                    "type RoutesWithoutRequiredParams = RouteName;\ntype RoutesWithRequiredParams = RouteName;",
                )
                line_list.insert(last_idx + 2, 'export function route(...args: any[]): any { return "" as any; }')
                code_str = "\n".join(line_list)
        target_path.write_text(code_str, encoding="utf-8")
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
    """Run ruff check --select F821 to identify undefined names in Python blocks."""
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

    cmd = [
        "uv",
        "run",
        "--no-sync",
        "ruff",
        "check",
        "--select",
        "F821",
        "--output-format",
        "concise",
        "--config",
        'builtins = ["VitePlugin", "ViteConfig", "RuntimeConfig", "TypeGenConfig", "Litestar", "Path"]',
        str(py_dir),
    ]
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
    """Resolve imported modules and symbols from an AST tree."""
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
                    if alias.name in _OPTIONAL_EXTERNAL_MODULES:
                        imported_modules[alias.asname or alias.name] = _StubModule()
                    else:
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
                if module_name in _OPTIONAL_EXTERNAL_MODULES:
                    for alias in node.names:
                        if alias.name != "*":
                            imported_symbols[alias.asname or alias.name] = _StubSymbol()
                else:
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
    """Validate keyword arguments of a Call against inspect.signature."""
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
    """Validate all calls in an AST tree against imported symbols and signatures."""
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
    """Validate imports, attributes, and callable signatures in Python blocks."""
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
    """Collect all target Markdown (.md) and reStructuredText (.rst) documentation files."""
    found: set[Path] = set()
    for path in paths:
        if path.is_file():
            found.add(path)
        elif path.is_dir():
            for md_path in path.rglob("*.md"):
                if "reference/typescript/" in md_path.as_posix():
                    continue
                found.add(md_path)
            for rst_path in path.rglob("*.rst"):
                found.add(rst_path)
    return sorted(found)


def main() -> int:
    """CLI entrypoint for documentation code example verification."""
    parser = argparse.ArgumentParser(description="Verify code examples embedded in documentation.")
    parser.add_argument(
        "--paths", nargs="+", default=["docs"], help="Path(s) to documentation files or directories to verify."
    )
    parser.add_argument(
        "--keep-workdir", action="store_true", help="Retain temporary files for inspection after execution."
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    target_paths = [Path(p) if Path(p).is_absolute() else (repo_root / p).resolve() for p in args.paths]
    doc_files = collect_rst_files(target_paths)

    all_blocks: list[CodeBlock] = []
    for doc_file in doc_files:
        try:
            rel_path = doc_file.relative_to(repo_root)
        except ValueError:
            rel_path = doc_file
        file_blocks = extract_code_blocks(doc_file, repo_root=repo_root)
        all_blocks.extend(msgspec.structs.replace(b, rst_path=rel_path) for b in file_blocks)

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
            sys.stdout.write(f"{diag}\n")

        total_files = len(doc_files)
        total_blocks = len(all_blocks)
        fail_count = len(diagnostics)

        summary = f"docs-example check: {total_blocks} blocks across {total_files} files, {fail_count} failures."
        sys.stdout.write(f"{summary}\n")

        return 1 if fail_count > 0 else 0
    finally:
        if not args.keep_workdir:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

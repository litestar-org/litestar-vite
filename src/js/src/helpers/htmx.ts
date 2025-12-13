/**
 * Litestar HTMX Extension
 *
 * Lightweight JSON templating for HTMX with CSRF support.
 *
 * Features:
 * - `hx-swap="json"` - Client-side JSON templating
 * - Automatic CSRF token injection
 * - Template syntax: `ls-for`, `ls-if`, `:attr`, `@event`, `${expr}`
 *
 * For typed routes, import from your generated routes file:
 * ```ts
 * import { route } from '@/generated/routes'
 * ```
 *
 * @example
 * ```html
 * <div hx-get="/api/books" hx-swap="json" hx-ext="litestar">
 *   <template ls-for="book in $data">
 *     <article :id="`book-${book.id}`">
 *       <h3>${book.title}</h3>
 *       <p>${book.author} • ${book.year}</p>
 *     </article>
 *   </template>
 * </div>
 * ```
 *
 * @module
 */

import { getCsrfToken } from "./csrf.js"

/** Type for route function - matches generated routes.ts */
type RouteFn = (name: string, params?: Record<string, string | number>) => string

declare global {
  interface Window {
    htmx?: HtmxApi
  }
}

interface HtmxApi {
  defineExtension: (name: string, ext: HtmxExtension) => void
  process: (elt: Element) => void
}

interface HtmxExtension {
  init?: () => void
  onEvent?: (name: string, evt: CustomEvent) => boolean | void
  transformResponse?: (text: string, xhr: XMLHttpRequest, elt: Element) => string
  isInlineSwap?: (swapStyle: string) => boolean
  handleSwap?: (swapStyle: string, target: Element, fragment: DocumentFragment | Element) => Element[]
}

type HtmxHeaders = Record<string, string> | Headers

interface HtmxConfigRequestEventDetail {
  headers?: HtmxHeaders
}

function getHeadersFromConfigRequestEvent(evt: CustomEvent): HtmxHeaders | null {
  const detail = evt.detail as unknown
  if (!detail || typeof detail !== "object") return null
  const { headers } = detail as HtmxConfigRequestEventDetail
  if (!headers || typeof headers !== "object") return null
  return headers
}

/** Template context - inherits from data via prototype for direct access */
interface Ctx {
  $data: unknown
  $parent?: Ctx
  $index?: number
  $key?: string
  $event?: Event
  route?: RouteFn
  navigate?: (name: string, params?: Record<string, string | number>) => void
  [key: string]: unknown
}

let debug = false
const cache = new Map<string, ((c: Ctx) => unknown) | null>()
const memoStore = new WeakMap<Node, Record<string, unknown>>()
const registeredHtmxInstances = new WeakSet<object>()

function runtime(node: Node): Record<string, unknown> {
  let store = memoStore.get(node)
  if (!store) {
    store = {}
    memoStore.set(node, store)
  }
  return store
}

// =============================================================================
// Registration
// =============================================================================

export function registerHtmxExtension(): void {
  if (typeof window === "undefined" || !window.htmx) return
  const htmx = window.htmx as unknown as object
  if (registeredHtmxInstances.has(htmx)) return
  registeredHtmxInstances.add(htmx)

  window.htmx.defineExtension("litestar", {
    onEvent(name, evt) {
      if (name === "htmx:configRequest") {
        const token = getCsrfToken()
        const headers = getHeadersFromConfigRequestEvent(evt)
        if (token && headers) {
          if (headers instanceof Headers) headers.set("X-CSRF-Token", token)
          else headers["X-CSRF-Token"] = token
        }
      }
      return true
    },

    transformResponse(text, xhr) {
      if (xhr.getResponseHeader("content-type")?.includes("application/json")) {
        const d = document.createElement("div")
        d.textContent = text
        return d.innerHTML
      }
      return text
    },

    isInlineSwap: (s) => s === "json",

    handleSwap(style, target, frag) {
      if (style === "json") {
        try {
          swapJson(target, JSON.parse(frag.textContent ?? ""))
        } catch (e) {
          target.innerHTML = `<div style="color:red;padding:1rem">${e}</div>`
        }
        return [target]
      }
      return []
    },
  })

  if (debug) console.log("[litestar] htmx extension registered")
}

// =============================================================================
// Note: hx-route functionality removed - use generated routes directly
// Import route from your generated routes.ts file instead:
//   import { route } from '@/generated/routes'
//   element.setAttribute('hx-get', route('my_route', { id: 123 }))
// =============================================================================

// =============================================================================
// JSON Swap Entry Point
// =============================================================================

export function swapJson(el: Element, data: unknown): void {
  swap(el, rootCtx(data))
}

// =============================================================================
// Core Swap Logic
// =============================================================================

function swap(node: Node, ctx: Ctx, end?: Node, parse = false): Node | null {
  // Text nodes: interpolate ${expr}
  if (node.nodeType === 3) {
    const g = memo(node, "t", () => {
      const t = node.textContent ?? ""
      return compileTextExpr(t)
    })
    if (!g) return null
    if (!parse) node.textContent = String(g(ctx) ?? "")
    return node
  }

  // Elements
  if (node.nodeType === 1) {
    const el = node as Element

    // Template: structural directives
    if (el.nodeName === "TEMPLATE") {
      return forDir(el as HTMLTemplateElement, ctx, end, parse) ?? ifDir(el as HTMLTemplateElement, ctx, end, parse)
    }

    // Process attribute directives
    let c: Ctx | false = ctx
    const handlers = memo(el, "a", () => {
      const h: Handler[] = []
      for (const attr of Array.from(el.attributes)) {
        const d = directives.find((x) => x.match(attr))
        if (d) {
          const handler = d.create(el, attr)
          if (handler) h.push(handler)
        }
      }
      return h
    })

    for (const h of handlers) {
      if (!parse && c) {
        const r = h(c, el)
        if (r !== undefined) c = r
      }
      if (!c) break
    }

    if (c === false) return el
    if (!c) return null

    // Recurse children
    swapKids(el.firstChild, undefined, c, parse)
    return el
  }

  return null
}

function swapKids(start: Node | null, end: Node | undefined, ctx: Ctx, parse = false): void {
  let current: Node | null = start
  while (current && current !== end) {
    const r = swap(current, ctx, end, parse)
    current = (r ?? current).nextSibling
  }
}

// =============================================================================
// Directives
// =============================================================================

type Handler = (ctx: Ctx, el: Element) => Ctx | false | void

interface Dir {
  match: (a: Attr) => boolean
  create: (el: Element, a: Attr) => Handler | null
}

const directives: Dir[] = [
  // :attr="expr" - attribute binding
  {
    match: (a) => a.name.startsWith(":"),
    create(_el, a) {
      const name = a.name.slice(1)
      const g = expr(a.value)
      if (!g) return null
      return (ctx, el) => {
        const v = g(ctx)
        if (name === "class" && typeof v === "object" && v) {
          for (const [k, on] of Object.entries(v)) el.classList.toggle(k, Boolean(on))
        } else if (v == null || v === false) {
          el.removeAttribute(name)
        } else {
          el.setAttribute(name, v === true ? "" : String(v))
        }
      }
    },
  },

  // @event="expr" - event binding
  {
    match: (a) => a.name.startsWith("@"),
    create(_el, a) {
      const name = a.name.slice(1)
      const g = expr(a.value)
      if (!g) return null
      return (ctx, el) => {
        const store = runtime(el)
        const ctxKey = `__litestar_ctx:${name}`
        const boundKey = `__litestar_bound:${name}`

        // Always keep the latest context for the handler
        store[ctxKey] = ctx

        // Bind the DOM listener only once per element+event
        if (store[boundKey]) return
        store[boundKey] = true

        el.addEventListener(name, (e) => {
          const current = memoStore.get(el)?.[ctxKey] as Ctx | undefined
          if (!current) return
          const eventCtx = Object.create(current) as Ctx
          eventCtx.$event = e
          g(eventCtx)
        })
      }
    },
  },

  // ls-scope="expr" - change context
  {
    match: (a) => a.name === "ls-scope",
    create(_, a) {
      const g = expr(a.value)
      if (!g) return null
      return (ctx) => {
        const d = g(ctx)
        return d ? childCtx(ctx, d) : false
      }
    },
  },

  // ls-text="expr" - text content
  {
    match: (a) => a.name === "ls-text",
    create(_, a) {
      const g = expr(a.value)
      if (!g) return null
      return (ctx, el) => {
        el.textContent = String(g(ctx) ?? "")
      }
    },
  },

  // ls-html="expr" - innerHTML (use carefully)
  {
    match: (a) => a.name === "ls-html",
    create(_, a) {
      const g = expr(a.value)
      if (!g) return null
      return (ctx, el) => {
        el.innerHTML = String(g(ctx) ?? "")
      }
    },
  },

  // ls-show/ls-hide
  {
    match: (a) => a.name === "ls-show",
    create(_, a) {
      const g = expr(a.value)
      if (!g) return null
      return (ctx, el) => {
        ;(el as HTMLElement).style.display = g(ctx) ? "" : "none"
      }
    },
  },
  {
    match: (a) => a.name === "ls-hide",
    create(_, a) {
      const g = expr(a.value)
      if (!g) return null
      return (ctx, el) => {
        ;(el as HTMLElement).style.display = g(ctx) ? "none" : ""
      }
    },
  },

  // name attr on inputs - auto-bind from context
  {
    match: (a) => a.name === "name",
    create(el, a) {
      if (!(el instanceof HTMLInputElement || el instanceof HTMLSelectElement || el instanceof HTMLTextAreaElement)) return null
      const key = a.value
      return (ctx, el) => {
        const v = ctx[key]
        if (v === undefined) return
        const inp = el as HTMLInputElement
        if (inp.type === "checkbox") inp.checked = Boolean(v)
        else if (inp.type === "radio") inp.checked = v === inp.value
        else inp.value = String(v ?? "")
      }
    },
  },
]

// =============================================================================
// Structural: ls-for
// =============================================================================

function forDir(tpl: HTMLTemplateElement, ctx: Ctx, _parentEnd?: Node, parse = false): Node | null {
  const raw = tpl.getAttribute("ls-for") ?? tpl.getAttribute("ls-each")
  if (!raw) return null

  preparseTpl(tpl)
  if (parse) return tpl

  // Parse "item in items" or just "items"
  const m = raw.match(/^\s*(\w+)\s+in\s+(.+)$/)
  const [alias, listExpr] = m ? [m[1], m[2]] : [null, raw]

  const g = memo(tpl, "g", () => expr(listExpr))
  if (!g) return null

  const items = toList(g(ctx), tpl, ctx, alias)
  const end = memo(tpl, "end", () => insertComment(tpl, "/ls-for"))
  const old: [string, Comment][] = memo(tpl, "list", () => collectComments(tpl, end))

  let i = 0
  for (; i < items.length; i++) {
    const [key, item] = items[i]
    const c = childCtx(ctx, item, i, key)
    if (alias) c[alias] = item

    if (i < old.length && old[i][0] === key) {
      // Same key: update in place
      swapKids(old[i][1].nextSibling, old[i + 1]?.[1] ?? end, c)
    } else {
      // Insert new
      const clone = tpl.content.cloneNode(true)
      const comment = document.createComment(key)
      const ref = old[i]?.[1] ?? end
      ref.parentNode?.insertBefore(comment, ref)
      ref.parentNode?.insertBefore(clone, ref)
      swapKids(comment.nextSibling, ref, c)

      // Remove old if exists
      if (i < old.length) {
        removeBetween(old[i][1], old[i + 1]?.[1] ?? end)
        old[i][1].remove()
      }
      old[i] = [key, comment]
    }
  }

  // Remove excess
  while (old.length > items.length) {
    const popped = old.pop()
    if (!popped) break
    const [, c] = popped
    removeBetween(c, old[old.length]?.[1] ?? end)
    c.remove()
  }

  return end
}

// =============================================================================
// Structural: ls-if
// =============================================================================

function ifDir(tpl: HTMLTemplateElement, ctx: Ctx, _parentEnd?: Node, parse = false): Node | null {
  const raw = tpl.getAttribute("ls-if")
  if (!raw) return null

  preparseTpl(tpl)

  // Find else template
  const elseTpl = tpl.nextElementSibling?.nodeName === "TEMPLATE" && tpl.nextElementSibling.hasAttribute("ls-else") ? (tpl.nextElementSibling as HTMLTemplateElement) : null
  if (elseTpl) preparseTpl(elseTpl)

  if (parse) return elseTpl ?? tpl

  const g = memo(tpl, "g", () => expr(raw))
  const anchor = memo(tpl, "anchor", () => insertComment(tpl, ""))
  const end = memo(tpl, "end", () => insertComment(anchor, "/ls-if"))

  const show = g?.(ctx)

  if (show) {
    if (anchor.data !== "if") {
      anchor.data = "if"
      removeBetween(anchor.nextSibling, end)
      end.parentNode?.insertBefore(tpl.content.cloneNode(true), end)
    }
    swapKids(anchor.nextSibling, end, ctx)
  } else if (elseTpl) {
    if (anchor.data !== "else") {
      anchor.data = "else"
      removeBetween(anchor.nextSibling, end)
      end.parentNode?.insertBefore(elseTpl.content.cloneNode(true), end)
    }
    swapKids(anchor.nextSibling, end, ctx)
  } else {
    anchor.data = ""
    removeBetween(anchor.nextSibling, end)
  }

  return end
}

// =============================================================================
// Context
// =============================================================================

function rootCtx(data: unknown): Ctx {
  const ctx: Ctx = {
    $data: data,
    // Note: route and navigate are optional - users can provide their own
    // by importing from their generated routes.ts file
  }
  if (data && typeof data === "object") Object.setPrototypeOf(ctx, data)
  return ctx
}

function childCtx(parent: Ctx, data: unknown, index?: number, key?: string): Ctx {
  const ctx = Object.create(data && typeof data === "object" ? data : null) as Ctx
  ctx.$data = data
  ctx.$parent = parent
  ctx.$index = index
  ctx.$key = key
  ctx.route = parent.route
  ctx.navigate = parent.navigate
  return ctx
}

// =============================================================================
// Expression Compiler
// =============================================================================

function expr(s: string | null): ((c: Ctx) => unknown) | null {
  if (!s) return null
  const cached = cache.get(s)
  if (cached !== undefined) return cached

  try {
    const fn = new Function("ctx", `with(ctx){return(${s})}`) as (c: Ctx) => unknown
    cache.set(s, fn)
    return fn
  } catch {
    cache.set(s, null)
    return null
  }
}

/** Compile text with ${expr} interpolation - escapes backticks and backslashes */
function compileTextExpr(t: string): ((c: Ctx) => unknown) | null {
  if (!t.includes("${")) return null
  // Escape backticks and backslashes for safe template literal compilation
  const escaped = t.replace(/[`\\]/g, "\\$&")
  return expr(`\`${escaped}\``)
}

// =============================================================================
// Utilities
// =============================================================================

function memo<T>(node: Node, key: string, fn: () => T): T {
  const store = runtime(node)
  if (!(key in store)) {
    store[key] = fn()
  }
  return store[key] as T
}

function preparseTpl(t: HTMLTemplateElement): void {
  memo(t, "p", () => {
    swapKids(t.content.firstChild, undefined, {} as Ctx, true)
    return true
  })
}

function toList(items: unknown, tpl: HTMLTemplateElement, ctx: Ctx, alias: string | null): [string, unknown][] {
  const keyAttr = tpl.getAttribute("ls-key")
  const keyFn = keyAttr ? expr(keyAttr) : null

  if (Array.isArray(items)) {
    return items.map((item, i) => {
      if (!keyFn) return [String(i), item]
      // Create a child context with the alias so key expressions like "item.id" work
      const keyCtx = childCtx(ctx, item, i)
      if (alias) keyCtx[alias] = item
      return [String(keyFn(keyCtx)), item]
    })
  }
  if (items && typeof items === "object") {
    return Object.entries(items)
  }
  return []
}

function insertComment(after: Node, text: string): Comment {
  const c = document.createComment(text)
  after.parentNode?.insertBefore(c, after.nextSibling)
  return c
}

function collectComments(tpl: Node, end: Node): [string, Comment][] {
  const list: [string, Comment][] = []
  let n = tpl.nextSibling
  while (n && n !== end) {
    if (n.nodeType === 8 && !(n as Comment).data.startsWith("/")) {
      list.push([(n as Comment).data, n as Comment])
    }
    n = n.nextSibling
  }
  return list
}

function removeBetween(start: Node | null, end: Node): void {
  let current = start
  while (current && current !== end) {
    const next = current.nextSibling
    current.parentNode?.removeChild(current)
    current = next
  }
}

// =============================================================================
// Public API
// =============================================================================

/**
 * Enable or disable debug logging for the HTMX extension.
 *
 * @param on - Whether to enable debug logging.
 */
export function setDebug(on: boolean): void {
  debug = on
}

export function addDirective(dir: Dir): void {
  directives.push(dir)
}

// Auto-register

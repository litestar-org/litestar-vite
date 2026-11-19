/* biome-ignore-all lint/suspicious/noTemplateCurlyInString: Testing ${expr} template syntax intentionally */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import {
  __clearExpressionCache,
  __compileExpressionForTest,
  __getExpressionCacheKeys,
  __getExpressionCacheSize,
  __setExpressionCacheLimit,
  addDirective,
  registerHtmxExtension,
  swapJson,
} from "../../src/helpers/htmx"
import type { HtmxExtensionOptions } from "../../src/helpers/index"

describe("htmx extension", () => {
  let container: HTMLElement

  beforeEach(() => {
    container = document.createElement("div")
    document.body.appendChild(container)
  })

  afterEach(() => {
    container.remove()
    vi.restoreAllMocks()
  })

  describe("swapJson", () => {
    describe("text interpolation", () => {
      it("interpolates ${expr} in text nodes", () => {
        container.innerHTML = "<p>${title}</p>"
        swapJson(container, { title: "Hello World" })
        expect(container.innerHTML).toBe("<p>Hello World</p>")
      })

      it("handles multiple expressions in text", () => {
        container.innerHTML = "<p>${firstName} ${lastName}</p>"
        swapJson(container, { firstName: "John", lastName: "Doe" })
        expect(container.innerHTML).toBe("<p>John Doe</p>")
      })

      it("handles expressions with operators", () => {
        container.innerHTML = "<p>${count + 1}</p>"
        swapJson(container, { count: 5 })
        expect(container.innerHTML).toBe("<p>6</p>")
      })

      it("handles method calls", () => {
        container.innerHTML = "<p>${items.join(', ')}</p>"
        swapJson(container, { items: ["a", "b", "c"] })
        expect(container.innerHTML).toBe("<p>a, b, c</p>")
      })

      it("handles ternary expressions", () => {
        container.innerHTML = "<p>${active ? 'Yes' : 'No'}</p>"
        swapJson(container, { active: true })
        expect(container.innerHTML).toBe("<p>Yes</p>")
      })
    })

    describe("ls-text directive", () => {
      it("sets text content from expression", () => {
        container.innerHTML = '<p ls-text="name"></p>'
        swapJson(container, { name: "Alice" })
        expect(container.querySelector("p")?.textContent).toBe("Alice")
      })

      it("handles nested property access", () => {
        container.innerHTML = '<p ls-text="user.name"></p>'
        swapJson(container, { user: { name: "Bob" } })
        expect(container.querySelector("p")?.textContent).toBe("Bob")
      })

      it("does not interpolate template syntax inside ls-text values", () => {
        container.innerHTML = '<p ls-text="msg"></p>'
        swapJson(container, { msg: "${1+1}" })
        expect(container.querySelector("p")?.textContent).toBe("${1+1}")

        swapJson(container, { msg: "${2+2}" })
        expect(container.querySelector("p")?.textContent).toBe("${2+2}")
      })

      it.each(['<p :class="{ active: isActive }" ls-text="msg"></p>', '<p ls-text="msg" :class="{ active: isActive }"></p>'])(
        "preserves sibling directives while isolating children for %s",
        (markup) => {
          container.innerHTML = markup
          swapJson(container, { isActive: true, msg: "${1+1}" })
          const p = container.querySelector("p")
          expect(p?.classList.contains("active")).toBe(true)
          expect(p?.textContent).toBe("${1+1}")
        },
      )
    })

    describe("ls-html directive", () => {
      it("sets innerHTML from expression", () => {
        container.innerHTML = '<div ls-html="content"></div>'
        swapJson(container, { content: "<strong>Bold</strong>" })
        expect(container.querySelector("div")?.innerHTML).toBe("<strong>Bold</strong>")
      })

      it("strips script tags from ls-html output", () => {
        container.innerHTML = '<div ls-html="content"></div>'
        swapJson(container, { content: "<p>Hello</p><script>alert(1)</script>" })
        const div = container.querySelector("div")
        expect(div?.querySelector("script")).toBeNull()
        expect(div?.querySelector("p")?.textContent).toBe("Hello")
      })

      it.each([
        ["template", '<template><img src="x" onerror="alert(1)"></template>'],
        ["script", "<script>alert(1)</script>"],
        ["style", "<style>body { color: red; }</style>"],
        ["iframe", '<iframe src="https://example.com"></iframe>'],
        ["object", '<object data="https://example.com"></object>'],
        ["embed", '<embed src="https://example.com">'],
        ["svg", '<svg onload="alert(1)"><circle cx="5" cy="5" r="5"></circle></svg>'],
        ["math", "<math><mi>x</mi></math>"],
        ["base", '<base href="https://other.example/">'],
        ["meta", '<meta http-equiv="refresh" content="0;url=https://other.example">'],
        ["link", '<link rel="stylesheet" href="https://other.example/a.css">'],
        ["form", '<form action="/submit"><p>nested</p></form>'],
        ["form", '<form><input name="tagName"></form>'],
        ["form", '<form><input name="parentNode"></form>'],
        ["form", '<form><input name="tagName"><input name="parentNode"><input name="nodeType"></form>'],
        ["litestar-stream", "<litestar-stream><p>nested</p></litestar-stream>"],
        ["litestar-island", "<litestar-island><p>nested</p></litestar-island>"],
        ["custom-widget", "<custom-widget><span>nested</span></custom-widget>"],
      ])("removes disallowed %s elements and their descendants from ls-html output", (tagName, markup) => {
        container.innerHTML = '<div ls-html="content"></div>'
        swapJson(container, { content: `<p>Safe</p>${markup}` })
        const div = container.querySelector("div")
        expect(div?.querySelector(tagName)).toBeNull()
        expect(div?.innerHTML).toBe("<p>Safe</p>")
      })

      it("removes form elements even when tagName, parentNode, or nodeType are DOM-clobbered", () => {
        const origCreateElement = document.createElement.bind(document)
        vi.spyOn(document, "createElement").mockImplementation(((tagName: string, options?: ElementCreationOptions) => {
          const el = origCreateElement(tagName, options)
          if (tagName.toLowerCase() === "template") {
            const tpl = el as HTMLTemplateElement
            const origDescriptor = Object.getOwnPropertyDescriptor(Element.prototype, "innerHTML")
            Object.defineProperty(tpl, "innerHTML", {
              configurable: true,
              get() {
                return origDescriptor?.get?.call(tpl) ?? ""
              },
              set(value: string) {
                origDescriptor?.set?.call(tpl, value)
                for (const form of Array.from(tpl.content.querySelectorAll("form"))) {
                  const tagClobber = form.querySelector('input[name="tagName"]')
                  const parentClobber = form.querySelector('input[name="parentNode"]')
                  const nodeTypeClobber = form.querySelector('input[name="nodeType"]')
                  if (tagClobber) {
                    Object.defineProperty(form, "tagName", { configurable: true, value: tagClobber })
                  }
                  if (parentClobber) {
                    Object.defineProperty(form, "parentNode", { configurable: true, value: parentClobber })
                  }
                  if (nodeTypeClobber) {
                    Object.defineProperty(form, "nodeType", { configurable: true, value: nodeTypeClobber })
                  }
                }
              },
            })
          }
          return el
        }) as typeof document.createElement)

        container.innerHTML = '<div ls-html="content"></div>'
        swapJson(container, {
          content: '<p>Safe</p><form><input name="tagName"><input name="parentNode"></form><form><input name="nodeType"></form>',
        })
        const div = container.querySelector("div")
        expect(div?.querySelector("form")).toBeNull()
        expect(div?.innerHTML).toBe("<p>Safe</p>")
      })

      it("removes comment nodes from ls-html output", () => {
        container.innerHTML = '<div ls-html="content"></div>'
        swapJson(container, { content: "<p>Keep</p><!-- hidden comment -->" })
        const div = container.querySelector("div")
        expect(div?.innerHTML).toBe("<p>Keep</p>")
        expect(div?.childNodes.length).toBe(1)
      })

      it("strips event handler attributes from ls-html output", () => {
        container.innerHTML = '<div ls-html="content"></div>'
        swapJson(container, { content: '<img src="x" onerror="alert(1)">' })
        const img = container.querySelector("img")
        expect(img?.getAttribute("onerror")).toBeNull()
      })

      it.each(["onclick", "ls-text", "data-ls-text", ":href", "@click", "hx-get", "data-hx-get", "data-hx-on--load", "srcdoc", "formaction", "style"])(
        "strips disallowed attribute %s in ls-html while preserving safe attributes",
        (attrName) => {
          container.innerHTML = '<div ls-html="content"></div>'
          swapJson(container, {
            content: `<a class="btn" aria-label="Open" data-item-id="42" ${attrName}="payload">Link</a>`,
          })
          const link = container.querySelector("a")
          expect(link?.hasAttribute(attrName)).toBe(false)
          expect(link?.getAttribute("class")).toBe("btn")
          expect(link?.getAttribute("aria-label")).toBe("Open")
          expect(link?.getAttribute("data-item-id")).toBe("42")
        },
      )

      it("strips javascript: protocol from href", () => {
        container.innerHTML = '<div ls-html="content"></div>'
        swapJson(container, { content: '<a href="javascript:alert(1)">Click</a>' })
        const a = container.querySelector("a")
        // href should be removed entirely
        expect(a?.hasAttribute("href")).toBe(false)
      })

      it.each([
        ["a", "href", "\tjavascript:1"],
        ["a", "href", "\x01\t j\ta\nv\ra script:alert(1)"],
        ["a", "href", "\x01data:text/html,x"],
        ["a", "href", "vbscript:1"],
        ["a", "href", "//other.example/x"],
        ["a", "href", "/\\other.example/x"],
        ["a", "href", "\\\\other.example/x"],
        ["a", "href", "\\/other.example/x"],
        ["img", "src", "\x01data:text/html,x"],
        ["blockquote", "cite", "\tjavascript:1"],
        ["a", "xlink:href", "javascript:1"],
        ["a", "action", "javascript:1"],
        ["a", "poster", "javascript:1"],
      ])("strips unsafe %s[%s] URL %j in ls-html", (tag, attr, url) => {
        container.innerHTML = '<div ls-html="content"></div>'
        swapJson(container, { content: `<${tag} ${attr}="${url}">Item</${tag}>` })
        const element = container.querySelector(tag)
        expect(element?.hasAttribute(attr)).toBe(false)
      })

      it.each([
        ["a", "href", "/page"],
        ["a", "href", "/docs/v1:2"],
        ["a", "href", "#sec:1"],
        ["a", "href", "?next=https://example.com"],
        ["a", "href", "https://example.com"],
        ["a", "href", "http://example.com"],
        ["a", "href", "mailto:a@b.com"],
        ["a", "href", "tel:+15551234"],
        ["img", "src", "https://example.com/logo.png"],
        ["blockquote", "cite", "https://example.com/source"],
      ])("preserves safe %s[%s] URL %j in ls-html", (tag, attr, url) => {
        container.innerHTML = '<div ls-html="content"></div>'
        swapJson(container, { content: `<${tag} ${attr}="${url}">Item</${tag}>` })
        const element = container.querySelector(tag)
        expect(element?.getAttribute(attr)).toBe(url)
      })

      it("does not execute directives or text interpolation inside ls-html content", () => {
        container.innerHTML = '<div :class="{ active: isActive }" ls-html="body"></div>'
        swapJson(container, {
          isActive: true,
          secret: "LEAKED",
          body: '<span ls-text="secret">${1+1}</span><p :id="1+1">${1+1}</p>',
        })
        const div = container.querySelector("div")
        expect(div?.classList.contains("active")).toBe(true)
        expect(div?.innerHTML).toBe("<span>${1+1}</span><p>${1+1}</p>")
      })

      it("isolates ls-html children inside ls-for templates", () => {
        container.innerHTML = `
          <div>
            <template ls-for="item in items">
              <article ls-html="item.body"></article>
            </template>
          </div>
        `
        swapJson(container, {
          items: [{ body: '<span ls-text="missing">${1+1}</span>' }],
        })
        expect(container.querySelector("article")?.innerHTML).toBe("<span>${1+1}</span>")
      })

      it("preserves safe HTML elements and attributes", () => {
        container.innerHTML = '<div ls-html="content"></div>'
        swapJson(container, {
          content: '<a href="/page" class="link"><em>Hello</em></a><br><ul><li>Item</li></ul>',
        })
        const div = container.querySelector("div")
        expect(div?.querySelector("a")?.getAttribute("href")).toBe("/page")
        expect(div?.querySelector("em")?.textContent).toBe("Hello")
        expect(div?.querySelector("li")?.textContent).toBe("Item")
      })
    })

    describe(":attr binding", () => {
      it("binds simple attribute", () => {
        container.innerHTML = '<a :href="url">Link</a>'
        swapJson(container, { url: "/path" })
        expect(container.querySelector("a")?.getAttribute("href")).toBe("/path")
      })

      it.each(["onclick", "onerror", "srcdoc", "formaction", "hx-get", "data-hx-get", "ls-html", "data-ls-text"])("blocks dynamic :%s attribute binding", (attrName) => {
        container.innerHTML = `<a :${attrName}="payload">Link</a>`
        swapJson(container, { payload: "blocked-value" })
        expect(container.querySelector("a")?.hasAttribute(attrName)).toBe(false)
      })

      it.each([
        ["a", "href"],
        ["img", "src"],
        ["form", "action"],
        ["a", "xlink:href"],
        ["video", "poster"],
        ["blockquote", "cite"],
      ])("removes unsafe URL values from %s :%s bindings", (tag, attr) => {
        const unsafeUrls = [
          "\tjavascript:1",
          "\x01\t j\ta\nv\ra script:alert(1)",
          "\x01data:text/html,x",
          "vbscript:1",
          "//other.example/x",
          "/\\other.example/x",
          "\\\\other.example/x",
          "\\/other.example/x",
        ]
        for (const url of unsafeUrls) {
          container.innerHTML = `<${tag} :${attr}="url"></${tag}>`
          swapJson(container, { url })
          expect(container.querySelector(tag)?.hasAttribute(attr)).toBe(false)
        }
      })

      it.each(["/page", "/a:b", "#sec:1", "?next=https://example.com", "https://example.com", "http://example.com", "mailto:a@b.com", "tel:+15551234"])(
        "preserves allowed URL %j in dynamic :href binding",
        (url) => {
          container.innerHTML = '<a :href="url">Link</a>'
          swapJson(container, { url })
          expect(container.querySelector("a")?.getAttribute("href")).toBe(url)
        },
      )

      it("removes dangerous URL protocols from href bindings", () => {
        container.innerHTML = '<a :href="url">Link</a>'
        swapJson(container, { url: "javascript:alert(1)" })
        expect(container.querySelector("a")?.hasAttribute("href")).toBe(false)
      })

      it("removes dangerous URL protocols from src bindings", () => {
        container.innerHTML = '<img :src="url">'
        swapJson(container, { url: "javascript:alert(1)" })
        expect(container.querySelector("img")?.hasAttribute("src")).toBe(false)
      })

      it("removes dangerous URL protocols from action bindings", () => {
        container.innerHTML = '<form :action="url"></form>'
        swapJson(container, { url: "javascript:alert(1)" })
        expect(container.querySelector("form")?.hasAttribute("action")).toBe(false)
      })

      it("binds id with template literal", () => {
        container.innerHTML = '<div :id="`item-${id}`"></div>'
        swapJson(container, { id: 42 })
        expect(container.querySelector("div")?.id).toBe("item-42")
      })

      it("removes attribute when value is null", () => {
        container.innerHTML = '<input :disabled="isDisabled">'
        swapJson(container, { isDisabled: null })
        expect(container.querySelector("input")?.hasAttribute("disabled")).toBe(false)
      })

      it("removes attribute when value is false", () => {
        container.innerHTML = '<input :disabled="isDisabled">'
        swapJson(container, { isDisabled: false })
        expect(container.querySelector("input")?.hasAttribute("disabled")).toBe(false)
      })

      it("sets boolean attribute when value is true", () => {
        container.innerHTML = '<input :disabled="isDisabled">'
        swapJson(container, { isDisabled: true })
        expect(container.querySelector("input")?.hasAttribute("disabled")).toBe(true)
      })

      it("handles :class with object syntax", () => {
        container.innerHTML = '<div :class="{ active: isActive, hidden: isHidden }"></div>'
        swapJson(container, { isActive: true, isHidden: false })
        const div = container.querySelector("div")
        expect(div?.classList.contains("active")).toBe(true)
        expect(div?.classList.contains("hidden")).toBe(false)
      })

      it("handles :class with string", () => {
        container.innerHTML = '<div :class="className"></div>'
        swapJson(container, { className: "foo bar" })
        expect(container.querySelector("div")?.getAttribute("class")).toBe("foo bar")
      })
    })

    describe("@event binding", () => {
      it("uses the latest context after subsequent swaps", () => {
        container.innerHTML = '<button @click="onClick(id)"></button>'

        const first = vi.fn()
        swapJson(container, { id: 1, onClick: first })

        ;(container.querySelector("button") as HTMLButtonElement).click()
        expect(first).toHaveBeenCalledWith(1)

        const second = vi.fn()
        swapJson(container, { id: 2, onClick: second })

        ;(container.querySelector("button") as HTMLButtonElement).click()
        expect(second).toHaveBeenCalledWith(2)
        expect(first).toHaveBeenCalledTimes(1)
      })

      it("exposes a sanitized plain-object event wrapper", () => {
        container.innerHTML = '<input name="q" @input="capture($event)">'
        const capture = vi.fn()
        swapJson(container, { capture })

        const input = container.querySelector("input") as HTMLInputElement
        input.value = "search"
        input.dispatchEvent(new Event("input"))

        const event = capture.mock.calls[0]?.[0] as Record<string, unknown>
        expect((event.target as Record<string, unknown>).value).toBe("search")
        expect(event.preventDefault).toBeTypeOf("function")
        expect(event.view).toBeUndefined()
      })
    })

    describe("ls-show/ls-hide", () => {
      it("ls-show shows element when true", () => {
        container.innerHTML = '<div ls-show="visible">Content</div>'
        swapJson(container, { visible: true })
        expect((container.querySelector("div") as HTMLElement).style.display).toBe("")
      })

      it("ls-show hides element when false", () => {
        container.innerHTML = '<div ls-show="visible">Content</div>'
        swapJson(container, { visible: false })
        expect((container.querySelector("div") as HTMLElement).style.display).toBe("none")
      })

      it("ls-hide hides element when true", () => {
        container.innerHTML = '<div ls-hide="hidden">Content</div>'
        swapJson(container, { hidden: true })
        expect((container.querySelector("div") as HTMLElement).style.display).toBe("none")
      })

      it("ls-hide shows element when false", () => {
        container.innerHTML = '<div ls-hide="hidden">Content</div>'
        swapJson(container, { hidden: false })
        expect((container.querySelector("div") as HTMLElement).style.display).toBe("")
      })
    })

    describe("ls-for loop", () => {
      it("renders array items", () => {
        container.innerHTML = `
          <ul>
            <template ls-for="item in $data">
              <li>\${item}</li>
            </template>
          </ul>
        `
        swapJson(container, ["a", "b", "c"])
        const items = container.querySelectorAll("li")
        expect(items.length).toBe(3)
        expect(items[0].textContent).toBe("a")
        expect(items[1].textContent).toBe("b")
        expect(items[2].textContent).toBe("c")
      })

      it("renders object array with alias", () => {
        container.innerHTML = `
          <ul>
            <template ls-for="book in $data">
              <li>\${book.title}</li>
            </template>
          </ul>
        `
        swapJson(container, [{ title: "Book A" }, { title: "Book B" }])
        const items = container.querySelectorAll("li")
        expect(items.length).toBe(2)
        expect(items[0].textContent).toBe("Book A")
        expect(items[1].textContent).toBe("Book B")
      })

      it("provides $index in loop context", () => {
        container.innerHTML = `
          <ul>
            <template ls-for="item in $data">
              <li>\${$index}: \${item}</li>
            </template>
          </ul>
        `
        swapJson(container, ["first", "second"])
        const items = container.querySelectorAll("li")
        expect(items[0].textContent).toBe("0: first")
        expect(items[1].textContent).toBe("1: second")
      })

      it("supports ls-key for keyed rendering", () => {
        container.innerHTML = `
          <ul>
            <template ls-for="item in $data" ls-key="item.id">
              <li :id="\`item-\${item.id}\`">\${item.name}</li>
            </template>
          </ul>
        `
        swapJson(container, [
          { id: 1, name: "One" },
          { id: 2, name: "Two" },
        ])
        expect(container.querySelector("#item-1")?.textContent).toBe("One")
        expect(container.querySelector("#item-2")?.textContent).toBe("Two")
      })

      it("handles empty arrays", () => {
        container.innerHTML = `
          <ul>
            <template ls-for="item in $data">
              <li>\${item}</li>
            </template>
          </ul>
        `
        swapJson(container, [])
        expect(container.querySelectorAll("li").length).toBe(0)
      })

      it("supports ls-each as alias for ls-for", () => {
        container.innerHTML = `
          <ul>
            <template ls-each="items">
              <li>\${name}</li>
            </template>
          </ul>
        `
        swapJson(container, { items: [{ name: "A" }, { name: "B" }] })
        const items = container.querySelectorAll("li")
        expect(items.length).toBe(2)
      })
    })

    describe("ls-if conditional", () => {
      it("renders content when condition is true", () => {
        container.innerHTML = `
          <div>
            <template ls-if="show">
              <p>Visible</p>
            </template>
          </div>
        `
        swapJson(container, { show: true })
        expect(container.querySelector("p")?.textContent).toBe("Visible")
      })

      it("does not render when condition is false", () => {
        container.innerHTML = `
          <div>
            <template ls-if="show">
              <p>Visible</p>
            </template>
          </div>
        `
        swapJson(container, { show: false })
        expect(container.querySelector("p")).toBeNull()
      })

      it("supports ls-else", () => {
        container.innerHTML = `
          <div>
            <template ls-if="loggedIn">
              <p>Welcome</p>
            </template>
            <template ls-else>
              <p>Please log in</p>
            </template>
          </div>
        `
        swapJson(container, { loggedIn: false })
        expect(container.querySelector("p")?.textContent).toBe("Please log in")
      })

      it("handles complex conditions", () => {
        container.innerHTML = `
          <div>
            <template ls-if="count > 0">
              <p>\${count} items</p>
            </template>
            <template ls-else>
              <p>No items</p>
            </template>
          </div>
        `
        swapJson(container, { count: 5 })
        expect(container.querySelector("p")?.textContent).toBe("5 items")
      })
    })

    describe("ls-scope", () => {
      it("changes context for children", () => {
        container.innerHTML = `
          <div ls-scope="user">
            <p>\${name}</p>
            <p>\${email}</p>
          </div>
        `
        swapJson(container, { user: { name: "Alice", email: "alice@example.com" } })
        const paragraphs = container.querySelectorAll("p")
        expect(paragraphs[0].textContent).toBe("Alice")
        expect(paragraphs[1].textContent).toBe("alice@example.com")
      })

      it("hides element when scope is falsy", () => {
        container.innerHTML = `
          <div ls-scope="user">
            <p>\${name}</p>
          </div>
        `
        swapJson(container, { user: null })
        // Element should still exist but content not rendered
        expect(container.querySelector("div")).toBeTruthy()
      })
    })

    describe("input binding", () => {
      it("binds input value from context by name", () => {
        container.innerHTML = '<input type="text" name="username">'
        swapJson(container, { username: "johndoe" })
        expect((container.querySelector("input") as HTMLInputElement).value).toBe("johndoe")
      })

      it("binds checkbox checked state", () => {
        container.innerHTML = '<input type="checkbox" name="agree">'
        swapJson(container, { agree: true })
        expect((container.querySelector("input") as HTMLInputElement).checked).toBe(true)
      })

      it("binds radio button checked state", () => {
        container.innerHTML = `
          <input type="radio" name="color" value="red">
          <input type="radio" name="color" value="blue">
        `
        swapJson(container, { color: "blue" })
        const inputs = container.querySelectorAll("input")
        expect((inputs[0] as HTMLInputElement).checked).toBe(false)
        expect((inputs[1] as HTMLInputElement).checked).toBe(true)
      })
    })

    describe("context helpers", () => {
      // Note: route() helper is no longer built-in. Users should import from generated routes.ts
      // See: import { route } from '@/generated/routes'

      it("provides $data alias for root data", () => {
        container.innerHTML = "<p>${JSON.stringify($data)}</p>"
        swapJson(container, { name: "test" })
        expect(container.querySelector("p")?.textContent).toBe('{"name":"test"}')
      })

      it("provides $parent in loops", () => {
        container.innerHTML = `
          <div>
            <template ls-for="item in items">
              <p>\${item} from \${$parent.source}</p>
            </template>
          </div>
        `
        swapJson(container, { items: ["a", "b"], source: "list" })
        const paragraphs = container.querySelectorAll("p")
        expect(paragraphs[0].textContent).toBe("a from list")
      })
    })

    describe("nested loops", () => {
      it("handles nested ls-for", () => {
        container.innerHTML = `
          <div>
            <template ls-for="group in $data">
              <section>
                <h2>\${group.name}</h2>
                <template ls-for="item in group.items">
                  <p>\${item}</p>
                </template>
              </section>
            </template>
          </div>
        `
        swapJson(container, [
          { name: "Group A", items: ["a1", "a2"] },
          { name: "Group B", items: ["b1"] },
        ])
        const sections = container.querySelectorAll("section")
        expect(sections.length).toBe(2)
        expect(sections[0].querySelectorAll("p").length).toBe(2)
        expect(sections[1].querySelectorAll("p").length).toBe(1)
      })
    })
  })

  // ===== Expression Security =====

  describe("expression sandbox (allowlist evaluator)", () => {
    beforeEach(() => {
      __clearExpressionCache()
    })

    it("allows simple property access", () => {
      expect(__compileExpressionForTest("user.name")).toBeTypeOf("function")
    })

    it("allows arithmetic operators", () => {
      expect(__compileExpressionForTest("count + 1")).toBeTypeOf("function")
    })

    it("allows ternary expressions", () => {
      expect(__compileExpressionForTest("active ? 'Yes' : 'No'")).toBeTypeOf("function")
    })

    it("allows method calls on context values", () => {
      expect(__compileExpressionForTest("items.join(', ')")).toBeTypeOf("function")
    })

    it("allows object literals", () => {
      expect(__compileExpressionForTest("{ active: isActive, hidden: false }")).toBeTypeOf("function")
    })

    it("allows template literals", () => {
      expect(__compileExpressionForTest("`item-${id}`")).toBeTypeOf("function")
    })

    it("allows comparison operators", () => {
      expect(__compileExpressionForTest("count > 0")).toBeTypeOf("function")
    })

    it("allows JSON.stringify on context data", () => {
      expect(__compileExpressionForTest("JSON.stringify($data)")).toBeTypeOf("function")
    })

    it("allows $parent, $index, $key access", () => {
      expect(__compileExpressionForTest("$parent.source")).toBeTypeOf("function")
      expect(__compileExpressionForTest("$index")).toBeTypeOf("function")
      expect(__compileExpressionForTest("$key")).toBeTypeOf("function")
    })

    it("allows function calls from context", () => {
      expect(__compileExpressionForTest("onClick(id)")).toBeTypeOf("function")
    })

    it("blocks indirect-this IIFE reaching globals", () => {
      expect(__compileExpressionForTest("(function(){return this})().fetch('/x')")).toBeNull()
    })

    it("blocks bare this reaching globalThis", () => {
      expect(__compileExpressionForTest("this.fetch('/x')")).toBeNull()
    })

    it("blocks array and computed member access", () => {
      expect(__compileExpressionForTest("['win','dow'].join('')")).toBeNull()
      expect(__compileExpressionForTest("[].map.constructor")).toBeNull()
      expect(__compileExpressionForTest("$data['constructor']")).toBeNull()
    })

    it("blocks reserved prototype identifiers and reflection paths", () => {
      expect(__compileExpressionForTest("constructor")).toBeNull()
      expect(__compileExpressionForTest("__proto__")).toBeNull()
      expect(__compileExpressionForTest("prototype")).toBeNull()
      expect(__compileExpressionForTest("constructor.defineProperty(constructor.getPrototypeOf({}), 'polluted', { value: true })")).toBeNull()
      expect(__compileExpressionForTest("constructor.getOwnPropertyDescriptor(constructor.getPrototypeOf(constructor), 'constructor').value")).toBeNull()
    })

    it("rejects constructor access", () => {
      expect(__compileExpressionForTest("constructor.constructor('alert(1)')()")).toBeNull()
    })

    it("rejects __proto__ access", () => {
      expect(__compileExpressionForTest("__proto__.polluted = true")).toBeNull()
    })

    it("rejects prototype access", () => {
      expect(__compileExpressionForTest("Object.prototype.x = 1")).toBeNull()
    })

    it("rejects import() expressions", () => {
      expect(__compileExpressionForTest("import('evil-module')")).toBeNull()
    })

    it("allows safe string concatenation", () => {
      expect(__compileExpressionForTest("'doc' + 'umentation'")).toBeTypeOf("function")
      expect(__compileExpressionForTest("'Hello, ' + name")).toBeTypeOf("function")
    })

    for (const src of ["window.location", "document.cookie", "globalThis.fetch('/')", "self.location", "top.location", "Function('return this')()"]) {
      it(`renders ${src} inert (no global reach)`, () => {
        const fn = __compileExpressionForTest(src)
        expect(fn).toBeTypeOf("function")
        expect(fn?.({ $data: {} } as never)).toBeUndefined()
      })
    }

    it("does not leak Object.prototype members through bare identifiers", () => {
      for (const src of ["hasOwnProperty", "valueOf", "toString", "isPrototypeOf"]) {
        const fn = __compileExpressionForTest(src)
        expect(fn).toBeTypeOf("function")
        expect(fn?.({ $data: {} } as never)).toBeUndefined()
      }
    })

    it("treats string-reconstructed names as inert strings", () => {
      const fn = __compileExpressionForTest("'doc' + 'ument'")
      expect(fn?.({ $data: {} } as never)).toBe("document")
    })

    it("rejects member access on non-plain host receivers", () => {
      const win = { eval: () => "PWNED", fetch: () => "PWNED", cookie: "secret" }
      const eventTargetProto = {}
      const eventProto = Object.create(eventTargetProto) as Record<string, unknown>
      Object.defineProperty(eventProto, "view", { get: () => win })
      Object.defineProperty(eventProto, "target", {
        get: () => ({ ownerDocument: { defaultView: win, cookie: "secret" } }),
      })
      const hostLikeEvent = Object.create(eventProto) as Record<string, unknown>
      const ctx = { $data: {}, $event: hostLikeEvent } as never
      for (const src of ["$event.view", "$event.view.fetch", "$event.target.ownerDocument.defaultView", "$event.target.ownerDocument.cookie"]) {
        const fn = __compileExpressionForTest(src)
        expect(fn).toBeTypeOf("function")
        expect(fn?.(ctx)).toBeUndefined()
      }
    })

    it("preserves supported expression semantics", () => {
      const ctx = {
        $data: {},
        a: 2,
        b: "fallback",
        user: { tags: ["one", "two"] },
        isActive: true,
      } as never
      expect(__compileExpressionForTest("1 + 2 * 3 === 7")?.(ctx)).toBe(true)
      expect(__compileExpressionForTest("false && missingFn()")?.(ctx)).toBe(false)
      expect(__compileExpressionForTest("missing ?? b")?.(ctx)).toBe("fallback")
      expect(__compileExpressionForTest("user.tags.join('/')")?.(ctx)).toBe("one/two")
      expect(__compileExpressionForTest("{ active: isActive, hidden: false }")?.(ctx)).toEqual({
        active: true,
        hidden: false,
      })
      expect(__compileExpressionForTest("`x-${a}-${b}`")?.(ctx)).toBe("x-2-fallback")
    })

    it.each([
      ['"  hi  ".trim().toUpperCase()', "HI"],
      ['items.join(",")', "b,a"],
      ["items.slice(0, 1)", ["b"]],
      ["items.length", 2],
      ["items.toSorted()", ["a", "b"]],
      ["items.toReversed()", ["a", "b"]],
      ["name.length", 6],
      ['name.replace("a", "b")', "bbnana"],
      ['name.replaceAll("a", "b")', "bbnbnb"],
      ["(3.14159).toFixed(2)", "3.14"],
      ["flag.toString()", "true"],
      ["Math.max(2, 5)", 5],
    ])("allows safe allowlisted expression %s", (expression, expected) => {
      const items = ["b", "a"]
      const ctx = {
        $data: {},
        items,
        name: "banana",
        flag: true,
      } as never
      expect(__compileExpressionForTest(expression)?.(ctx)).toEqual(expected)
      expect(items).toEqual(["b", "a"])
    })

    it.each([
      'text.match("(a+)+$")',
      'text.matchAll("a")',
      'text.search("a")',
      'text.split(",")',
      "text.repeat(10)",
      'text.replace(re, "x")',
      'text.replaceAll(re, "x")',
      'items.push("x")',
      "items.pop()",
      "items.splice(0, 1)",
      "items.sort()",
      "items.reverse()",
      "user.toString()",
      'user.hasOwnProperty("name")',
      "flag.valueOf()",
      "fn.name",
      "fn.length",
    ])("blocks excluded primitive, array, function, and Object.prototype member %s", (expression) => {
      const items = ["b", "a"]
      const ctx = {
        $data: {},
        text: "a,b,c",
        re: /a/g,
        items,
        user: { name: "Alice" },
        flag: true,
        fn: (value: unknown) => value,
      } as never
      const compiled = __compileExpressionForTest(expression)
      expect(compiled).toBeTypeOf("function")
      expect(compiled?.(ctx)).toBeUndefined()
      expect(items).toEqual(["b", "a"])
    })

    it("does not false-positive on property names containing blocked words", () => {
      // "documentation" contains "document" but should be allowed
      expect(__compileExpressionForTest("documentation")).toBeTypeOf("function")
      // "selfie" contains "self" but should be allowed
      expect(__compileExpressionForTest("selfie")).toBeTypeOf("function")
      // "topLevel" contains "top" but should be allowed
      expect(__compileExpressionForTest("topLevel")).toBeTypeOf("function")
      // "constructorName" starts with "constructor" but is a longer word
      expect(__compileExpressionForTest("constructorName")).toBeTypeOf("function")
    })
  })

  describe("expression cache hardening", () => {
    beforeEach(() => {
      __setExpressionCacheLimit(1024)
      __clearExpressionCache()
    })

    it("reuses compiled expressions and keeps cache bounded", () => {
      expect(__getExpressionCacheSize()).toBe(0)
      expect(__compileExpressionForTest("value")).toBeTypeOf("function")
      expect(__getExpressionCacheSize()).toBe(1)

      expect(__compileExpressionForTest("value")).toBeTypeOf("function")
      expect(__getExpressionCacheSize()).toBe(1)
    })

    it("evicts least-recently-used expressions when limit is exceeded", () => {
      __setExpressionCacheLimit(2)
      __clearExpressionCache()

      __compileExpressionForTest("first")
      __compileExpressionForTest("second")
      expect(__getExpressionCacheKeys()).toEqual(["first", "second"])

      // Insert third — should evict "first" (oldest)
      __compileExpressionForTest("third")
      expect(__getExpressionCacheSize()).toBe(2)
      expect(__getExpressionCacheKeys()).toEqual(["second", "third"])

      // Re-access "second" — promotes it to most recent
      __compileExpressionForTest("second")
      expect(__getExpressionCacheKeys()).toEqual(["third", "second"])

      // Insert fourth — should evict "third" (now least recently used), not "second"
      __compileExpressionForTest("fourth")
      expect(__getExpressionCacheSize()).toBe(2)
      expect(__getExpressionCacheKeys()).toEqual(["second", "fourth"])
    })
  })

  describe("registerHtmxExtension", () => {
    it("does not auto-register on module import", async () => {
      vi.resetModules()
      const defineExtension = vi.fn()
      ;(window as unknown as Record<string, unknown>).htmx = { defineExtension, process: vi.fn() }

      await import("../../src/helpers/htmx")

      expect(defineExtension).not.toHaveBeenCalled()
    })

    it("registers extension and injects CSRF header", () => {
      const defineExtension = vi.fn()
      ;(window as unknown as Record<string, unknown>).__LITESTAR_CSRF__ = "csrf-token"
      ;(window as unknown as Record<string, unknown>).htmx = { defineExtension, process: vi.fn() }

      registerHtmxExtension()

      expect(defineExtension).toHaveBeenCalledTimes(1)
      const ext = defineExtension.mock.calls[0]?.[1] as { onEvent?: (name: string, evt: CustomEvent) => void }

      const detail = { headers: {} as Record<string, string> }
      const evt = new CustomEvent("htmx:configRequest", { detail })
      ext.onEvent?.("htmx:configRequest", evt)

      expect(detail.headers["X-CSRFToken"]).toBe("csrf-token")
    })

    it.each([
      { label: "same-origin relative path", detail: { path: "/api/items" } },
      { label: "same-origin relative url", detail: { url: "/api/items" } },
      { label: "missing path and url", detail: {} },
    ])("attaches CSRF header on htmx:configRequest for $label", ({ detail: targetDetail }) => {
      const defineExtension = vi.fn()
      ;(window as unknown as Record<string, unknown>).__LITESTAR_CSRF__ = "csrf-token"
      ;(window as unknown as Record<string, unknown>).htmx = { defineExtension, process: vi.fn() }

      registerHtmxExtension()

      const ext = defineExtension.mock.calls[0]?.[1] as { onEvent?: (name: string, evt: CustomEvent) => void }
      const headers: Record<string, string> = {}
      const evt = new CustomEvent("htmx:configRequest", { detail: { headers, ...targetDetail } })
      ext.onEvent?.("htmx:configRequest", evt)

      expect(headers["X-CSRFToken"]).toBe("csrf-token")
    })

    it.each([
      { label: "cross-origin path", detail: { path: "https://other.example/api" } },
      { label: "leading-space cross-origin path", detail: { path: " https://other.example/api" } },
      { label: "protocol-relative path", detail: { path: "//other.example/api" } },
      { label: "slash-backslash path", detail: { path: "/\\other.example/api" } },
      { label: "double-backslash path", detail: { path: "\\\\other.example/api" } },
      { label: "invalid URL path", detail: { path: "http://[::1" } },
      { label: "cross-origin url fallback", detail: { url: "https://other.example/api" } },
      { label: "empty path with cross-origin url fallback", detail: { path: "", url: "https://other.example/api" } },
    ])("omits CSRF header on htmx:configRequest for $label", ({ detail: targetDetail }) => {
      const defineExtension = vi.fn()
      ;(window as unknown as Record<string, unknown>).__LITESTAR_CSRF__ = "csrf-token"
      ;(window as unknown as Record<string, unknown>).htmx = { defineExtension, process: vi.fn() }

      registerHtmxExtension()

      const ext = defineExtension.mock.calls[0]?.[1] as { onEvent?: (name: string, evt: CustomEvent) => void }
      const headers: Record<string, string> = {}
      const evt = new CustomEvent("htmx:configRequest", { detail: { headers, ...targetDetail } })
      ext.onEvent?.("htmx:configRequest", evt)

      expect(headers["X-CSRFToken"]).toBeUndefined()
    })

    it("attaches CSRF header only to configured trustedOrigins on htmx:configRequest", () => {
      const defineExtension = vi.fn()
      ;(window as unknown as Record<string, unknown>).__LITESTAR_CSRF__ = "csrf-token"
      ;(window as unknown as Record<string, unknown>).htmx = { defineExtension, process: vi.fn() }

      const options: HtmxExtensionOptions = {
        trustedOrigins: ["https://api.example.com"],
      }
      registerHtmxExtension(options)

      const ext = defineExtension.mock.calls[0]?.[1] as { onEvent?: (name: string, evt: CustomEvent) => void }

      const trustedHeaders: Record<string, string> = {}
      ext.onEvent?.(
        "htmx:configRequest",
        new CustomEvent("htmx:configRequest", {
          detail: { headers: trustedHeaders, path: "https://api.example.com/items" },
        }),
      )
      expect(trustedHeaders["X-CSRFToken"]).toBe("csrf-token")

      const trustedHeadersInstance = new Headers()
      ext.onEvent?.(
        "htmx:configRequest",
        new CustomEvent("htmx:configRequest", {
          detail: { headers: trustedHeadersInstance, url: "https://api.example.com/items" },
        }),
      )
      expect(trustedHeadersInstance.get("X-CSRFToken")).toBe("csrf-token")

      const untrustedHeaders: Record<string, string> = {}
      ext.onEvent?.(
        "htmx:configRequest",
        new CustomEvent("htmx:configRequest", {
          detail: { headers: untrustedHeaders, path: "https://other.example/items" },
        }),
      )
      expect(untrustedHeaders["X-CSRFToken"]).toBeUndefined()

      const protocolRelativeHeaders: Record<string, string> = {}
      ext.onEvent?.(
        "htmx:configRequest",
        new CustomEvent("htmx:configRequest", {
          detail: { headers: protocolRelativeHeaders, path: "//api.example.com/items" },
        }),
      )
      expect(protocolRelativeHeaders["X-CSRFToken"]).toBeUndefined()
    })

    it("uses the configured header name when injected", () => {
      const defineExtension = vi.fn()
      ;(window as unknown as Record<string, unknown>).__LITESTAR_CSRF__ = "csrf-token"
      ;(window as unknown as Record<string, unknown>).__LITESTAR_CSRF_HEADER_NAME__ = "x-custom-header"
      ;(window as unknown as Record<string, unknown>).htmx = { defineExtension, process: vi.fn() }

      registerHtmxExtension()

      const ext = defineExtension.mock.calls[0]?.[1] as { onEvent?: (name: string, evt: CustomEvent) => void }
      const detail = { headers: {} as Record<string, string> }
      const evt = new CustomEvent("htmx:configRequest", { detail })
      ext.onEvent?.("htmx:configRequest", evt)

      expect(detail.headers["x-custom-header"]).toBe("csrf-token")
      expect(detail.headers["X-CSRFToken"]).toBeUndefined()

      delete (window as unknown as Record<string, unknown>).__LITESTAR_CSRF_HEADER_NAME__
    })

    it("does not throw if event detail is missing/invalid", () => {
      const defineExtension = vi.fn()
      ;(window as unknown as Record<string, unknown>).__LITESTAR_CSRF__ = "csrf-token"
      ;(window as unknown as Record<string, unknown>).htmx = { defineExtension, process: vi.fn() }

      registerHtmxExtension()

      const ext = defineExtension.mock.calls[0]?.[1] as { onEvent?: (name: string, evt: CustomEvent) => void }
      const evt = new CustomEvent("htmx:configRequest")
      expect(() => ext.onEvent?.("htmx:configRequest", evt)).not.toThrow()
    })

    it('handleSwap("json") parses JSON and runs swapJson', () => {
      const defineExtension = vi.fn()
      ;(window as unknown as Record<string, unknown>).htmx = { defineExtension, process: vi.fn() }

      registerHtmxExtension()

      const ext = defineExtension.mock.calls[0]?.[1] as {
        handleSwap?: (swapStyle: string, target: Element, fragment: DocumentFragment | Element) => Element[]
      }

      container.innerHTML = "<p>${title}</p>"
      const frag = document.createElement("div")
      frag.textContent = JSON.stringify({ title: "Hello from HTMX" })

      ext.handleSwap?.("json", container, frag)
      expect(container.innerHTML).toBe("<p>Hello from HTMX</p>")
    })

    it("does not render error messages as HTML (XSS prevention)", () => {
      const defineExtension = vi.fn()
      ;(window as unknown as Record<string, unknown>).htmx = { defineExtension, process: vi.fn() }

      registerHtmxExtension()

      const ext = defineExtension.mock.calls[0]?.[1] as {
        handleSwap?: (swapStyle: string, target: Element, fragment: DocumentFragment | Element) => Element[]
      }

      // Craft a fragment with invalid JSON containing an XSS payload
      const frag = document.createElement("div")
      frag.textContent = '<img src=x onerror="alert(1)">'

      ext.handleSwap?.("json", container, frag)

      // Error container must use safe DOM construction, not innerHTML
      const errorDiv = container.querySelector("div")
      expect(errorDiv).toBeTruthy()
      // The error text should be visible and HTML-escaped (no child elements from XSS payload)
      expect(errorDiv?.children.length).toBe(0)
      expect(errorDiv?.textContent).toContain("SyntaxError")
    })
  })

  describe("addDirective", () => {
    it("allows adding custom directives", () => {
      addDirective({
        match: (a) => a.name === "ls-uppercase",
        create: (_el, a) => {
          return (ctx, el) => {
            el.textContent = String((ctx as Record<string, unknown>)[a.value] ?? "").toUpperCase()
          }
        },
      })

      container.innerHTML = '<p ls-uppercase="name"></p>'
      swapJson(container, { name: "hello" })
      expect(container.querySelector("p")?.textContent).toBe("HELLO")
    })
  })

  describe("re-rendering", () => {
    it("updates content on subsequent swaps", () => {
      container.innerHTML = "<p>${count}</p>"

      swapJson(container, { count: 1 })
      expect(container.querySelector("p")?.textContent).toBe("1")

      swapJson(container, { count: 2 })
      expect(container.querySelector("p")?.textContent).toBe("2")
    })

    it("updates loop items on subsequent swaps", () => {
      container.innerHTML = `
        <ul>
          <template ls-for="item in $data">
            <li>\${item}</li>
          </template>
        </ul>
      `

      swapJson(container, ["a", "b"])
      expect(container.querySelectorAll("li").length).toBe(2)

      swapJson(container, ["x", "y", "z"])
      expect(container.querySelectorAll("li").length).toBe(3)
      expect(container.querySelectorAll("li")[0].textContent).toBe("x")
    })
  })
})

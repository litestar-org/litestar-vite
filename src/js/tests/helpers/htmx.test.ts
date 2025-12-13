/* biome-ignore-all lint/suspicious/noTemplateCurlyInString: Testing ${expr} template syntax intentionally */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { addDirective, registerHtmxExtension, swapJson } from "../../src/helpers/htmx"

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
    })

    describe("ls-html directive", () => {
      it("sets innerHTML from expression", () => {
        container.innerHTML = '<div ls-html="content"></div>'
        swapJson(container, { content: "<strong>Bold</strong>" })
        expect(container.querySelector("div")?.innerHTML).toBe("<strong>Bold</strong>")
      })
    })

    describe(":attr binding", () => {
      it("binds simple attribute", () => {
        container.innerHTML = '<a :href="url">Link</a>'
        swapJson(container, { url: "/path" })
        expect(container.querySelector("a")?.getAttribute("href")).toBe("/path")
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

      expect(detail.headers["X-CSRF-Token"]).toBe("csrf-token")
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

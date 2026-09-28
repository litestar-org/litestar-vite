import { createElement, useState } from "react"
import { renderToString } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { createSSRApp, h, ref } from "vue"
import { renderToString as renderVue } from "vue/server-renderer"
import { hydrateIslands } from "../src/fragments/client.js"
import { wrapIsland, getIslandClientScript } from "../src/fragments/island.js"
import { hydrateReact } from "../src/fragments/react.js"
import { createFragmentRenderer } from "../src/fragments/renderer.js"
import { hydrateVue } from "../src/fragments/vue.js"

function Counter({ initial }: { initial: number }) {
  const [count, setCount] = useState(initial)
  return createElement("button", { onClick: () => setCount(count + 1) }, String(count))
}
const VueCounter = {
  props: ["initial"],
  setup(props: { initial: number }) {
    const count = ref(props.initial)
    return () => h("button", { onClick: () => count.value++ }, String(count.value))
  },
}

describe("compiled fragment registry", () => {
  it("renders a real React component and rejects unregistered imports", async () => {
    const render = createFragmentRenderer({ "Counter.tsx": async () => ({ default: Counter }) }, { clientEntry: "/assets/islands.js" })
    const result = await render({ component: "Counter.tsx", props: { initial: 4 }, mode: "island" })
    expect(result.html).toContain("<button>4</button>")
    expect(result.html).toContain('src="/assets/islands.js"')
    await expect(render({ component: "../../outside.tsx" })).rejects.toThrow("Unknown fragment")
    expect(() => getIslandClientScript("javascript:alert(1)")).toThrow("URL")
    const noClient = createFragmentRenderer({ "Counter.tsx": async () => ({ default: Counter }) })
    await expect(noClient({ component: "Counter.tsx", mode: "island" })).rejects.toThrow("clientEntry")
    await expect(noClient({ component: "Counter.tsx", mode: "unknown" })).rejects.toThrow("mode")
  })

  it("hydrates real React and Vue SSR markup and handles clicks", async () => {
    const reactHtml = renderToString(createElement(Counter, { initial: 2 }))
    const vueHtml = await renderVue(createSSRApp(VueCounter, { initial: 3 }))
    document.body.innerHTML =
      wrapIsland(reactHtml, { component: "Counter.tsx", props: { initial: 2 }, islandId: "react-counter" }) +
      wrapIsland(vueHtml, { component: "Counter.vue", props: { initial: 3 }, islandId: "vue-counter" })
    hydrateIslands({
      "Counter.tsx": { load: async () => ({ default: Counter }), hydrate: hydrateReact },
      "Counter.vue": { load: async () => ({ default: VueCounter }), hydrate: hydrateVue },
    })
    await new Promise((resolve) => setTimeout(resolve, 30))
    document.querySelector<HTMLButtonElement>("#react-counter button")!.click()
    document.querySelector<HTMLButtonElement>("#vue-counter button")!.click()
    await new Promise((resolve) => setTimeout(resolve, 30))
    expect(document.querySelector("#react-counter button")!.textContent).toBe("3")
    expect(document.querySelector("#vue-counter button")!.textContent).toBe("4")
  })
})

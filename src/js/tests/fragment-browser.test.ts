// @vitest-environment node
import { execFile } from "node:child_process"
import { mkdtemp, rm, writeFile } from "node:fs/promises"
import { createServer } from "node:http"
import { createRequire } from "node:module"
import { tmpdir } from "node:os"
import path from "node:path"
import { promisify } from "node:util"
import { build } from "esbuild"
import { createElement } from "react"
import { renderToString } from "react-dom/server"
import { compile } from "svelte/compiler"
import { expect, it } from "vitest"
import { createSSRApp, h } from "vue"
import { renderToString as renderVue } from "vue/server-renderer"
import { wrapIsland } from "../src/fragments/island.js"

const exec = promisify(execFile)
const chrome = process.env.CHROME_BIN

it.skipIf(!chrome)(
  "hydrates built React, Vue, and Svelte islands in Chrome and handles clicks",
  async () => {
    const directory = await mkdtemp(path.join(tmpdir(), "litestar-islands-"))
    const root = process.cwd()
    const svelte =
      "<script>let { initial } = $props(); let count = $state(initial); $effect(() => () => { window.cleaned.push('svelte') });</script><button onclick={() => count++}>{count}</button>"
    const sveltePlugin = (generate: "client" | "server") => ({
      name: "test-svelte",
      setup(builder: any) {
        builder.onResolve({ filter: /^Counter\.svelte$/ }, () => ({ path: "Counter.svelte", namespace: "fixture" }))
        builder.onLoad({ filter: /.*/, namespace: "fixture" }, () => ({ contents: compile(svelte, { filename: "Counter.svelte", generate }).js.code, resolveDir: root }))
      },
    })
    let server: ReturnType<typeof createServer> | undefined
    try {
      const ssr = await build({
        stdin: {
          contents: 'import Counter from "Counter.svelte"; import {render} from "svelte/server"; export const html=render(Counter,{props:{initial:4}}).body;',
          resolveDir: root,
        },
        bundle: true,
        platform: "node",
        format: "cjs",
        write: false,
        plugins: [sveltePlugin("server")],
      })
      const serverModule = path.join(directory, "server.cjs")
      await writeFile(serverModule, ssr.outputFiles[0].text)
      const svelteHtml = createRequire(import.meta.url)(serverModule).html
      const html =
        wrapIsland(renderToString(createElement("button", null, "2")), { component: "react", props: { initial: 2 }, islandId: "react" }) +
        wrapIsland(await renderVue(createSSRApp({ render: () => h("button", "3") })), { component: "vue", props: { initial: 3 }, islandId: "vue" }) +
        wrapIsland(svelteHtml, { component: "svelte", props: { initial: 4 }, islandId: "svelte" })
      const browser = await build({
        stdin: {
          resolveDir: root,
          contents: `
      import {createElement,useState,useEffect} from 'react';
      import {h,ref,onUnmounted} from 'vue';
      import SvelteCounter from 'Counter.svelte';
      import {hydrateIslands} from './src/js/src/fragments/client.ts';
      import {hydrateReact} from './src/js/src/fragments/react.ts';
      import {hydrateVue} from './src/js/src/fragments/vue.ts';
      import {hydrateSvelte} from './src/js/src/fragments/svelte.ts';
      window.cleaned=[];
      function ReactCounter({initial}) { useEffect(()=>()=>{window.cleaned.push('react')},[]); const [count,setCount]=useState(initial); return createElement('button',{onClick:()=>setCount(count+1)},String(count)); }
      const VueCounter={props:['initial'],setup(props){onUnmounted(()=>window.cleaned.push('vue'));const count=ref(props.initial);return ()=>h('button',{onClick:()=>count.value++},String(count.value));}};
      let ready=0;
      document.addEventListener('litestar:island-ready',()=>{ready++;if(ready===3)setTimeout(()=>{
        document.querySelectorAll('button').forEach(button=>button.click());
        setTimeout(()=>{
          document.body.dataset.result=Array.from(document.querySelectorAll('button')).map(button=>button.textContent).join(',');
          const islands=Array.from(document.querySelectorAll('litestar-island'));
          islands.forEach(island=>island.remove());
          setTimeout(()=>{
            document.body.dataset.cleaned=window.cleaned.sort().join(',');
            islands.forEach(island=>document.body.append(island));
          },100);
        },100);
      },100);
        if(ready===6)setTimeout(()=>{
          document.querySelectorAll('button').forEach(button=>button.click());
          setTimeout(()=>{document.body.dataset.reconnected=Array.from(document.querySelectorAll('button')).map(button=>button.textContent).join(',');},100);
        },100);
      });
      hydrateIslands({react:{load:async()=>({default:ReactCounter}),hydrate:hydrateReact},vue:{load:async()=>({default:VueCounter}),hydrate:hydrateVue},svelte:{load:async()=>({default:SvelteCounter}),hydrate:hydrateSvelte}});
    `,
        },
        bundle: true,
        platform: "browser",
        format: "esm",
        write: false,
        plugins: [sveltePlugin("client")],
      })
      server = createServer((req, res) => {
        res.setHeader("Content-Type", req.url === "/client.js" ? "text/javascript" : "text/html")
        res.end(req.url === "/client.js" ? browser.outputFiles[0].text : `<!doctype html><body>${html}<script type="module" src="/client.js"></script></body>`)
      })
      await new Promise<void>((resolve) => server!.listen(0, "127.0.0.1", resolve))
      const port = (server.address() as { port: number }).port
      const { stdout } = await exec(
        chrome!,
        ["--headless", "--no-sandbox", "--disable-gpu", `--user-data-dir=${directory}/chrome`, "--virtual-time-budget=5000", "--dump-dom", `http://127.0.0.1:${port}`],
        { timeout: 20000, maxBuffer: 1000000 },
      )
      expect(stdout).toContain('data-result="3,4,5"')
      expect(stdout).toContain('data-cleaned="react,svelte,vue"')
      expect(stdout).toContain('data-reconnected="3,4,5"')
    } finally {
      await new Promise<void>((resolve) => (server ? server.close(() => resolve()) : resolve()))
      await rm(directory, { recursive: true, force: true })
    }
  },
  30000,
)

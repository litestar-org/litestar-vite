import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import { expect, it } from "vitest"
import { runTypeGeneration } from "../src/shared/typegen-core.js"

it("removes generated channel contracts when the last channel is removed", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "vite-channels-"))
  try {
    fs.writeFileSync(path.join(root, "asyncapi.json"), JSON.stringify({ asyncapi: "3.1.0", channels: {} }))
    fs.writeFileSync(path.join(root, "channels.ts"), "export type RemovedChannel = string")
    const result = await runTypeGeneration({
      projectRoot: root,
      output: ".",
      openapiPath: "openapi.json",
      pagePropsPath: "pages.json",
      routesPath: "routes.json",
      asyncapiPath: "asyncapi.json",
      channelsTsPath: "channels.ts",
      generateSdk: false,
      generateZod: false,
      generatePageProps: false,
      generateSchemas: false,
      generateChannels: true,
      sdkClientPlugin: "@hey-api/client-fetch",
    })
    expect(result.errors).toEqual([])
    expect(fs.existsSync(path.join(root, "channels.ts"))).toBe(false)
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})

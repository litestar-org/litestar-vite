import { execFileSync } from "node:child_process"
import fs from "node:fs"
import path from "node:path"

/**
 * Build the dev-server HTML artifact if it doesn't exist.
 * Tests in index.test.ts read this file at module level for placeholder assertions.
 */
export function setup() {
  const artifactPath = path.resolve(__dirname, "../../../dist/js/dev-server-index.html")
  if (!fs.existsSync(artifactPath)) {
    console.log("[global-setup] Building dev-server artifact...")
    execFileSync("npm", ["run", "build-dev-server"], {
      cwd: path.resolve(__dirname, "../../.."),
      stdio: "pipe",
    })
  }
}

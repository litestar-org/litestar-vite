import path from "node:path"
import { defineWorkspace } from "vitest/config"

export default defineWorkspace([path.resolve(__dirname, "vitest.config.ts")])

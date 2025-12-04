import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "./src/lib/generated/openapi.json",
  output: "./src/lib/generated",
  plugins: ["@hey-api/typescript", "@hey-api/schemas", "@hey-api/sdk", "@hey-api/client-fetch"],
})

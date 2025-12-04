import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "./generated/openapi.json",
  output: "./generated",
  plugins: ["@hey-api/typescript", "@hey-api/schemas", "@hey-api/sdk", "@hey-api/client-nuxt"],
})

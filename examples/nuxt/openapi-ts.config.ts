import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "./app/generated/openapi.json",
  output: "./app/generated/api",
  plugins: ["@hey-api/typescript", "@hey-api/schemas", "@hey-api/sdk", "@hey-api/client-nuxt"],
})

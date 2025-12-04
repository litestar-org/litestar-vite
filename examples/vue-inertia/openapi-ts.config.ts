import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "./resources/generated/openapi.json",
  output: "./resources/generated",
  plugins: ["@hey-api/typescript", "@hey-api/schemas", "@hey-api/sdk", "@hey-api/client-axios"],
})

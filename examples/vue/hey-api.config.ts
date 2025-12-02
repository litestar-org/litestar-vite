/// <reference types="vite/client" />

export default {
  input: "./src/generated/openapi.json",
  output: "./src/generated",
  plugins: [{ name: "@hey-api/client-axios" }],
  exportCore: true,
  exportServices: true,
  exportModels: true,
  exportSchemas: true,
  useOptions: true,
  useUnionTypes: true,
  name: "ApiClient",
  postfixServices: "Service",
  postfixModels: "",
  enumNames: true,
  operationId: true,
  format: true,
  types: {
    dates: "string",
    enums: "typescript",
    numbers: "string",
  },
  schemas: {
    export: true,
    type: "typescript",
  },
};

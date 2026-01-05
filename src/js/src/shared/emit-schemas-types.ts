/**
 * Generate ergonomic schema type helpers from hey-api output.
 *
 * This module generates `schemas.ts` which provides cleaner access to
 * request/response types using route names (e.g., FormInput<'api:login'>)
 * instead of verbose hey-api type names (e.g., AccountLoginData['body']).
 */
import fs from "node:fs"
import path from "node:path"

import { writeIfChanged } from "./write-if-changed.js"

function toImportPath(fromDir: string, targetFile: string): string {
  const relativePath = path.relative(fromDir, targetFile).replace(/\\/g, "/")
  const withoutExtension = relativePath.replace(/\.d\.ts$/, "").replace(/\.ts$/, "")
  if (withoutExtension.startsWith(".")) {
    return withoutExtension
  }
  return `./${withoutExtension}`
}

/**
 * Route metadata from routes.json
 */
interface RouteDefinition {
  uri: string
  methods: string[]
  method: string
  parameters?: string[]
  parameterTypes?: Record<string, string>
  queryParameters?: Record<string, string>
}

interface RoutesJson {
  routes: Record<string, RouteDefinition>
}

/**
 * Parsed hey-api type information
 */
interface HeyApiTypeInfo {
  typeName: string
  url: string | null
  hasBody: boolean
  hasPath: boolean
  hasQuery: boolean
}

/**
 * Operation mapping (route name -> hey-api type name)
 */
interface OperationMapping {
  routeName: string
  path: string
  method: string
  dataType: string | null
  responsesType: string | null
  errorsType: string | null
}

/**
 * Parse hey-api types.gen.ts to extract Data and Responses types with their URLs.
 *
 * Looks for patterns like:
 *   export type SomeOperationData = { body: {...}; url: '/api/path'; ... }
 *   export type SomeOperationResponses = { 200: {...}; ... }
 *   export type SomeOperationErrors = SomeOperationResponses[400 | 422]
 */
function parseHeyApiTypes(content: string): {
  dataTypes: Map<string, HeyApiTypeInfo>
  responsesTypes: Set<string>
  errorsTypes: Set<string>
  urlToDataType: Map<string, string>
} {
  const dataTypes = new Map<string, HeyApiTypeInfo>()
  const responsesTypes = new Set<string>()
  const errorsTypes = new Set<string>()
  const urlToDataType = new Map<string, string>()

  // Match Data types: export type XxxData = { ... url: '/path' ... }
  // Handle multiline type definitions
  const typeBlockRegex = /export\s+type\s+(\w+Data)\s*=\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}/gs
  for (const match of content.matchAll(typeBlockRegex)) {
    const typeName = match[1]
    const typeBody = match[2]

    // Extract URL from type body
    const urlMatch = typeBody.match(/url:\s*['"]([^'"]+)['"]/)
    const url = urlMatch ? urlMatch[1] : null

    // Check for body, path, query properties
    const hasBody = /\bbody\s*:/.test(typeBody) && !/\bbody\s*\?\s*:\s*never/.test(typeBody)
    const hasPath = /\bpath\s*:/.test(typeBody) && !/\bpath\s*\?\s*:\s*never/.test(typeBody)
    const hasQuery = /\bquery\s*:/.test(typeBody) && !/\bquery\s*\?\s*:\s*never/.test(typeBody)

    const info: HeyApiTypeInfo = { typeName, url, hasBody, hasPath, hasQuery }
    dataTypes.set(typeName, info)

    if (url) {
      urlToDataType.set(url, typeName)
    }
  }

  // Match Responses types: export type XxxResponses = { ... }
  const responsesRegex = /export\s+type\s+(\w+Responses)\s*=/g
  for (const match of content.matchAll(responsesRegex)) {
    responsesTypes.add(match[1])
  }

  // Match Errors types: export type XxxErrors = ...
  const errorsRegex = /export\s+type\s+(\w+Errors)\s*=/g
  for (const match of content.matchAll(errorsRegex)) {
    errorsTypes.add(match[1])
  }

  return { dataTypes, responsesTypes, errorsTypes, urlToDataType }
}

/**
 * Normalize a route path for matching.
 * Converts Litestar path params to OpenAPI format: {param:type} -> {param}
 */
function normalizePath(path: string): string {
  // Remove type constraints from path params: {id:int} -> {id}
  return path.replace(/\{([^:}]+):[^}]+\}/g, "{$1}")
}

/**
 * Create operation mappings by matching routes to hey-api types by URL.
 */
function createOperationMappings(
  routes: Record<string, RouteDefinition>,
  urlToDataType: Map<string, string>,
  responsesTypes: Set<string>,
  errorsTypes: Set<string>,
): OperationMapping[] {
  const mappings: OperationMapping[] = []

  for (const [routeName, route] of Object.entries(routes)) {
    const normalizedPath = normalizePath(route.uri)

    // Try to find matching Data type by URL
    const dataType = urlToDataType.get(normalizedPath) || null

    // Derive Responses and Errors type names from Data type
    let responsesType: string | null = null
    let errorsType: string | null = null

    if (dataType) {
      const baseName = dataType.replace(/Data$/, "")
      const candidateResponses = `${baseName}Responses`
      const candidateErrors = `${baseName}Errors`

      if (responsesTypes.has(candidateResponses)) {
        responsesType = candidateResponses
      }
      if (errorsTypes.has(candidateErrors)) {
        errorsType = candidateErrors
      }
    }

    mappings.push({
      routeName,
      path: route.uri,
      method: route.method,
      dataType,
      responsesType,
      errorsType,
    })
  }

  // Sort by route name for deterministic output
  return mappings.sort((a, b) => a.routeName.localeCompare(b.routeName))
}

/**
 * Generate schemas.ts content from operation mappings.
 */
function generateSchemasTs(mappings: OperationMapping[], apiTypesImportPath: string): string {
  // Filter to only operations with at least dataType or responsesType
  const validMappings = mappings.filter((m) => m.dataType || m.responsesType)

  if (validMappings.length === 0) {
    // No valid mappings - generate minimal file
    return `// AUTO-GENERATED by litestar-vite. Do not edit.
/* eslint-disable */

// Re-export all types from hey-api
export * from "${apiTypesImportPath}"

// No API operations found with matching types.
// Ensure routes have corresponding hey-api Data/Responses types.

/** No operations found */
export type OperationName = never

/** No operation data types */
export interface OperationDataTypes {}

/** No operation response types */
export interface OperationResponseTypes {}

/** Extract request body type - no operations available */
export type FormInput<T extends OperationName> = never

/** Extract response type - no operations available */
export type FormResponse<T extends OperationName, _Status extends number> = never

/** Extract success response - no operations available */
export type SuccessResponse<T extends OperationName> = never
`
  }

  // Collect unique Data and Responses types for import
  const dataTypeImports = [...new Set(validMappings.map((m) => m.dataType).filter(Boolean))] as string[]
  const responsesTypeImports = [...new Set(validMappings.map((m) => m.responsesType).filter(Boolean))] as string[]
  const errorsTypeImports = [...new Set(validMappings.map((m) => m.errorsType).filter(Boolean))] as string[]

  const allImports = [...dataTypeImports, ...responsesTypeImports, ...errorsTypeImports].sort()

  // Build OperationName union
  const operationNames = validMappings.map((m) => `  | '${m.routeName}'`).join("\n")

  // Build OperationDataTypes interface
  const dataTypeEntries = validMappings
    .filter((m) => m.dataType)
    .map((m) => `  '${m.routeName}': ${m.dataType}`)
    .join("\n")

  // Build OperationResponseTypes interface
  const responsesTypeEntries = validMappings
    .filter((m) => m.responsesType)
    .map((m) => `  '${m.routeName}': ${m.responsesType}`)
    .join("\n")

  // Build OperationErrorTypes interface
  const errorsTypeEntries = validMappings.map((m) => `  '${m.routeName}': ${m.errorsType || "never"}`).join("\n")

  return `// AUTO-GENERATED by litestar-vite. Do not edit.
/* eslint-disable */

// Re-export all types from hey-api for direct access
export * from "${apiTypesImportPath}"

// Import specific operation types for mapping
import type {
  ${allImports.join(",\n  ")}
} from "${apiTypesImportPath}"

// ============================================================================
// Operation Name Registry
// ============================================================================

/**
 * All available API operation names.
 * These match the route names from routes.ts for consistency.
 *
 * @example
 * import type { OperationName } from './generated/schemas'
 * const op: OperationName = 'api:login'
 */
export type OperationName =
${operationNames}

/**
 * Mapping of operation names to hey-api Data types.
 * Data types contain body, path, query, and url properties.
 */
export interface OperationDataTypes {
${dataTypeEntries}
}

/**
 * Mapping of operation names to hey-api Responses types.
 * Responses types map status codes to response shapes.
 */
export interface OperationResponseTypes {
${responsesTypeEntries}
}

/**
 * Mapping of operation names to hey-api Error types.
 * Error types represent non-2xx responses.
 */
export interface OperationErrorTypes {
${errorsTypeEntries}
}

// ============================================================================
// Ergonomic Type Helpers
// ============================================================================

/**
 * Extract request body type for an operation.
 * Use this for form data typing.
 *
 * @example
 * import { useForm } from '@inertiajs/react'
 * import type { FormInput } from './generated/schemas'
 *
 * const form = useForm<FormInput<'api:login'>>({
 *   username: '',
 *   password: '',
 * })
 */
export type FormInput<T extends OperationName> =
  T extends keyof OperationDataTypes
    ? OperationDataTypes[T] extends { body: infer B }
      ? B extends never ? never : B
      : never
    : never

/**
 * Extract path parameters type for an operation.
 *
 * @example
 * type BookParams = PathParams<'api:book_detail'>  // { book_id: number }
 */
export type PathParams<T extends OperationName> =
  T extends keyof OperationDataTypes
    ? OperationDataTypes[T] extends { path: infer P }
      ? P extends never ? never : P
      : never
    : never

/**
 * Extract query parameters type for an operation.
 *
 * @example
 * type SearchQuery = QueryParams<'api:books'>  // { q?: string; limit?: number }
 */
export type QueryParams<T extends OperationName> =
  T extends keyof OperationDataTypes
    ? OperationDataTypes[T] extends { query: infer Q }
      ? Q extends never ? never : Q
      : never
    : never

/**
 * Extract response type for a specific HTTP status code.
 *
 * @example
 * type LoginSuccess = FormResponse<'api:login', 201>  // { access_token: string; ... }
 * type LoginError = FormResponse<'api:login', 400>    // { detail: string; ... }
 */
export type FormResponse<T extends OperationName, Status extends number> =
  T extends keyof OperationResponseTypes
    ? Status extends keyof OperationResponseTypes[T]
      ? OperationResponseTypes[T][Status]
      : never
    : never

/**
 * Extract successful response type (200 or 201).
 * Convenience helper for the most common case.
 *
 * @example
 * type Books = SuccessResponse<'api:books'>  // Book[]
 * type NewBook = SuccessResponse<'api:book_create'>  // Book
 */
export type SuccessResponse<T extends OperationName> =
  T extends keyof OperationResponseTypes
    ? OperationResponseTypes[T] extends { 200: infer R }
      ? R
      : OperationResponseTypes[T] extends { 201: infer R }
        ? R
        : OperationResponseTypes[T] extends { 204: infer R }
          ? R
          : never
    : never

/**
 * Extract error response type.
 * Returns the union of all error response types for an operation.
 *
 * @example
 * type LoginErrors = ErrorResponse<'api:login'>  // { detail: string; ... }
 */
export type ErrorResponse<T extends OperationName> = OperationErrorTypes[T]

/**
 * Extract all possible response types as a union.
 *
 * @example
 * type AllResponses = AnyResponse<'api:login'>  // success | error union
 */
export type AnyResponse<T extends OperationName> =
  T extends keyof OperationResponseTypes
    ? OperationResponseTypes[T][keyof OperationResponseTypes[T]]
    : never

// ============================================================================
// Utility Types for Forms
// ============================================================================

/**
 * Make all form input properties optional.
 * Useful for initializing form state with empty values.
 *
 * @example
 * const initialData: PartialFormInput<'api:login'> = {}
 */
export type PartialFormInput<T extends OperationName> = Partial<FormInput<T>>

/**
 * Inertia-style form state with validation errors.
 *
 * @example
 * const formState: FormState<'api:login'> = {
 *   data: { username: '', password: '' },
 *   errors: {},
 *   processing: false,
 *   wasSuccessful: false,
 *   recentlySuccessful: false,
 * }
 */
export interface FormState<T extends OperationName> {
  data: FormInput<T>
  errors: Partial<Record<keyof FormInput<T>, string | string[]>>
  processing: boolean
  wasSuccessful: boolean
  recentlySuccessful: boolean
}

/**
 * Check if an operation has a request body.
 */
export type HasBody<T extends OperationName> = FormInput<T> extends never ? false : true

/**
 * Check if an operation has path parameters.
 */
export type HasPathParams<T extends OperationName> = PathParams<T> extends never ? false : true

/**
 * Check if an operation has query parameters.
 */
export type HasQueryParams<T extends OperationName> = QueryParams<T> extends never ? false : true
`
}

/**
 * Generate schemas.ts from routes.json and hey-api types.gen.ts.
 *
 * @param routesJsonPath - Path to routes.json
 * @param outputDir - Output directory (contains api/types.gen.ts)
 * @returns true if file was changed, false if unchanged
 */
export async function emitSchemasTypes(routesJsonPath: string, outputDir: string, schemasOutputPath?: string): Promise<boolean> {
  const outDir = path.resolve(process.cwd(), outputDir)
  const outFile = schemasOutputPath ? path.resolve(process.cwd(), schemasOutputPath) : path.join(outDir, "schemas.ts")
  const schemasDir = path.dirname(outFile)
  const apiTypesPath = path.join(outDir, "api", "types.gen.ts")
  const apiTypesImportPath = toImportPath(schemasDir, apiTypesPath)

  // Check if hey-api types exist
  if (!fs.existsSync(apiTypesPath)) {
    // eslint-disable-next-line no-console
    console.warn("litestar-vite: api/types.gen.ts not found, skipping schemas.ts generation")
    return false
  }

  // Check if routes.json exists
  if (!fs.existsSync(routesJsonPath)) {
    // eslint-disable-next-line no-console
    console.warn("litestar-vite: routes.json not found, skipping schemas.ts generation")
    return false
  }

  // Read and parse routes.json
  const routesContent = await fs.promises.readFile(routesJsonPath, "utf-8")
  const routesJson: RoutesJson = JSON.parse(routesContent)

  // Read and parse hey-api types
  const typesContent = await fs.promises.readFile(apiTypesPath, "utf-8")
  const { urlToDataType, responsesTypes, errorsTypes } = parseHeyApiTypes(typesContent)

  // Create operation mappings
  const mappings = createOperationMappings(routesJson.routes, urlToDataType, responsesTypes, errorsTypes)

  // Generate schemas.ts content
  const content = generateSchemasTs(mappings, apiTypesImportPath)

  // Write if changed
  await fs.promises.mkdir(schemasDir, { recursive: true })
  const result = await writeIfChanged(outFile, content, { encoding: "utf-8" })

  return result.changed
}

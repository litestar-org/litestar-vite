import fs from "node:fs"
import path from "node:path"

import { writeIfChanged } from "./write-if-changed.js"

interface InertiaPagePropsJson {
  pages: Record<
    string,
    {
      route: string
      propsType?: string
      tsType?: string
      customTypes?: string[]
      schemaRef?: string
      handler?: string
    }
  >
  sharedProps: Record<string, { type: string; optional?: boolean }>
  typeGenConfig: {
    includeDefaultAuth: boolean
    includeDefaultFlash: boolean
  }
  typeImportPaths?: Record<string, string>
  fallbackType?: "unknown" | "any"
  generatedAt: string
}

/**
 * Generate `page-props.ts` from `inertia-pages.json` metadata.
 *
 * @returns true if file was changed, false if unchanged
 */
export async function emitPagePropsTypes(pagesPath: string, outputDir: string): Promise<boolean> {
  const contents = await fs.promises.readFile(pagesPath, "utf-8")
  const json: InertiaPagePropsJson = JSON.parse(contents)

  const outDir = path.resolve(process.cwd(), outputDir)
  await fs.promises.mkdir(outDir, { recursive: true })
  const outFile = path.join(outDir, "page-props.ts")

  const { includeDefaultAuth, includeDefaultFlash } = json.typeGenConfig
  const typeImportPaths = json.typeImportPaths ?? {}
  const fallbackType = json.fallbackType ?? "unknown"
  const defaultFallback = fallbackType === "any" ? "Record<string, any>" : "Record<string, unknown>"

  // Build default types based on config
  let userTypes = ""
  let authTypes = ""
  let flashTypes = ""

  if (includeDefaultAuth) {
    userTypes = `/**
 * Default User interface - minimal baseline for common auth patterns.
 * Extend by adding properties to UserExtensions in page-props.user.ts
 */
export interface User extends UserExtensions {
  id: string
  email: string
  name?: string | null
}

`
    authTypes = `/**
 * Default AuthData interface - mirrors Laravel Jetstream pattern.
 * isAuthenticated + optional user is the universal pattern.
 */
export interface AuthData {
  isAuthenticated: boolean
  user?: User
}

`
  } else {
    // Empty interfaces for user extension
    userTypes = `/**
 * User interface - add properties to UserExtensions in page-props.user.ts
 */
export interface User extends UserExtensions {}

`
    authTypes = `/**
 * AuthData interface - define your auth structure here or in page-props.user.ts
 */
export interface AuthData {}

`
  }

  if (includeDefaultFlash) {
    flashTypes = `/**
 * Default FlashMessages interface - category to messages mapping.
 * Standard categories: success, error, info, warning.
 */
export interface FlashMessages {
  [category: string]: string[]
}

`
  } else {
    flashTypes = `/**
 * FlashMessages interface - define via module augmentation.
 * Default flash types are disabled.
 */
export interface FlashMessages {}

`
  }

  const defaultGeneratedSharedProps: InertiaPagePropsJson["sharedProps"] = {
    errors: { type: "Record<string, string[]>", optional: true },
    csrf_token: { type: "string", optional: true },
    ...(includeDefaultAuth || includeDefaultFlash
      ? {
          auth: { type: "AuthData", optional: true },
          flash: { type: "FlashMessages", optional: true },
        }
      : {}),
  }

  const generatedSharedProps = Object.keys(json.sharedProps ?? {}).length > 0 ? json.sharedProps : defaultGeneratedSharedProps

  const generatedSharedPropLines = Object.entries(generatedSharedProps)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, def]) => {
      const optional = def.optional ? "?" : ""
      const safeKey = /^[$A-Z_][0-9A-Z_$]*$/i.test(key) ? key : JSON.stringify(key)
      return `  ${safeKey}${optional}: ${def.type}`
    })

  // Collect custom types from metadata
  const allCustomTypes = new Set<string>()
  for (const data of Object.values(json.pages)) {
    if (data.tsType) {
      allCustomTypes.add(data.tsType)
    }
    for (const t of data.customTypes ?? []) {
      allCustomTypes.add(t)
    }
  }

  const builtinTypes = new Set<string>([
    "any",
    "unknown",
    "never",
    "void",
    "undefined",
    "null",
    "boolean",
    "string",
    "number",
    "bigint",
    "symbol",
    "object",
    "Record",
    "Partial",
    "Required",
    "Readonly",
    "Pick",
    "Omit",
    "Exclude",
    "Extract",
    "NonNullable",
    "Parameters",
    "ReturnType",
    "InstanceType",
    "Uppercase",
    "Lowercase",
    "Capitalize",
    "Uncapitalize",
    "Promise",
    "Array",
    "Map",
    "Set",
    "WeakMap",
    "WeakSet",
    "Date",
    "RegExp",
    "User",
    "AuthData",
    "FlashMessages",
  ])

  for (const def of Object.values(generatedSharedProps)) {
    for (const match of def.type.matchAll(/\b[A-Za-z_][A-Za-z0-9_]*\b/g)) {
      const name = match[0]
      if (!builtinTypes.has(name)) {
        allCustomTypes.add(name)
      }
    }
  }

  // Parse available exports from hey-api types
  const apiTypesPath = path.join(outDir, "api", "types.gen.ts")
  const availableApiTypes = new Set<string>()
  if (fs.existsSync(apiTypesPath)) {
    const content = await fs.promises.readFile(apiTypesPath, "utf-8")
    for (const match of content.matchAll(/export (?:type|interface|enum|class) (\w+)/g)) {
      if (match[1]) {
        availableApiTypes.add(match[1])
      }
    }
  }

  const apiImports = [...allCustomTypes].filter((t) => availableApiTypes.has(t)).sort()
  const remainingTypes = [...allCustomTypes].filter((t) => !availableApiTypes.has(t)).sort()

  const importsByPath = new Map<string, string[]>()
  const unresolvedTypes: string[] = []
  for (const t of remainingTypes) {
    const importPath = typeImportPaths[t]
    if (importPath) {
      const list = importsByPath.get(importPath) ?? []
      list.push(t)
      importsByPath.set(importPath, list)
    } else {
      unresolvedTypes.push(t)
    }
  }

  if (unresolvedTypes.length > 0) {
    // eslint-disable-next-line no-console
    console.warn(
      `litestar-vite: Unresolved Inertia props types: ${unresolvedTypes.join(", ")}.\n` +
        "  To fix:\n" +
        "  1. Add to OpenAPI by including in route return types\n" +
        "  2. Or configure TypeGenConfig.type_import_paths:\n" +
        `     types=TypeGenConfig(type_import_paths={"${unresolvedTypes[0]}": "@/types/custom"})`,
    )
  }

  let importStatement = ""
  if (apiImports.length > 0) {
    importStatement += `import type { ${apiImports.join(", ")} } from "./api/types.gen"\n`
  }
  const sortedImportPaths = [...importsByPath.keys()].sort()
  for (const p of sortedImportPaths) {
    const names = (importsByPath.get(p) ?? []).sort()
    if (names.length > 0) {
      importStatement += `import type { ${names.join(", ")} } from "${p}"\n`
    }
  }
  if (importStatement) {
    importStatement += "\n"
  }

  // Build page props entries
  const pageEntries: string[] = []
  for (const [component, data] of Object.entries(json.pages)) {
    const rawType = data.tsType || data.propsType || defaultFallback
    const propsType = rawType.includes("|") ? `(${rawType})` : rawType
    pageEntries.push(`  "${component}": ${propsType} & FullSharedProps`)
  }

  const body = `// AUTO-GENERATED by litestar-vite. Do not edit.
/* eslint-disable */

// Import user-defined type extensions (edit page-props.user.ts to customize)
import type { UserExtensions, SharedPropsExtensions } from "./page-props.user"

${importStatement}${userTypes}${authTypes}${flashTypes}/**
 * Generated shared props (always present).
 * Includes built-in props + static config props.
 */
export interface GeneratedSharedProps {
${generatedSharedPropLines.join("\n")}
}

/**
 * User-defined shared props for dynamic share() calls in guards/middleware.
 * Extend by adding properties to SharedPropsExtensions in page-props.user.ts
 */
export type SharedProps = SharedPropsExtensions

/** Full shared props = generated + user-defined.
 * Includes index signature for compatibility with Inertia's usePage<T>(). */
export type FullSharedProps = GeneratedSharedProps & SharedProps & { [key: string]: unknown }

/** Page props mapped by component name */
export interface PageProps {
${pageEntries.join("\n")}
}

/** Component name union type */
export type ComponentName = keyof PageProps

/** Type-safe props for a specific component */
export type InertiaPageProps<C extends ComponentName> = PageProps[C]

/** Get props type for a specific page component */
export type PagePropsFor<C extends ComponentName> = PageProps[C]
`

  const result = await writeIfChanged(outFile, body, { encoding: "utf-8" })

  // Generate user stub file if it doesn't exist (one-time generation)
  const userStubFile = path.join(outDir, "page-props.user.ts")
  if (!fs.existsSync(userStubFile)) {
    const userStub = `/**
 * User-defined type extensions for Inertia page props.
 * This file is generated ONCE and never overwritten - edit freely!
 *
 * Add properties to these interfaces to extend the generated types.
 * The main page-props.ts file imports and uses these extensions.
 */

/**
 * Extend the User interface with additional properties.
 *
 * @example
 * export interface UserExtensions {
 *   avatarUrl?: string | null
 *   roles: string[]
 *   teams: Team[]
 * }
 */
export interface UserExtensions {
  // Add your custom User properties here
}

/**
 * Extend SharedProps with session-based or dynamic properties.
 *
 * @example
 * export interface SharedPropsExtensions {
 *   locale?: string
 *   currentTeam?: {
 *     teamId: string
 *     teamName: string
 *   }
 * }
 */
export interface SharedPropsExtensions {
  // Add your custom shared props here
}

// Export custom types that can be used in page props
// export interface CurrentTeam {
//   teamId: string
//   teamName: string
// }
`
    await fs.promises.writeFile(userStubFile, userStub, "utf-8")
  }

  return result.changed
}

import fs from "node:fs"
import path from "node:path"

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
 */
export async function emitPagePropsTypes(pagesPath: string, outputDir: string): Promise<void> {
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
 * Users extend this via module augmentation with their full user model.
 *
 * @example
 * declare module 'litestar-vite-plugin/inertia' {
 *   interface User {
 *     avatarUrl?: string | null
 *     roles: Role[]
 *     teams: Team[]
 *   }
 * }
 */
export interface User {
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
 * User interface - define via module augmentation.
 * Default auth types are disabled.
 *
 * @example
 * declare module 'litestar-vite-plugin/inertia' {
 *   interface User {
 *     uuid: string
 *     username: string
 *   }
 * }
 */
export interface User {}

`
    authTypes = `/**
 * AuthData interface - define via module augmentation.
 * Default auth types are disabled.
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
    for (const match of content.matchAll(/export (?:type|interface|enum|class) (\\w+)/g)) {
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
    console.warn(`litestar-vite: unresolved Inertia props types: ${unresolvedTypes.join(", ")}. Add them to TypeGenConfig.type_import_paths or include them in OpenAPI.`)
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

${importStatement}${userTypes}${authTypes}${flashTypes}/**
 * Generated shared props (always present).
 * Includes built-in props + static config props.
 */
export interface GeneratedSharedProps {
${generatedSharedPropLines.join("\n")}
}

/**
 * User-defined shared props for dynamic share() calls in guards/middleware.
 * Extend this interface via module augmentation.
 *
 * @example
 * declare module 'litestar-vite-plugin/inertia' {
 *   interface User {
 *     avatarUrl?: string | null
 *     roles: Role[]
 *     teams: Team[]
 *   }
 *   interface SharedProps {
 *     locale?: string
 *     currentTeam?: CurrentTeam
 *   }
 * }
 */
export interface SharedProps {
}

/** Full shared props = generated + user-defined */
export type FullSharedProps = GeneratedSharedProps & SharedProps

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

// Re-export for module augmentation
declare module "litestar-vite-plugin/inertia" {
  export { User, AuthData, FlashMessages, SharedProps, GeneratedSharedProps, FullSharedProps, PageProps, ComponentName, InertiaPageProps, PagePropsFor }
}
`

  await fs.promises.writeFile(outFile, body, "utf-8")
}

import fs from "node:fs"
import path from "node:path"
import ts from "typescript"
import { describe, expect, it } from "vitest"

function listTypeScriptFiles(directory: string): string[] {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const entryPath = path.join(directory, entry.name)
    return entry.isDirectory() ? listTypeScriptFiles(entryPath) : entry.name.endsWith(".ts") ? [entryPath] : []
  })
}

function findImportSpecifiers(filePath: string, source: string): string[] {
  const specifiers: string[] = []
  const sourceFile = ts.createSourceFile(filePath, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS)

  function visit(node: ts.Node): void {
    if ((ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) && node.moduleSpecifier && ts.isStringLiteralLike(node.moduleSpecifier)) {
      specifiers.push(node.moduleSpecifier.text)
    } else if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword && node.arguments.length === 1 && ts.isStringLiteralLike(node.arguments[0])) {
      specifiers.push(node.arguments[0].text)
    }
    ts.forEachChild(node, visit)
  }

  visit(sourceFile)
  return specifiers
}

describe("package manifest", () => {
  it("declares @hey-api/openapi-ts as an optional peer dependency", () => {
    const packageJson = JSON.parse(fs.readFileSync(path.resolve(process.cwd(), "package.json"), "utf-8")) as {
      peerDependencies?: Record<string, string>
      peerDependenciesMeta?: Record<string, { optional?: boolean }>
    }

    expect(packageJson.peerDependencies?.["@hey-api/openapi-ts"]).toMatch(/^\^0\.98\./)
    expect(packageJson.peerDependenciesMeta?.["@hey-api/openapi-ts"]?.optional).toBe(true)
  })

  it("keeps browser helpers free of external imports", () => {
    const helpersDirectory = path.resolve(process.cwd(), "src/js/src/helpers")
    const externalImports = listTypeScriptFiles(helpersDirectory).flatMap((filePath) =>
      findImportSpecifiers(filePath, fs.readFileSync(filePath, "utf-8"))
        .filter((specifier) => !specifier.startsWith(".") && !specifier.startsWith("/") && specifier !== "litestar-vite-plugin" && !specifier.startsWith("litestar-vite-plugin/"))
        .map((specifier) => `${path.relative(helpersDirectory, filePath)}: ${specifier}`),
    )

    expect(externalImports).toEqual([])
  })
})

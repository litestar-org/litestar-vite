/**
 * CLI script to generate page-props.ts from inertia-pages.json.
 *
 * Usage: node emit-page-props-cli.js <pages-json-path> <output-dir>
 *
 * This allows the Python CLI to generate TypeScript types without
 * requiring a full Vite build.
 */
import { emitPagePropsTypes } from "./shared/emit-page-props-types.js"

async function main(): Promise<void> {
  const [pagesPath, outputDir] = process.argv.slice(2)

  if (!pagesPath || !outputDir) {
    console.error("Usage: emit-page-props-cli <pages-json-path> <output-dir>")
    process.exit(1)
  }

  try {
    await emitPagePropsTypes(pagesPath, outputDir)
    console.log(`Generated page-props.ts in ${outputDir}`)
  } catch (error) {
    console.error("Failed to generate page-props.ts:", error)
    process.exit(1)
  }
}

main()

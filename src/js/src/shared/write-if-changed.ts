import fs from "node:fs"
import path from "node:path"

export interface WriteResult {
  changed: boolean
  path: string
}

/**
 * Write file only if content differs from existing.
 * Uses direct Buffer comparison (more efficient than hashing for small files).
 *
 * @param filePath - Absolute path to file
 * @param content - Content to write
 * @param options - Write options
 * @returns WriteResult indicating whether file was changed
 */
export async function writeIfChanged(filePath: string, content: string, options?: { encoding?: BufferEncoding }): Promise<WriteResult> {
  const encoding = options?.encoding ?? "utf-8"
  const newBuffer = Buffer.from(content, encoding)

  try {
    const existing = await fs.promises.readFile(filePath)
    if (existing.equals(newBuffer)) {
      return { changed: false, path: filePath }
    }
  } catch {
    // File doesn't exist, will write
  }

  await fs.promises.mkdir(path.dirname(filePath), { recursive: true })
  await fs.promises.writeFile(filePath, newBuffer)
  return { changed: true, path: filePath }
}

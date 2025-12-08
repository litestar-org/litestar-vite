/**
 * Path formatting utilities for consistent logging output.
 *
 * @module
 */

import path from "node:path"

/**
 * Format an absolute path as relative to the project root for cleaner logging.
 *
 * @param absolutePath - The absolute path to format
 * @param root - The project root directory (defaults to process.cwd())
 * @returns The path relative to root, or the original path if already relative or on different drive
 */
export function formatPath(absolutePath: string, root?: string): string {
  if (!absolutePath) return absolutePath

  const projectRoot = root ?? process.cwd()

  // If already relative, return as-is
  if (!path.isAbsolute(absolutePath)) {
    return absolutePath
  }

  // Handle different drives on Windows
  try {
    const relativePath = path.relative(projectRoot, absolutePath)

    // On Windows, if paths are on different drives, path.relative returns the absolute path
    // Check if the result starts with '..' more than expected or is still absolute
    if (path.isAbsolute(relativePath)) {
      return absolutePath
    }

    return relativePath
  } catch {
    // If path.relative fails for any reason, return original
    return absolutePath
  }
}

/**
 * Format multiple paths, joining them with a separator.
 *
 * @param paths - Array of absolute paths to format
 * @param root - The project root directory (defaults to process.cwd())
 * @param separator - Separator between paths (defaults to ", ")
 * @returns Formatted paths joined by separator
 */
export function formatPaths(paths: string[], root?: string, separator = ", "): string {
  return paths.map((p) => formatPath(p, root)).join(separator)
}

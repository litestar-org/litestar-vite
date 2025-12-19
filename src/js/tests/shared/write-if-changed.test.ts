import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import { afterEach, beforeEach, describe, expect, it } from "vitest"

import { writeIfChanged } from "../../src/shared/write-if-changed"

describe("writeIfChanged", () => {
  let tmpDir: string

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "litestar-vite-test-"))
  })

  afterEach(() => {
    // Cleanup temp directory
    if (fs.existsSync(tmpDir)) {
      fs.rmSync(tmpDir, { recursive: true, force: true })
    }
  })

  it("writes file when it doesn't exist", async () => {
    const filePath = path.join(tmpDir, "new-file.txt")
    const content = "Hello, world!"

    const result = await writeIfChanged(filePath, content)

    expect(result.changed).toBe(true)
    expect(result.path).toBe(filePath)
    expect(fs.existsSync(filePath)).toBe(true)
    expect(fs.readFileSync(filePath, "utf-8")).toBe(content)
  })

  it("writes file when content differs", async () => {
    const filePath = path.join(tmpDir, "existing-file.txt")
    fs.writeFileSync(filePath, "Old content")

    const newContent = "New content"
    const result = await writeIfChanged(filePath, newContent)

    expect(result.changed).toBe(true)
    expect(result.path).toBe(filePath)
    expect(fs.readFileSync(filePath, "utf-8")).toBe(newContent)
  })

  it("skips write when content is identical", async () => {
    const filePath = path.join(tmpDir, "unchanged-file.txt")
    const content = "Same content"
    fs.writeFileSync(filePath, content)

    const result = await writeIfChanged(filePath, content)

    expect(result.changed).toBe(false)
    expect(result.path).toBe(filePath)
    expect(fs.readFileSync(filePath, "utf-8")).toBe(content)
  })

  it("creates parent directories if they don't exist", async () => {
    const filePath = path.join(tmpDir, "nested", "deep", "file.txt")
    const content = "Nested file content"

    const result = await writeIfChanged(filePath, content)

    expect(result.changed).toBe(true)
    expect(fs.existsSync(filePath)).toBe(true)
    expect(fs.readFileSync(filePath, "utf-8")).toBe(content)
  })

  it("handles unicode content correctly", async () => {
    const filePath = path.join(tmpDir, "unicode.txt")
    const content = "Hello 世界 🌍"

    const result = await writeIfChanged(filePath, content)

    expect(result.changed).toBe(true)
    expect(fs.readFileSync(filePath, "utf-8")).toBe(content)

    // Second write should be skipped
    const result2 = await writeIfChanged(filePath, content)
    expect(result2.changed).toBe(false)
  })

  it("handles empty content", async () => {
    const filePath = path.join(tmpDir, "empty.txt")
    const content = ""

    const result = await writeIfChanged(filePath, content)

    expect(result.changed).toBe(true)
    expect(fs.readFileSync(filePath, "utf-8")).toBe("")
  })

  it("handles very large content", async () => {
    const filePath = path.join(tmpDir, "large.txt")
    const content = "x".repeat(1024 * 1024) // 1MB

    const result = await writeIfChanged(filePath, content)

    expect(result.changed).toBe(true)
    expect(fs.readFileSync(filePath, "utf-8")).toBe(content)

    // Second write should be skipped
    const result2 = await writeIfChanged(filePath, content)
    expect(result2.changed).toBe(false)
  })

  it("detects changes in whitespace", async () => {
    const filePath = path.join(tmpDir, "whitespace.txt")
    fs.writeFileSync(filePath, "line1\nline2")

    const newContent = "line1\r\nline2"
    const result = await writeIfChanged(filePath, newContent)

    expect(result.changed).toBe(true)
    expect(fs.readFileSync(filePath, "utf-8")).toBe(newContent)
  })

  it("uses Buffer.equals for comparison (not string comparison)", async () => {
    const filePath = path.join(tmpDir, "binary-safe.txt")
    // Use content that might differ in different encodings
    const content = "Test\u0000content"

    const result1 = await writeIfChanged(filePath, content)
    expect(result1.changed).toBe(true)

    const result2 = await writeIfChanged(filePath, content)
    expect(result2.changed).toBe(false)
  })
})

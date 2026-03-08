import { route } from "$lib/generated/routes"
import { error } from "@sveltejs/kit"

import type { PageLoad } from "./$types"

type Book = {
  id: number
  title: string
  author: string
  year: number
  tags: string[]
}

type Summary = {
  app: string
  headline: string
  total_books: number
  featured: Book
}

export const load = (async ({ fetch }) => {
  const [summaryResponse, booksResponse] = await Promise.all([fetch(route("summary")), fetch(route("books"))])

  if (!summaryResponse.ok) {
    throw error(summaryResponse.status, "Failed to load library summary")
  }

  if (!booksResponse.ok) {
    throw error(booksResponse.status, "Failed to load library books")
  }

  const [summary, books] = await Promise.all([summaryResponse.json() as Promise<Summary>, booksResponse.json() as Promise<Book[]>])

  return {
    books,
    summary,
  }
}) satisfies PageLoad

import { createFileRoute } from "@tanstack/react-router"
import { useEffect, useState } from "react"

import { route } from "@/generated/routes"

type Book = {
  id: number
  title: string
  author: string
  year: number
  tags: string[]
}

export const Route = createFileRoute("/books")({
  component: BooksPage,
})

function BooksPage() {
  const [books, setBooks] = useState<Book[]>([])

  useEffect(() => {
    fetch(route("books"))
      .then((res) => res.json())
      .then(setBooks)
  }, [])

  if (books.length === 0) {
    return <div className="text-slate-600">Loading...</div>
  }

  return (
    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {books.map((book) => (
        <article key={book.id} className="rounded-xl border border-slate-200 bg-linear-to-b from-white to-slate-50 p-4 shadow-sm">
          <h3 className="font-semibold text-[#202235] text-lg">{book.title}</h3>
          <p className="mt-1 text-slate-600">
            {book.author} · {book.year}
          </p>
          <p className="mt-1 text-[#202235] text-sm">{book.tags.join(" · ")}</p>
        </article>
      ))}
    </section>
  )
}

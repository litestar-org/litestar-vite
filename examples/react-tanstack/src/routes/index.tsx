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

type Summary = {
  app: string
  headline: string
  total_books: number
  featured: Book
}

export const Route = createFileRoute("/")({
  component: IndexPage,
})

function IndexPage() {
  const [summary, setSummary] = useState<Summary | null>(null)

  useEffect(() => {
    fetch(route("summary"))
      .then((res) => res.json())
      .then(setSummary)
  }, [])

  if (!summary) {
    return <div className="text-slate-600">Loading...</div>
  }

  return (
    <section className="space-y-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-200/40">
      <h2 className="text-xl font-semibold text-[#202235]">{summary.headline}</h2>
      <p className="text-slate-600">{summary.total_books} books in the library. Featured:</p>
      <article className="rounded-xl border border-slate-200 bg-linear-to-b from-white to-slate-50 p-4">
        <h3 className="text-lg font-semibold text-[#202235]">{summary.featured.title}</h3>
        <p className="mt-1 text-slate-600">
          {summary.featured.author} · {summary.featured.year}
        </p>
        <p className="mt-1 text-sm text-[#202235]">{summary.featured.tags.join(" · ")}</p>
      </article>
    </section>
  )
}

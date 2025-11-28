import { useEffect, useMemo, useState } from "react"

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

function App() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [books, setBooks] = useState<Book[]>([])
  const [view, setView] = useState<"overview" | "books">("overview")

  useEffect(() => {
    async function loadData() {
      const [summaryRes, booksRes] = await Promise.all([
        fetch("/api/summary"),
        fetch("/api/books"),
      ])
      setSummary(await summaryRes.json())
      setBooks(await booksRes.json())
    }

    void loadData()
  }, [])

  const featured = useMemo(() => summary?.featured, [summary])

  return (
    <div className="max-w-5xl mx-auto px-4 py-10 space-y-6">
      <header className="space-y-2">
        <p className="uppercase tracking-[0.14em] text-sm font-semibold text-[#edb641]">Litestar · Vite</p>
        <h1 className="text-3xl font-semibold text-[#202235]">Library (React)</h1>
        <p className="text-slate-600 max-w-3xl">One backend, many frontends. Switch tabs to see how each framework consumes the same API.</p>
        <nav className="inline-flex gap-2 bg-slate-100 rounded-full p-1 shadow-sm" aria-label="Views">
          <button
            className={`px-4 py-2 rounded-full text-sm font-semibold transition ${view === "overview" ? "bg-white shadow text-[#202235]" : "text-slate-600"}`}
            onClick={() => setView("overview")}
          >
            Overview
          </button>
          <button
            className={`px-4 py-2 rounded-full text-sm font-semibold transition ${view === "books" ? "bg-white shadow text-[#202235]" : "text-slate-600"}`}
            onClick={() => setView("books")}
          >
            Books ({summary?.total_books ?? "–"})
          </button>
        </nav>
      </header>

      {view === "overview" && summary && featured && (
        <section className="bg-white border border-slate-200 rounded-2xl p-6 shadow-lg shadow-slate-200/40 space-y-2">
          <h2 className="text-xl font-semibold text-[#202235]">{summary.headline}</h2>
          <p className="text-slate-600">Featured book</p>
          <article className="border border-slate-200 rounded-xl p-4 bg-gradient-to-b from-white to-slate-50">
            <h3 className="text-lg font-semibold text-[#202235]">{featured.title}</h3>
            <p className="text-slate-600 mt-1">{featured.author} • {featured.year}</p>
            <p className="text-[#202235] text-sm mt-1">{featured.tags.join(" · ")}</p>
          </article>
        </section>
      )}

      {view === "books" && (
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {books.map((book) => (
            <article
              key={book.id}
              className="border border-slate-200 rounded-xl p-4 bg-gradient-to-b from-white to-slate-50 shadow-sm"
            >
              <h3 className="text-lg font-semibold text-[#202235]">{book.title}</h3>
              <p className="text-slate-600 mt-1">{book.author} • {book.year}</p>
              <p className="text-[#202235] text-sm mt-1">{book.tags.join(" · ")}</p>
            </article>
          ))}
        </section>
      )}
    </div>
  )
}

export default App

import { Head } from "@inertiajs/react"

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

type Props = {
  summary: Summary
  books: Book[]
}

export default function Books({ summary, books }: Props) {
  return (
    <>
      <Head title="Books" />
      <div className="app">
        <header className="hero">
          <p className="eyebrow">Litestar + Vite</p>
          <h1>Books (React + Inertia)</h1>
          <p className="lede">Server-provided props; same backend as every other example.</p>
        </header>

        <section className="panel">
          <h2>{summary.headline}</h2>
          <p className="muted">Total books: {summary.total_books}</p>
          <article className="card">
            <h3>{summary.featured.title}</h3>
            <p className="muted">{summary.featured.author} • {summary.featured.year}</p>
            <p className="chips">{summary.featured.tags.join(" · ")}</p>
          </article>
        </section>

        <section className="grid" aria-label="Books">
          {books.map((book) => (
            <article key={book.id} className="card">
              <h3>{book.title}</h3>
              <p className="muted">{book.author} • {book.year}</p>
              <p className="chips">{book.tags.join(" · ")}</p>
            </article>
          ))}
        </section>
      </div>
    </>
  )
}

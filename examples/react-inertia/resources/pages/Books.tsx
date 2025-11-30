import { Head, Link } from "@inertiajs/react"

interface Book {
  id: number
  title: string
  author: string
  year: number
  tags: string[]
}

interface Summary {
  app: string
  headline: string
  total_books: number
  featured: Book
}

interface Props {
  summary: Summary
  books: Book[]
}

export default function Books({ summary, books }: Props) {
  return (
    <>
      <Head title="Books" />
      <main className="mx-auto max-w-5xl space-y-6 px-4 py-10">
        <header className="space-y-2">
          <p className="font-semibold text-[#edb641] text-sm uppercase tracking-[0.14em]">
            Litestar · Vite
          </p>
          <h1 className="font-semibold text-3xl text-[#202235]">
            Library (React + Inertia)
          </h1>
          <p className="max-w-3xl text-slate-600">{summary.headline}</p>
          <nav className="flex gap-4">
            <Link
              href="/"
              className="rounded-full bg-slate-100 px-4 py-2 font-semibold text-slate-600 text-sm transition hover:bg-slate-200"
            >
              Home
            </Link>
            <span className="rounded-full bg-white px-4 py-2 font-semibold text-[#202235] text-sm shadow">
              Books ({summary.total_books})
            </span>
          </nav>
        </header>

        <section
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
          aria-label="Books"
        >
          {books.map((book) => (
            <article
              key={book.id}
              className="rounded-xl border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-4 shadow-sm"
            >
              <h3 className="font-semibold text-[#202235] text-lg">{book.title}</h3>
              <p className="mt-1 text-slate-600">
                {book.author} · {book.year}
              </p>
              <p className="mt-1 text-[#202235] text-sm">{book.tags.join(" · ")}</p>
            </article>
          ))}
        </section>

        <footer className="border-slate-200 border-t pt-8 text-slate-400 text-xs">
          <p>
            Data provided by Inertia.js props from the server. No client-side fetch required.
          </p>
        </footer>
      </main>
    </>
  )
}

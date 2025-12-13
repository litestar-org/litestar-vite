import { useEffect, useMemo, useState } from "react"
import { BrowserRouter, Link, Route, Routes, useLocation } from "react-router-dom"
import { route, routeDefinitions } from "@/generated/routes"

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

type RouteName = keyof typeof routeDefinitions
type RouteDefinition = (typeof routeDefinitions)[RouteName]
const routeEntries = Object.entries(routeDefinitions) as [RouteName, RouteDefinition][]

// Shared data hook
function useLibraryData() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [books, setBooks] = useState<Book[]>([])

  useEffect(() => {
    async function loadData() {
      // Using type-safe route() helper instead of hardcoded strings
      const [summaryRes, booksRes] = await Promise.all([fetch(route("summary")), fetch(route("books"))])
      setSummary(await summaryRes.json())
      setBooks(await booksRes.json())
    }

    void loadData()
  }, [])

  return { summary, books }
}

// Overview page component
function OverviewPage({ summary }: { summary: Summary | null }) {
  const featured = useMemo(() => summary?.featured, [summary])

  if (!summary || !featured) {
    return <div className="text-slate-600">Loading...</div>
  }

  return (
    <section className="space-y-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-200/40">
      <h2 className="font-semibold text-[#202235] text-xl">{summary.headline}</h2>
      <p className="text-slate-600">Featured book</p>
      <article className="rounded-xl border border-slate-200 bg-linear-to-b from-white to-slate-50 p-4">
        <h3 className="font-semibold text-[#202235] text-lg">{featured.title}</h3>
        <p className="mt-1 text-slate-600">
          {featured.author} • {featured.year}
        </p>
        <p className="mt-1 text-[#202235] text-sm">{featured.tags.join(" · ")}</p>
      </article>
    </section>
  )
}

// Books page component
function BooksPage({ books }: { books: Book[] }) {
  if (books.length === 0) {
    return <div className="text-slate-600">Loading...</div>
  }

  return (
    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {books.map((book) => (
        <article key={book.id} className="rounded-xl border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-4 shadow-sm">
          <h3 className="font-semibold text-[#202235] text-lg">{book.title}</h3>
          <p className="mt-1 text-slate-600">
            {book.author} • {book.year}
          </p>
          <p className="mt-1 text-[#202235] text-sm">{book.tags.join(" · ")}</p>
        </article>
      ))}
    </section>
  )
}

// Navigation component that uses React Router
function Navigation({ totalBooks }: { totalBooks: number | undefined }) {
  const location = useLocation()
  const isOverview = location.pathname === "/" || location.pathname === "/overview"
  const isBooks = location.pathname === "/books"

  return (
    <nav className="inline-flex gap-2 rounded-full bg-slate-100 p-1 shadow-sm" aria-label="Views">
      <Link to="/" className={`rounded-full px-4 py-2 font-semibold text-sm transition ${isOverview ? "bg-white text-[#202235] shadow" : "text-slate-600"}`}>
        Overview
      </Link>
      <Link to="/books" className={`rounded-full px-4 py-2 font-semibold text-sm transition ${isBooks ? "bg-white text-[#202235] shadow" : "text-slate-600"}`}>
        Books ({totalBooks ?? "–"})
      </Link>
    </nav>
  )
}

// Main app layout
function AppLayout() {
  const { summary, books } = useLibraryData()

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-10">
      <header className="space-y-2">
        <p className="font-semibold text-[#edb641] text-sm uppercase tracking-[0.14em]">Litestar · Vite</p>
        <h1 className="font-semibold text-3xl text-[#202235]">Example Library (React + Router)</h1>
        <p className="max-w-3xl text-slate-600">One backend, many frontends. Click the tabs to navigate - notice the URL changes!</p>
        <Navigation totalBooks={summary?.total_books} />
      </header>

      <Routes>
        <Route path="/" element={<OverviewPage summary={summary} />} />
        <Route path="/overview" element={<OverviewPage summary={summary} />} />
        <Route path="/books" element={<BooksPage books={books} />} />
      </Routes>

      {/* Show injected routes from server (if available) */}
      <footer className="border-slate-200 border-t pt-8 text-slate-400 text-xs">
        <details>
          <summary className="cursor-pointer">Type-safe route() helper usage</summary>
          <div className="mt-2 space-y-1 rounded bg-slate-100 p-2 font-mono">
            <div>route("summary") → {route("summary")}</div>
            <div>route("books") → {route("books")}</div>
            <div>
              {'route("book_detail", { book_id: 42 })'} → {route("book_detail", { book_id: 42 })}
            </div>
          </div>
        </details>
        <details className="mt-2">
          <summary className="cursor-pointer">Route definitions (from generated routes.ts)</summary>
          <div className="mt-2 grid grid-cols-1 gap-1 sm:grid-cols-2">
            {routeEntries.map(([name, def]) => (
              <span key={name} className="font-mono text-slate-600">
                {name} → {def.path}
              </span>
            ))}
          </div>
        </details>
      </footer>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  )
}

export default App

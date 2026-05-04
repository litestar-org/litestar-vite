import { useEffect, useState } from "react"
import { createBrowserRouter, Link, Outlet, RouterProvider, useLoaderData, useLocation } from "react-router-dom"

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

async function summaryLoader(): Promise<Summary> {
  const response = await fetch(route("summary"))
  return response.json() as Promise<Summary>
}

async function booksLoader(): Promise<Book[]> {
  const response = await fetch(route("books"))
  return response.json() as Promise<Book[]>
}

async function bookDetailLoader({ params }: { params: { book_id?: string } }): Promise<Book> {
  const id = Number(params.book_id ?? "0")
  const response = await fetch(route("book_detail", { book_id: id }))
  return response.json() as Promise<Book>
}

function Layout() {
  const location = useLocation()
  const isOverview = location.pathname === "/"
  const isBooks = location.pathname.startsWith("/books")
  const [totalBooks, setTotalBooks] = useState<number | null>(null)

  useEffect(() => {
    void summaryLoader().then((s) => setTotalBooks(s.total_books))
  }, [])

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-10">
      <header className="space-y-2">
        <p className="font-semibold text-[#edb641] text-sm uppercase tracking-[0.14em]">Litestar · Vite</p>
        <h1 className="font-semibold text-3xl text-[#202235]">Library (React + React Router 7)</h1>
        <p className="max-w-3xl text-slate-600">SPA mode with React Router 7's data router. Loaders fan out fetches alongside route changes.</p>
        <nav className="inline-flex gap-2 rounded-full bg-slate-100 p-1 shadow-sm" aria-label="Views">
          <Link to="/" className={`rounded-full px-4 py-2 font-semibold text-sm transition ${isOverview ? "bg-white text-[#202235] shadow" : "text-slate-600"}`}>
            Overview
          </Link>
          <Link to="/books" className={`rounded-full px-4 py-2 font-semibold text-sm transition ${isBooks ? "bg-white text-[#202235] shadow" : "text-slate-600"}`}>
            Books ({totalBooks ?? "–"})
          </Link>
        </nav>
      </header>
      <Outlet />
    </div>
  )
}

function OverviewPage() {
  const summary = useLoaderData() as Summary
  const featured = summary.featured

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
        <Link to={`/books/${featured.id}`} className="mt-3 inline-block rounded-full bg-[#202235] px-4 py-2 font-semibold text-sm text-white">
          View detail
        </Link>
      </article>
    </section>
  )
}

function BooksPage() {
  const books = useLoaderData() as Book[]

  return (
    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {books.map((book) => (
        <article key={book.id} className="rounded-xl border border-slate-200 bg-linear-to-b from-white to-slate-50 p-4 shadow-sm">
          <h3 className="font-semibold text-[#202235] text-lg">{book.title}</h3>
          <p className="mt-1 text-slate-600">
            {book.author} • {book.year}
          </p>
          <p className="mt-1 text-[#202235] text-sm">{book.tags.join(" · ")}</p>
          <Link to={`/books/${book.id}`} className="mt-3 inline-block rounded-full bg-slate-100 px-4 py-2 font-semibold text-slate-700 text-sm">
            Detail
          </Link>
        </article>
      ))}
    </section>
  )
}

function BookDetailPage() {
  const book = useLoaderData() as Book

  return (
    <section className="space-y-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-200/40">
      <h2 className="font-semibold text-[#202235] text-xl">{book.title}</h2>
      <p className="text-slate-600">
        {book.author} • {book.year}
      </p>
      <p className="text-[#202235] text-sm">{book.tags.join(" · ")}</p>
      <Link to="/books" className="mt-4 inline-block rounded-full bg-slate-100 px-4 py-2 font-semibold text-slate-700 text-sm">
        Back to books
      </Link>
    </section>
  )
}

const router = createBrowserRouter([
  {
    path: "/",
    Component: Layout,
    children: [
      { index: true, loader: summaryLoader, Component: OverviewPage },
      { path: "books", loader: booksLoader, Component: BooksPage },
      { path: "books/:book_id", loader: bookDetailLoader, Component: BookDetailPage },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}

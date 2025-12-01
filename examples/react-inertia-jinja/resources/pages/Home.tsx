import { Head, Link } from "@inertiajs/react"

interface Props {
  message?: string
}

export default function Home({ message }: Props) {
  return (
    <>
      <Head title="Home" />
      <main className="mx-auto max-w-5xl space-y-6 px-4 py-10">
        <header className="space-y-2">
          <p className="font-semibold text-[#edb641] text-sm uppercase tracking-[0.14em]">Litestar · Vite</p>
          <h1 className="font-semibold text-3xl text-[#202235]">Library (React + Inertia)</h1>
          <p className="max-w-3xl text-slate-600">Server-driven SPA with shared backend payloads. Inertia.js bridges server and client.</p>
        </header>

        <section className="space-y-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-200/40">
          {message && <p className="font-medium text-[#202235]">{message}</p>}
          <p className="text-slate-600">This page demonstrates Inertia.js with React. Server sends props, React renders.</p>
        </section>

        <nav className="flex gap-4">
          <Link href="/books" className="rounded-full bg-[#202235] px-6 py-2 font-semibold text-sm text-white transition hover:bg-[#2d3348]">
            View Books
          </Link>
        </nav>
      </main>
    </>
  )
}

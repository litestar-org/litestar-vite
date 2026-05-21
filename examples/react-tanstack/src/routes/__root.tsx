import { createRootRoute, Link, Outlet } from "@tanstack/react-router"

export const Route = createRootRoute({
  component: RootLayout,
})

function RootLayout() {
  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-10">
      <header className="space-y-2">
        <p className="text-sm font-semibold tracking-[0.14em] text-[#edb641] uppercase">Litestar · Vite</p>
        <h1 className="text-3xl font-semibold text-[#202235]">Example Library (React + TanStack Router)</h1>
        <p className="max-w-3xl text-slate-600">One backend, many frontends. File-based routing with TanStack Router.</p>
        <nav className="inline-flex gap-2 rounded-full bg-slate-100 p-1 shadow-sm" aria-label="Views">
          <Link to="/" className="rounded-full px-4 py-2 text-sm font-semibold text-slate-600 transition [&.active]:bg-white [&.active]:text-[#202235] [&.active]:shadow">
            Overview
          </Link>
          <Link to="/books" className="rounded-full px-4 py-2 text-sm font-semibold text-slate-600 transition [&.active]:bg-white [&.active]:text-[#202235] [&.active]:shadow">
            Books
          </Link>
        </nav>
      </header>

      <Outlet />
    </div>
  )
}

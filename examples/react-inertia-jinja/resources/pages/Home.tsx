import { Head, Link } from "@inertiajs/react"
import { route, routeDefinitions } from "@/generated/routes"

type RouteName = keyof typeof routeDefinitions
type RouteDefinition = (typeof routeDefinitions)[RouteName]
const routeEntries = Object.entries(routeDefinitions) as [RouteName, RouteDefinition][]

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
          {/* Using type-safe route() helper like Laravel's Ziggy */}
          <Link href={route("books_page")} className="rounded-full bg-[#202235] px-6 py-2 font-semibold text-sm text-white transition hover:bg-[#2d3348]">
            View Books
          </Link>
        </nav>

        <footer className="border-slate-200 border-t pt-8 text-slate-400 text-xs">
          <details>
            <summary className="cursor-pointer">Type-safe route() helper usage</summary>
            <div className="mt-2 space-y-1 rounded bg-slate-100 p-2 font-mono">
              <div>route("index") → {route("index")}</div>
              <div>route("books_page") → {route("books_page")}</div>
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
      </main>
    </>
  )
}

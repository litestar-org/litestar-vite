<script lang="ts">
import { onMount } from "svelte"
import routesJson from "$lib/generated/routes.json"

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

let summary = $state<Summary | null>(null)
let books = $state<Book[]>([])
let view = $state<"overview" | "books">("overview")

onMount(async () => {
  const [summaryRes, booksRes] = await Promise.all([fetch("/api/summary"), fetch("/api/books")])
  summary = await summaryRes.json()
  books = await booksRes.json()
})

const featured = $derived(summary?.featured)
const serverRoutes = routesJson.routes
</script>

<svelte:head>
  <title>Library (SvelteKit)</title>
</svelte:head>

<main class="mx-auto max-w-5xl space-y-6 px-4 py-10">
  <header class="space-y-2">
    <p class="font-semibold text-[#edb641] text-sm uppercase tracking-[0.14em]">Litestar · Vite</p>
    <h1 class="font-semibold text-3xl text-[#202235]">Library (SvelteKit)</h1>
    <p class="max-w-3xl text-slate-600">Same API, different frontend. SvelteKit with SSR proxy to Litestar.</p>
    <nav class="inline-flex gap-2 rounded-full bg-slate-100 p-1 shadow-sm" aria-label="Views">
      <button
        class="rounded-full px-4 py-2 font-semibold text-sm transition {view === 'overview' ? 'bg-white text-[#202235] shadow' : 'text-slate-600'}"
        onclick={() => (view = "overview")}
      >
        Overview
      </button>
      <button
        class="rounded-full px-4 py-2 font-semibold text-sm transition {view === 'books' ? 'bg-white text-[#202235] shadow' : 'text-slate-600'}"
        onclick={() => (view = "books")}
      >
        Books {summary ? `(${summary.total_books})` : ""}
      </button>
    </nav>
  </header>

  {#if view === "overview"}
    {#if featured}
      <section class="space-y-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-200/40">
        <h2 class="font-semibold text-[#202235] text-xl">{summary?.headline}</h2>
        <p class="text-slate-600">Featured book</p>
        <article class="rounded-xl border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-4">
          <h3 class="font-semibold text-[#202235] text-lg">{featured.title}</h3>
          <p class="mt-1 text-slate-600">{featured.author} • {featured.year}</p>
          <p class="mt-1 text-[#202235] text-sm">{featured.tags.join(" · ")}</p>
        </article>
      </section>
    {:else}
      <div class="text-slate-600">Loading...</div>
    {/if}
  {:else}
    {#if books.length > 0}
      <section class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {#each books as book (book.id)}
          <article class="rounded-xl border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-4 shadow-sm">
            <h3 class="font-semibold text-[#202235] text-lg">{book.title}</h3>
            <p class="mt-1 text-slate-600">{book.author} • {book.year}</p>
            <p class="mt-1 text-[#202235] text-sm">{book.tags.join(" · ")}</p>
          </article>
        {/each}
      </section>
    {:else}
      <div class="text-slate-600">Loading...</div>
    {/if}
  {/if}

  <footer class="border-slate-200 border-t pt-8 text-slate-400 text-xs">
    <details>
      <summary class="cursor-pointer">Server Routes (from generated routes.json)</summary>
      <div class="mt-2 grid grid-cols-1 gap-1 sm:grid-cols-2">
        {#each Object.entries(serverRoutes) as [name, route]}
          <span class="font-mono text-slate-600">
            {name} → {route.uri}
          </span>
        {/each}
      </div>
    </details>
  </footer>
</main>

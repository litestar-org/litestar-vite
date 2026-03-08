<script lang="ts">
import { route, routeDefinitions } from "$lib/generated/routes"
import type { PageProps } from "./$types"

let { data }: PageProps = $props()
let view = $state<"overview" | "books">("overview")
const featured = $derived(data.summary.featured)
const routeEntries = Object.entries(routeDefinitions)
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
        Books ({data.summary.total_books})
      </button>
    </nav>
  </header>

  {#if view === "overview"}
    <section class="space-y-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-200/40">
      <h2 class="font-semibold text-[#202235] text-xl">{data.summary.headline}</h2>
      <p class="text-slate-600">Featured book</p>
      <article class="rounded-xl border border-slate-200 bg-linear-to-b from-white to-slate-50 p-4">
        <h3 class="font-semibold text-[#202235] text-lg">{featured.title}</h3>
        <p class="mt-1 text-slate-600">{featured.author} • {featured.year}</p>
        <p class="mt-1 text-[#202235] text-sm">{featured.tags.join(" · ")}</p>
      </article>
    </section>
  {:else}
    <section class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {#each data.books as book (book.id)}
        <article class="rounded-xl border border-slate-200 bg-linear-to-b from-white to-slate-50 p-4 shadow-sm">
          <h3 class="font-semibold text-[#202235] text-lg">{book.title}</h3>
          <p class="mt-1 text-slate-600">{book.author} • {book.year}</p>
          <p class="mt-1 text-[#202235] text-sm">{book.tags.join(" · ")}</p>
        </article>
      {/each}
    </section>
  {/if}

  <footer class="border-slate-200 border-t pt-8 text-slate-400 text-xs">
    <details>
      <summary class="cursor-pointer">Type-safe route() helper usage</summary>
      <div class="mt-2 space-y-1 rounded bg-slate-100 p-2 font-mono">
        <div>route("summary") → {route("summary")}</div>
        <div>route("books") → {route("books")}</div>
        <div>route("book_detail", {'{'} book_id: 42 {'}'}) → {route("book_detail", { book_id: 42 })}</div>
      </div>
    </details>
    <details class="mt-2">
      <summary class="cursor-pointer">Route definitions (from generated routes.ts)</summary>
      <div class="mt-2 grid grid-cols-1 gap-1 sm:grid-cols-2">
        {#each routeEntries as [name, def]}
          <span class="font-mono text-slate-600">
            {name} → {def.path}
          </span>
        {/each}
      </div>
    </details>
  </footer>
</main>

<script lang="ts">
import { Link } from "@inertiajs/svelte"

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

let { summary, books }: { summary: Summary; books: Book[] } = $props()
</script>

<svelte:head>
  <title>Books - svelte-inertia-jinja</title>
</svelte:head>

<main class="mx-auto max-w-5xl space-y-6 px-4 py-10">
  <header class="space-y-2">
    <p class="text-sm font-semibold tracking-[0.14em] text-[#edb641] uppercase">Litestar · Vite</p>
    <h1 class="text-3xl font-semibold text-[#202235]">Library (Svelte 5 + Inertia + Jinja)</h1>
    <p class="max-w-3xl text-slate-600">{summary.headline}</p>
    <nav class="flex gap-4">
      <Link href="/" class="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-200">Home</Link>
      <span class="rounded-full bg-white px-4 py-2 text-sm font-semibold text-[#202235] shadow">
        Books ({summary.total_books})
      </span>
    </nav>
  </header>

  <section class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="Books">
    {#each books as book (book.id)}
      <article class="rounded-xl border border-slate-200 bg-linear-to-b from-white to-slate-50 p-4 shadow-sm">
        <h3 class="text-lg font-semibold text-[#202235]">{book.title}</h3>
        <p class="mt-1 text-slate-600">{book.author} · {book.year}</p>
        <p class="mt-1 text-sm text-[#202235]">{book.tags.join(" · ")}</p>
      </article>
    {/each}
  </section>
</main>

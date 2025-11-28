<script lang="ts">
import { onMount } from "svelte"

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

let summary: Summary | null = null
let books: Book[] = []
let view: "overview" | "books" = "overview"

onMount(async () => {
  const [summaryRes, booksRes] = await Promise.all([
    fetch("/api/summary"),
    fetch("/api/books"),
  ])
  summary = await summaryRes.json()
  books = await booksRes.json()
})

const featured = $derived(summary?.featured)
</script>

<main class="app">
  <header class="hero">
    <p class="eyebrow">Litestar + Vite</p>
    <h1>Library (Svelte)</h1>
    <p class="lede">Same API, different frontend.</p>
    <div class="tabs" role="tablist">
      <button class:active={view === "overview"} on:click={() => (view = "overview")}>Overview</button>
      <button class:active={view === "books"} on:click={() => (view = "books")}>Books {summary ? `(${summary.total_books})` : ""}</button>
    </div>
  </header>

  {#if view === "overview" && featured}
    <section class="panel">
      <h2>{summary?.headline}</h2>
      <p>Featured book</p>
      <article class="card">
        <h3>{featured.title}</h3>
        <p class="muted">{featured.author} • {featured.year}</p>
        <p class="chips">{featured.tags.join(" · ")}</p>
      </article>
    </section>
  {:else}
    <section class="grid" aria-label="Books">
      {#each books as book}
        <article class="card" aria-label={`Book ${book.title}`}>
          <h3>{book.title}</h3>
          <p class="muted">{book.author} • {book.year}</p>
          <p class="chips">{book.tags.join(" · ")}</p>
        </article>
      {/each}
    </section>
  {/if}
</main>

<style>
  :global(body) {
    margin: 0;
    font-family: "Inter", "SF Pro Text", system-ui, -apple-system, sans-serif;
    background: #f8fafc;
    color: #0f172a;
  }

  .app {
    max-width: 1100px;
    margin: 0 auto;
    padding: 2.5rem 1.5rem 3rem;
  }

  .hero {
    display: grid;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
  }

  .eyebrow {
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 600;
    color: #a855f7;
    font-size: 0.85rem;
  }

  .hero h1 {
    margin: 0;
    font-size: 2.1rem;
  }

  .lede {
    margin: 0;
    color: #475569;
  }

  .tabs {
    display: inline-flex;
    gap: 0.5rem;
    background: #e2e8f0;
    border-radius: 999px;
    padding: 0.25rem;
  }

  .tabs button {
    border: none;
    background: transparent;
    padding: 0.5rem 1.05rem;
    border-radius: 999px;
    font-weight: 600;
    color: #0f172a;
    cursor: pointer;
    transition: background 120ms ease, box-shadow 120ms ease;
  }

  .tabs button.active {
    background: #fff;
    box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
  }

  .panel {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 18px;
    padding: 1.5rem;
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05);
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 1rem;
  }

  .card {
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1rem 1.25rem;
    background: linear-gradient(180deg, #fff, #f8fafc);
  }

  .muted {
    color: #64748b;
    margin: 0.15rem 0 0.35rem;
  }

  .chips {
    font-size: 0.95rem;
    color: #0f172a;
  }
</style>

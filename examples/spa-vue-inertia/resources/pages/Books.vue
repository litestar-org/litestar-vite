<script setup lang="ts">
import { Head } from "@inertiajs/vue3"

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

defineProps<{
  summary: Summary
  books: Book[]
}>()
</script>

<template>
  <Head title="Books" />
  <div class="app">
    <header class="hero">
      <p class="eyebrow">Litestar + Vite</p>
      <h1>Books (Vue + Inertia)</h1>
      <p class="lede">Shared backend; this view uses server-provided props.</p>
    </header>

    <section class="panel">
      <h2>{{ summary.headline }}</h2>
      <p class="muted">Total books: {{ summary.total_books }}</p>
      <article class="card">
        <h3>{{ summary.featured.title }}</h3>
        <p class="muted">{{ summary.featured.author }} • {{ summary.featured.year }}</p>
        <p class="chips">{{ summary.featured.tags.join(" · ") }}</p>
      </article>
    </section>

    <section class="grid" aria-label="Books">
      <article v-for="book in books" :key="book.id" class="card">
        <h3>{{ book.title }}</h3>
        <p class="muted">{{ book.author }} • {{ book.year }}</p>
        <p class="chips">{{ book.tags.join(" · ") }}</p>
      </article>
    </section>
  </div>
</template>

<style scoped>
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
  color: #22c55e;
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

.panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  padding: 1.5rem;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05);
  margin-bottom: 1rem;
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

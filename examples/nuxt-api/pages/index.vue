<script setup lang="ts">
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

const { data: summary } = await useFetch<Summary>("/api/summary")
const { data: books } = await useFetch<Book[]>("/api/books")

const view = ref<"overview" | "books">("overview")
</script>

<template>
  <main class="max-w-5xl mx-auto px-4 py-10 space-y-6">
    <header class="space-y-2">
      <p class="uppercase tracking-[0.14em] text-sm font-semibold text-[#edb641]">Litestar · Vite</p>
      <h1 class="text-3xl font-semibold text-[#202235]">Library (Nuxt)</h1>
      <p class="text-slate-600">Nuxt frontend consuming the shared Litestar backend.</p>
      <div class="inline-flex gap-2 bg-slate-100 rounded-full p-1 shadow-sm" role="tablist">
        <button
          class="px-4 py-2 rounded-full text-sm font-semibold transition"
          :class="view === 'overview' ? 'bg-white shadow text-[#202235]' : 'text-slate-600'"
          @click="view = 'overview'"
          type="button"
        >Overview</button>
        <button
          class="px-4 py-2 rounded-full text-sm font-semibold transition"
          :class="view === 'books' ? 'bg-white shadow text-[#202235]' : 'text-slate-600'"
          @click="view = 'books'"
          type="button"
        >Books {{ summary?.total_books ? `(${summary.total_books})` : '' }}</button>
      </div>
    </header>

    <section v-if="view === 'overview' && summary" class="bg-white border border-slate-200 rounded-2xl p-6 shadow-lg shadow-slate-200/40 space-y-3">
      <h2 class="text-xl font-semibold text-[#202235]">{{ summary.headline }}</h2>
      <p class="text-slate-600">Featured book</p>
      <article class="border border-slate-200 rounded-xl p-4 bg-gradient-to-b from-white to-slate-50">
        <h3 class="text-lg font-semibold text-[#202235]">{{ summary.featured.title }}</h3>
        <p class="text-slate-600 mt-1">{{ summary.featured.author }} • {{ summary.featured.year }}</p>
        <p class="text-[#202235] text-sm mt-1">{{ summary.featured.tags.join(" · ") }}</p>
      </article>
    </section>

    <section v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" aria-label="Books">
      <article v-for="book in books" :key="book.id" class="border border-slate-200 rounded-xl p-4 bg-gradient-to-b from-white to-slate-50 shadow-sm">
        <h3 class="text-lg font-semibold text-[#202235]">{{ book.title }}</h3>
        <p class="text-slate-600 mt-1">{{ book.author }} • {{ book.year }}</p>
        <p class="text-[#202235] text-sm mt-1">{{ book.tags.join(" · ") }}</p>
      </article>
    </section>
  </main>
</template>

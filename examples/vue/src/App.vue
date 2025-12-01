<script setup lang="ts">
import { computed, onMounted, ref } from "vue"
import routesJson from "./generated/routes.json"

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

const summary = ref<Summary | null>(null)
const books = ref<Book[]>([])
const view = ref<"overview" | "books">("overview")

const featured = computed(() => summary.value?.featured)
const serverRoutes = routesJson.routes

onMounted(async () => {
  const [summaryRes, booksRes] = await Promise.all([fetch("/api/summary"), fetch("/api/books")])
  summary.value = await summaryRes.json()
  books.value = await booksRes.json()
})
</script>

<template>
  <main class="mx-auto max-w-5xl space-y-6 px-4 py-10">
    <header class="space-y-2">
      <p class="font-semibold text-[#edb641] text-sm uppercase tracking-[0.14em]">Litestar · Vite</p>
      <h1 class="font-semibold text-3xl text-[#202235]">Library (Vue)</h1>
      <p class="max-w-3xl text-slate-600">Same API, different frontend. Vue 3 with Composition API.</p>
      <nav class="inline-flex gap-2 rounded-full bg-slate-100 p-1 shadow-sm" aria-label="Views">
        <button
          class="rounded-full px-4 py-2 font-semibold text-sm transition"
          :class="view === 'overview' ? 'bg-white text-[#202235] shadow' : 'text-slate-600'"
          @click="view = 'overview'"
        >
          Overview
        </button>
        <button
          class="rounded-full px-4 py-2 font-semibold text-sm transition"
          :class="view === 'books' ? 'bg-white text-[#202235] shadow' : 'text-slate-600'"
          @click="view = 'books'"
        >
          Books {{ summary?.total_books ? `(${summary.total_books})` : "" }}
        </button>
      </nav>
    </header>

    <section v-if="view === 'overview'" class="space-y-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-200/40">
      <template v-if="featured">
        <h2 class="font-semibold text-[#202235] text-xl">{{ summary?.headline }}</h2>
        <p class="text-slate-600">Featured book</p>
        <article class="rounded-xl border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-4">
          <h3 class="font-semibold text-[#202235] text-lg">{{ featured.title }}</h3>
          <p class="mt-1 text-slate-600">{{ featured.author }} • {{ featured.year }}</p>
          <p class="mt-1 text-[#202235] text-sm">{{ featured.tags.join(" · ") }}</p>
        </article>
      </template>
      <div v-else class="text-slate-600">Loading...</div>
    </section>

    <section v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="Books">
      <template v-if="books.length > 0">
        <article v-for="book in books" :key="book.id" class="rounded-xl border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-4 shadow-sm">
          <h3 class="font-semibold text-[#202235] text-lg">{{ book.title }}</h3>
          <p class="mt-1 text-slate-600">{{ book.author }} • {{ book.year }}</p>
          <p class="mt-1 text-[#202235] text-sm">{{ book.tags.join(" · ") }}</p>
        </article>
      </template>
      <div v-else class="text-slate-600">Loading...</div>
    </section>

    <footer class="border-slate-200 border-t pt-8 text-slate-400 text-xs">
      <details>
        <summary class="cursor-pointer">Server Routes (from generated routes.json)</summary>
        <div class="mt-2 grid grid-cols-1 gap-1 sm:grid-cols-2">
          <span v-for="(route, name) in serverRoutes" :key="name" class="font-mono text-slate-600">
            {{ name }} → {{ route.uri }}
          </span>
        </div>
      </details>
    </footer>
  </main>
</template>

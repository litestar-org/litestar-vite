<script setup lang="ts">
import { Head, Link } from "@inertiajs/vue3"
import { route, routeDefinitions } from "@/generated/routes"

const routeEntries = Object.entries(routeDefinitions)

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
  <main class="mx-auto max-w-5xl space-y-6 px-4 py-10">
    <header class="space-y-2">
      <p class="font-semibold text-[#edb641] text-sm uppercase tracking-[0.14em]">Litestar · Vite</p>
      <h1 class="font-semibold text-3xl text-[#202235]">Library (Vue + Inertia)</h1>
      <p class="max-w-3xl text-slate-600">{{ summary.headline }}</p>
      <nav class="flex gap-4">
        <!-- Using type-safe route() helper like Laravel's Ziggy -->
        <Link :href="route('index')" class="rounded-full bg-slate-100 px-4 py-2 font-semibold text-slate-600 text-sm transition hover:bg-slate-200">
          Home
        </Link>
        <span class="rounded-full bg-white px-4 py-2 font-semibold text-[#202235] text-sm shadow">Books ({{ summary.total_books }})</span>
      </nav>
    </header>

    <section class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="Books">
      <article v-for="book in books" :key="book.id" class="rounded-xl border border-slate-200 bg-gradient-to-b from-white to-slate-50 p-4 shadow-sm">
        <h3 class="font-semibold text-[#202235] text-lg">{{ book.title }}</h3>
        <p class="mt-1 text-slate-600">{{ book.author }} • {{ book.year }}</p>
        <p class="mt-1 text-[#202235] text-sm">{{ book.tags.join(" · ") }}</p>
      </article>
    </section>

    <footer class="border-slate-200 border-t pt-8 text-slate-400 text-xs">
      <p>Data provided by Inertia.js props from the server. No client-side fetch required.</p>
      <details class="mt-2">
        <summary class="cursor-pointer">Type-safe route() helper usage</summary>
        <div class="mt-2 space-y-1 rounded bg-slate-100 p-2 font-mono">
          <div>route("index") → {{ route("index") }}</div>
          <div>route("books_page") → {{ route("books_page") }}</div>
        </div>
      </details>
      <details class="mt-2">
        <summary class="cursor-pointer">Route definitions (from generated routes.ts)</summary>
        <div class="mt-2 grid grid-cols-1 gap-1 sm:grid-cols-2">
          <span v-for="[name, def] in routeEntries" :key="name" class="font-mono text-slate-600">
            {{ name }} → {{ def.path }}
          </span>
        </div>
      </details>
    </footer>
  </main>
</template>

<script setup lang="ts">
import { Head, Link } from "@inertiajs/vue3"

type Book = { id: number; title: string; author: string; year: number; tags: string[] }
type Summary = { app: string; headline: string; total_books: number; featured: Book }

defineProps<{ summary: Summary; books: Book[] }>()
</script>

<template>
  <Head title="Books" />
  <main class="mx-auto max-w-5xl space-y-6 px-4 py-10">
    <header class="space-y-2">
      <p class="font-semibold text-[#edb641] text-sm uppercase tracking-[0.14em]">Litestar · Vite</p>
      <h1 class="font-semibold text-3xl text-[#202235]">Library (Vue + Inertia + SSR)</h1>
      <p class="max-w-3xl text-slate-600">{{ summary.headline }}</p>
      <nav class="flex gap-4">
        <Link href="/" class="rounded-full bg-slate-100 px-4 py-2 font-semibold text-slate-600 text-sm">Home</Link>
        <span class="rounded-full bg-white px-4 py-2 font-semibold text-[#202235] text-sm shadow">Books ({{ summary.total_books }})</span>
      </nav>
    </header>
    <section class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="Books">
      <article v-for="book in books" :key="book.id" class="rounded-xl border border-slate-200 bg-linear-to-b from-white to-slate-50 p-4 shadow-sm">
        <h3 class="font-semibold text-[#202235] text-lg">{{ book.title }}</h3>
        <p class="mt-1 text-slate-600">{{ book.author }} • {{ book.year }}</p>
        <p class="mt-1 text-[#202235] text-sm">{{ book.tags.join(" · ") }}</p>
      </article>
    </section>
  </main>
</template>

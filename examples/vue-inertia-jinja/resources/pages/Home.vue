<script setup lang="ts">
import { Head, Link } from "@inertiajs/vue3"
import { route, routeDefinitions } from "@/generated/routes"

const routeEntries = Object.entries(routeDefinitions)

defineProps<{
  message?: string
}>()
</script>

<template>
  <Head title="Home" />
  <main class="mx-auto max-w-5xl space-y-6 px-4 py-10">
    <header class="space-y-2">
      <p class="font-semibold text-[#edb641] text-sm uppercase tracking-[0.14em]">Litestar · Vite</p>
      <h1 class="font-semibold text-3xl text-[#202235]">Library (Vue + Inertia)</h1>
      <p class="max-w-3xl text-slate-600">Server-driven SPA with shared backend payloads. Inertia.js bridges server and client.</p>
      <p v-if="message" class="font-medium text-[#202235]">{{ message }}</p>
    </header>

    <section class="space-y-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-200/40">
      <p class="text-slate-600">This page demonstrates Inertia.js with Vue in template mode (Jinja2).</p>
    </section>

    <nav class="flex gap-4">
      <!-- Using type-safe route() helper like Laravel's Ziggy -->
      <Link :href="route('books_page')" class="rounded-full bg-[#202235] px-6 py-2 font-semibold text-white text-sm transition hover:bg-[#2d3348]">
        View Books
      </Link>
    </nav>

    <footer class="border-slate-200 border-t pt-8 text-slate-400 text-xs">
      <details>
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

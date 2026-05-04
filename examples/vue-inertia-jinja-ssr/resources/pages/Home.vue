<script setup lang="ts">
import { Head, Link } from "@inertiajs/vue3"

defineProps<{
  message?: string
}>()
</script>

<template>
  <Head title="Home" />
  <main class="mx-auto max-w-5xl space-y-6 px-4 py-10">
    <header class="space-y-2">
      <p class="font-semibold text-[#edb641] text-sm uppercase tracking-[0.14em]">Litestar · Vite</p>
      <h1 class="font-semibold text-3xl text-[#202235]">Library (Vue + Inertia + Jinja shell + SSR)</h1>
      <p class="max-w-3xl text-slate-600">
        The Jinja shell renders <code>&lt;div id="app"&gt;&lt;/div&gt;</code>; the Inertia SSR endpoint
        replaces that element's outer HTML with the Node-rendered Inertia tree.
      </p>
      <p v-if="message" class="font-medium text-[#202235]">{{ message }}</p>
    </header>
    <nav class="flex gap-4">
      <Link href="/books" class="rounded-full bg-[#202235] px-6 py-2 font-semibold text-sm text-white">View Books</Link>
    </nav>
  </main>
</template>

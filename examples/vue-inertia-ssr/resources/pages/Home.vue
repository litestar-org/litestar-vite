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
      <h1 class="font-semibold text-3xl text-[#202235]">Library (Vue + Inertia + SSR)</h1>
      <p class="max-w-3xl text-slate-600">
        The initial HTML below is rendered by a Node /render server at port 13714. View source to see the SSR-rendered markup.
      </p>
      <p v-if="message" class="font-medium text-[#202235]">{{ message }}</p>
    </header>

    <nav class="flex gap-4">
      <Link href="/books" class="rounded-full bg-[#202235] px-6 py-2 font-semibold text-sm text-white">
        View Books
      </Link>
    </nav>
  </main>
</template>

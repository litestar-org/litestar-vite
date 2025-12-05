<script setup lang="ts">
import { Head, Link } from "@inertiajs/vue3"
import { route } from "@/generated/routes"

defineProps<{
  message?: string
}>()
</script>

<template>
  <Head title="Home" />
  <div class="max-w-5xl mx-auto px-4 py-10 space-y-6">
    <div class="space-y-3">
      <p class="uppercase tracking-[0.14em] text-sm font-semibold text-[#edb641]">Litestar · Vite</p>
      <h1 class="text-3xl font-semibold text-[#202235]">Library (Vue + Inertia SPA)</h1>
      <p class="text-slate-600">Server-driven SPA example sharing the same backend.</p>
      <p v-if="message" class="text-[#202235] font-medium">{{ message }}</p>
    </div>

    <nav class="flex gap-4">
      <!-- Using type-safe route() helper like Laravel's Ziggy -->
      <Link :href="route('books_page')" class="rounded-full bg-[#202235] px-6 py-2 font-semibold text-white text-sm transition hover:bg-[#2d3348]">
        View Books
      </Link>
    </nav>
  </div>
</template>

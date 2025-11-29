<script setup lang="ts">
import { Head } from "@inertiajs/vue3"

defineProps<{
  message?: string
}>()
</script>

<template>
  <Head title="Home" />
  <div class="max-w-5xl mx-auto px-4 py-10 space-y-3">
    <p class="uppercase tracking-[0.14em] text-sm font-semibold text-[#edb641]">Litestar · Vite</p>
    <h1 class="text-3xl font-semibold text-[#202235]">Library (Vue + Inertia SPA)</h1>
    <p class="text-slate-600">Server-driven SPA example sharing the same backend.</p>
    <p v-if="message" class="text-[#202235] font-medium">{{ message }}</p>
  </div>
</template>

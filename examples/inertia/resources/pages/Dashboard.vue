<script setup>
import { Head, Link } from "@inertiajs/vue3"
defineProps({
  content: {
    message: String,
  },
})
</script>

<template>
  <Head title="Dashboard" />
  <h1 class="text-xl">Dashboard</h1>
  <p class="text-sm">{{ content.message }}</p>
  <Link href="/schema">Visit Schema</Link>
</template>

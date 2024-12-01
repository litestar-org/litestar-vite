<script setup>
import { Head, Link } from "@inertiajs/vue3"
defineProps({
  content: {
    message: String,
  },
})
</script>

<template>
  <Head title="Home" />
  <h1 class="text-xl pl-4 mb-5">Home Page</h1>
  <p class="text-sm">{{ content.message }}</p>
</template>

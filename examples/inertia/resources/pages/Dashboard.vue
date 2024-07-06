<script setup>
import { Head, Link } from "@inertiajs/vue3";
defineProps({
  content: {
    message: String,
  },
});
</script>

<template>
  <h1>Dashboard</h1>
  <p>{{ content.message }}</p>
  <Link href="/">Home</Link>
</template>

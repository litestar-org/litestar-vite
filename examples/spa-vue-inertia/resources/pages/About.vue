<script setup lang="ts">
import { Head, Link } from "@inertiajs/vue3"

defineProps<{
  title: string
  description: string
}>()
</script>

<template>
  <Head :title="title" />
  <div class="app">
    <h1>{{ title }}</h1>
    <p>{{ description }}</p>
    <nav>
      <Link href="/">Home</Link> |
      <Link href="/users">Users</Link>
    </nav>
  </div>
</template>

<style scoped>
.app {
  max-width: 1280px;
  margin: 0 auto;
  padding: 2rem;
  text-align: center;
}

nav {
  margin-top: 2rem;
}

nav a {
  color: #646cff;
  text-decoration: none;
  margin: 0 0.5rem;
}

nav a:hover {
  text-decoration: underline;
}
</style>

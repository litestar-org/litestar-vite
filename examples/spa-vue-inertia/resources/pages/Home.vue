<script setup lang="ts">
import { Head, Link } from "@inertiajs/vue3"

defineProps<{
  message?: string
}>()
</script>

<template>
  <Head title="Home" />
  <div class="app">
    <h1>Vue 3 + Inertia.js + Litestar</h1>
    <p v-if="message" class="message">{{ message }}</p>
    <nav>
      <Link href="/about">About</Link> |
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

.message {
  color: #646cff;
  font-weight: 500;
  margin: 1rem 0;
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

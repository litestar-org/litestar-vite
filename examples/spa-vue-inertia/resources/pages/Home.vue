<script setup lang="ts">
import { Head } from "@inertiajs/vue3"

defineProps<{
  message?: string
}>()
</script>

<template>
  <Head title="Home" />
  <div class="app">
    <h1>{{ project_name }}</h1>
    <p>Vue 3 + Inertia.js + Litestar</p>
    <p v-if="message" class="message">{{ message }}</p>
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
}
</style>

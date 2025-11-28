<script setup lang="ts">
import { Head, Link } from "@inertiajs/vue3"

interface User {
  id: number
  name: string
  email: string
}

defineProps<{
  users: User[]
}>()
</script>

<template>
  <Head title="Users" />
  <div class="app">
    <h1>Users</h1>
    <ul class="user-list">
      <li v-for="user in users" :key="user.id" class="user-item">
        <span class="user-name">{{ user.name }}</span>
        <span class="user-email">{{ user.email }}</span>
      </li>
    </ul>
    <nav>
      <Link href="/">Home</Link> |
      <Link href="/about">About</Link>
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

.user-list {
  list-style: none;
  padding: 0;
  max-width: 400px;
  margin: 2rem auto;
}

.user-item {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem;
  background: #f5f5f5;
  margin-bottom: 0.5rem;
  border-radius: 4px;
}

.user-name {
  font-weight: 500;
}

.user-email {
  color: #666;
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

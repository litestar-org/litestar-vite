<script setup lang="ts">
import { ref, onMounted } from "vue";
import Counter from "./components/Counter.vue";
import UserList from "./components/UserList.vue";

interface User {
  id: number;
  name: string;
  role: string;
}

const message = ref("");
const users = ref<User[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

onMounted(async () => {
  try {
    // Fetch greeting
    const helloRes = await fetch("/api/hello");
    const helloData = await helloRes.json();
    message.value = helloData.message;

    // Fetch users
    const usersRes = await fetch("/api/users");
    const usersData = await usersRes.json();
    users.value = usersData.users;
  } catch (e) {
    error.value = "Failed to load data from API";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="app">
    <header>
      <h1>Vue 3 + Litestar Vite</h1>
      <p v-if="message">{{ message }}</p>
    </header>

    <main>
      <section class="card">
        <h2>Interactive Counter</h2>
        <Counter />
      </section>

      <section class="card">
        <h2>Users from API</h2>
        <p v-if="loading">Loading...</p>
        <p v-else-if="error" class="error">{{ error }}</p>
        <UserList v-else :users="users" />
      </section>
    </main>

    <footer>
      <p>Built with Vue 3 + Litestar</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
interface User {
  id: number;
  name: string;
  role: string;
}

defineProps<{
  users: User[];
}>();
</script>

<template>
  <ul class="user-list">
    <li v-for="user in users" :key="user.id" class="user-item">
      <span class="user-name">{{ user.name }}</span>
      <span class="user-role" :class="user.role.toLowerCase()">
        {{ user.role }}
      </span>
    </li>
  </ul>
</template>

<style scoped>
.user-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.user-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: #f9f9f9;
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

.user-name {
  font-weight: 500;
}

.user-role {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.875rem;
}

.user-role.admin {
  background: #e74c3c;
  color: white;
}

.user-role.user {
  background: #3498db;
  color: white;
}
</style>

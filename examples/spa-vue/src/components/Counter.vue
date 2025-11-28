<script setup lang="ts">
import { ref } from "vue";

const count = ref(0);

function increment() {
  count.value++;
}

function decrement() {
  count.value--;
}
</script>

<template>
  <div class="counter">
    <button @click="decrement" :disabled="count <= 0">-</button>
    <span class="count">{{ count }}</span>
    <button @click="increment">+</button>
  </div>
</template>

<style scoped>
.counter {
  display: flex;
  align-items: center;
  gap: 1rem;
  justify-content: center;
}

button {
  padding: 0.5rem 1rem;
  font-size: 1.25rem;
  border: none;
  border-radius: 4px;
  background: #42b883;
  color: white;
  cursor: pointer;
  transition: background 0.2s;
}

button:hover:not(:disabled) {
  background: #3aa876;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.count {
  font-size: 2rem;
  font-weight: bold;
  min-width: 3rem;
  text-align: center;
}
</style>

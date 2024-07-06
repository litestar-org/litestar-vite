<script setup>
import { Link } from "@inertiajs/vue3";
</script>

<template>
  <main>
    <header>
      <Link class="text-sm m-2" href="/">Home</Link>
      <Link class="text-sm m-2" href="/dashboard/">Dashboard</Link>
    </header>
    <div>
      <slot />
    </div>
  </main>
</template>

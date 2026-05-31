<script lang="ts">
import { inertia, Link } from "@inertiajs/svelte"

let { message }: { message?: string } = $props()
</script>

<svelte:head>
  <title>Home - svelte-inertia</title>
</svelte:head>

<main class="mx-auto max-w-5xl space-y-6 px-4 py-10">
  <header class="space-y-2">
    <p class="text-sm font-semibold tracking-[0.14em] text-[#edb641] uppercase">Litestar · Vite</p>
    <h1 class="text-3xl font-semibold text-[#202235]">Library (Svelte 5 + Inertia)</h1>
    <p class="max-w-3xl text-slate-600">Server-driven SPA with shared backend payloads. Inertia.js bridges server and client.</p>
    {#if message}
      <p class="font-medium text-[#202235]">{message}</p>
    {/if}
  </header>

  <section class="space-y-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-200/40">
    <p class="text-slate-600">This page demonstrates Inertia.js with Svelte 5. Server sends props, Svelte renders.</p>
  </section>

  <nav class="flex gap-4">
    <Link href="/books" class="rounded-full bg-[#202235] px-6 py-2 text-sm font-semibold text-white transition hover:bg-[#2d3348]">View Books</Link>
    <a href="/legacy" use:inertia class="rounded-full bg-slate-100 px-6 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-200"> use:inertia action </a>
  </nav>
</main>

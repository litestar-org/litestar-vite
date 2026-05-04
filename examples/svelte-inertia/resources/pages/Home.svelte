<script lang="ts">
import { inertia, Link } from "@inertiajs/svelte"

let { message }: { message?: string } = $props()
</script>

<svelte:head>
  <title>Home - svelte-inertia</title>
</svelte:head>

<main class="mx-auto max-w-5xl space-y-6 px-4 py-10">
  <header class="space-y-2">
    <p class="font-semibold text-[#edb641] text-sm uppercase tracking-[0.14em]">Litestar · Vite</p>
    <h1 class="font-semibold text-3xl text-[#202235]">Library (Svelte 5 + Inertia)</h1>
    <p class="max-w-3xl text-slate-600">
      Server-driven SPA with shared backend payloads. Inertia.js bridges server and client.
    </p>
    {#if message}
      <p class="font-medium text-[#202235]">{message}</p>
    {/if}
  </header>

  <section class="space-y-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-200/40">
    <p class="text-slate-600">This page demonstrates Inertia.js with Svelte 5. Server sends props, Svelte renders.</p>
  </section>

  <nav class="flex gap-4">
    <Link
      href="/books"
      class="rounded-full bg-[#202235] px-6 py-2 font-semibold text-sm text-white transition hover:bg-[#2d3348]"
    >
      View Books
    </Link>
    <a
      href="/legacy"
      use:inertia
      class="rounded-full bg-slate-100 px-6 py-2 font-semibold text-slate-700 text-sm transition hover:bg-slate-200"
    >
      use:inertia action
    </a>
  </nav>
</main>

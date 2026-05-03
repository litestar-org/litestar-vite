<script lang="ts">
import { Link } from "@inertiajs/svelte"

let { message }: { message?: string } = $props()
</script>

<svelte:head>
  <title>Home - svelte-inertia-jinja</title>
</svelte:head>

<main class="mx-auto max-w-5xl space-y-6 px-4 py-10">
  <header class="space-y-2">
    <p class="font-semibold text-[#edb641] text-sm uppercase tracking-[0.14em]">Litestar · Vite</p>
    <h1 class="font-semibold text-3xl text-[#202235]">Library (Svelte 5 + Inertia + Jinja)</h1>
    <p class="max-w-3xl text-slate-600">
      Template mode: a Jinja2 shell wraps the Inertia bootstrap. Page payloads are injected into the
      <code>#app_page</code> script element by the server.
    </p>
    {#if message}
      <p class="font-medium text-[#202235]">{message}</p>
    {/if}
  </header>

  <nav class="flex gap-4">
    <Link
      href="/books"
      class="rounded-full bg-[#202235] px-6 py-2 font-semibold text-sm text-white transition hover:bg-[#2d3348]"
    >
      View Books
    </Link>
  </nav>
</main>

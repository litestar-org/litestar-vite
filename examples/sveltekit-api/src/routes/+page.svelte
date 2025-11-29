<script lang="ts">
let count = $state(0)

function increment() {
  count += 1
}
</script>

<svelte:head>
  <title>sveltekit-api</title>
</svelte:head>

<main class="app">
  <h1>sveltekit-api</h1>
  <p>SvelteKit + Litestar</p>
  <div class="card">
    <button onclick={increment}>
      count is {count}
    </button>
  </div>
</main>

<style>
  .app {
    max-width: 1280px;
    margin: 0 auto;
    padding: 2rem;
    text-align: center;
  }

  .card {
    padding: 2em;
  }
</style>

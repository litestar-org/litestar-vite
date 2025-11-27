import "./app.css"
import App from "./App.svelte"

const target = document.getElementById("app")
if (!target) throw new Error("Element with id 'app' not found")

const app = new App({
  target: target,
})

export default app

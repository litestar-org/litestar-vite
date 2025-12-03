import "htmx.org"
import Alpine from "alpinejs"
import "./styles.css"

// Import and register the Litestar HTMX extension
// This provides: typed routes (hx-route), CSRF injection, JSON templating, and flash messages
import { onFlash, registerHtmxExtension } from "litestar-vite-plugin/helpers"

registerHtmxExtension()

// Set up flash message handler
// Flash messages are triggered via HX-Trigger: {"showFlash": {"message": "...", "level": "..."}}
onFlash((message, level) => {
  // Dispatch to Alpine's flash store
  window.dispatchEvent(new CustomEvent("flash", { detail: { message, level } }))
})

// Initialize Alpine.js with flash store
Alpine.store("flash", {
  messages: [],
  add(message, level = "info") {
    const id = Date.now()
    this.messages.push({ id, message, level })
    // Auto-dismiss after 5 seconds
    setTimeout(() => this.remove(id), 5000)
  },
  remove(id) {
    this.messages = this.messages.filter((m) => m.id !== id)
  },
})

// Listen for flash events
window.addEventListener("flash", (e) => {
  Alpine.store("flash").add(e.detail.message, e.detail.level)
})

window.Alpine = Alpine
Alpine.start()

import "htmx.org"
import Alpine from "alpinejs"

// Initialize Alpine.js
window.Alpine = Alpine
Alpine.start()

// HTMX configuration
document.body.addEventListener("htmx:configRequest", (event) => {
  // Add CSRF token to all requests if available
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content")
  if (csrfToken) {
    event.detail.headers["X-CSRF-Token"] = csrfToken
  }
})

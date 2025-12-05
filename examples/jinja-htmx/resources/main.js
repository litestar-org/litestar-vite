import htmx from "htmx.org"
import "./styles.css"

// Register the Litestar HTMX extension so JSON templating and CSRF headers work automatically
import { registerHtmxExtension } from "litestar-vite-plugin/helpers"
// Import type-safe route helper for use in JSON templates
import { route } from "./generated/routes"

window.htmx = htmx
// Make route() available globally for JSON template expressions
// Templates can now use: route("book_detail", { book_id: book.id })
window.route = route
registerHtmxExtension()
htmx.process(document.body)

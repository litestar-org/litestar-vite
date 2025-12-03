import htmx from "htmx.org"
import "./styles.css"

// Register the Litestar HTMX extension so JSON templating and CSRF headers work automatically
import { registerHtmxExtension } from "litestar-vite-plugin/helpers"

window.htmx = htmx
registerHtmxExtension()
htmx.process(document.body)

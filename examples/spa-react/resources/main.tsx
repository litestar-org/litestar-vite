import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import App from "./App.tsx"
import "./App.css"

const root = document.getElementById("root")
if (!root) throw new Error("Element with id 'root' not found")

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

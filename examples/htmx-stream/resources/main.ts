import { createChannelsStream, defineStreamElement, type StreamGap } from "litestar-vite-plugin/helpers"
import "./styles.css"

defineStreamElement()

const channelOutput = document.querySelector<HTMLElement>("#channel-output")
const channelStream = createChannelsStream({
  basePath: "/channels",
  channel: "demo",
  onEvent: (event) => {
    if (channelOutput) channelOutput.textContent = JSON.stringify(event)
  },
})
channelStream.connect()

setTimeout(() => void fetch("/api/channels/publish", { method: "POST" }), 100)

for (const stream of document.querySelectorAll("litestar-stream")) {
  stream.addEventListener("litestar:stream-health", (event) => {
    const healthy = (event as CustomEvent<{ healthy: boolean }>).detail.healthy
    const output = stream.parentElement?.querySelector<HTMLElement>("[data-health]")
    if (output) output.textContent = healthy ? "connected" : "disconnected"
  })
  stream.addEventListener("litestar:stream-gap", (event) => {
    const gap = (event as CustomEvent<StreamGap>).detail
    const output = stream.parentElement?.querySelector<HTMLElement>("[data-gap]")
    if (output) output.textContent = `Missing ${gap.missing} event between ${gap.from} and ${gap.to}`
  })
}

window.addEventListener("pagehide", () => channelStream.dispose(), { once: true })

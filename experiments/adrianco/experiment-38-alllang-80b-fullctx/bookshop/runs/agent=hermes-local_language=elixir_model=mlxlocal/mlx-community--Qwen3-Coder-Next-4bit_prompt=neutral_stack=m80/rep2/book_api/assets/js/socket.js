// Phoenix LiveView JavaScript
import "phoenix_html"
import { Socket, LongPoll } from "phoenix"
import { LiveSocket } from "phoenix_live_view"

// Get CSRF token
const csrfToken = document.querySelector("meta[name='csrf-token']").getAttribute("content")

// Initialize LiveSocket
let liveSocket = new LiveSocket("/live", Socket, {
  longPollFallbackMs: 2500,
  params: { _csrf_token: csrfToken }
})

// Connect if there are any LiveViews on the page
liveSocket.connect()

// Expose liveSocket on window for web console debug logs and latency simulation:
// >> liveSocket.enableDebug()
// >> liveSocket.enableLatencySim(1000)
window.liveSocket = liveSocket

/**
 * Owner: Frontend
 *
 * Opens the WebSocket connection to the backend (/ws/live) and routes incoming
 * messages by their "type" field, matching docs/schema.md:
 *   - type: "detection" -> pass objects[] to whatever renders VideoPanel boxes
 *   - type: "alert"      -> pass to whatever renders AlertsFeed
 *
 * Usage from a component:
 *   connectSocket({
 *     onDetection: (msg) => ...,
 *     onAlert: (msg) => ...,
 *   });
 */

export function connectSocket({ onDetection, onAlert, url = "ws://localhost:8000/ws/live" }) {
  const socket = new WebSocket(url);

  socket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.type === "detection") {
      onDetection?.(message);
    } else if (message.type === "alert") {
      onAlert?.(message);
    }
  };

  socket.onopen = () => console.log("[socket] connected to IBVAP backend");
  socket.onclose = () => console.log("[socket] disconnected");
  socket.onerror = (err) => console.error("[socket] error", err);

  return socket;
}

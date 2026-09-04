/**
 * Owner: Frontend
 *
 * Opens and manages the WebSocket connection to the backend (/ws/live).
 * Features:
 *   - Auto-reconnect with exponential backoff
 *   - Heartbeat keep-alive pings
 *   - Type-safe message dispatching
 *   - Status change callbacks
 */

export function connectSocket({
  onDetection,
  onAlert,
  onStatusChange,
  url = (location.protocol === "https:" ? "wss://" : "ws://") + (location.host ? location.host + "/ws/live" : "localhost:8000/ws/live"),
}) {
  let socket = null;
  let isClosedIntentionally = false;
  let retryCount = 0;
  let pingTimer = null;
  const maxRetries = 15;

  function initSocket() {
    if (isClosedIntentionally) return;

    onStatusChange?.("connecting");
    try {
      socket = new WebSocket(url);
    } catch (e) {
      scheduleReconnect();
      return;
    }

    socket.onopen = () => {
      console.log("[socket] Connected to IBVAP live telemetry stream");
      retryCount = 0;
      onStatusChange?.("connected");

      // Periodic keep-alive ping
      clearInterval(pingTimer);
      pingTimer = setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send("ping");
        }
      }, 5000);
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === "detection") {
          onDetection?.(message);
        } else if (message.type === "alert") {
          onAlert?.(message);
        }
      } catch (err) {
        console.warn("[socket] Parse error:", err);
      }
    };

    socket.onclose = (event) => {
      clearInterval(pingTimer);
      if (!isClosedIntentionally) {
        onStatusChange?.("disconnected");
        scheduleReconnect();
      }
    };

    socket.onerror = (err) => {
      console.warn("[socket] Connection error:", err);
      socket?.close();
    };
  }

  function scheduleReconnect() {
    if (retryCount >= maxRetries || isClosedIntentionally) return;
    const delay = Math.min(1000 * Math.pow(1.5, retryCount), 10000);
    retryCount++;
    console.log(`[socket] Reconnecting in ${Math.round(delay)}ms (attempt ${retryCount})...`);
    setTimeout(initSocket, delay);
  }

  initSocket();

  return {
    close: () => {
      isClosedIntentionally = true;
      clearInterval(pingTimer);
      if (socket) {
        socket.close();
      }
    },
    send: (data) => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(typeof data === "string" ? data : JSON.stringify(data));
      }
    },
  };
}

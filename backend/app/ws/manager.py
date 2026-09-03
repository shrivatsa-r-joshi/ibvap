"""
Owner: Backend

WebSocket connection manager. Tracks connected frontend clients and broadcasts
every `detection` and `alert` message (docs/schema.md) to all of them as JSON.
"""
import json
import logging
from fastapi import WebSocket

logger = logging.getLogger("ibvap.ws")


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection and register it."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected client."""
        self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict) -> None:
        """Send a JSON message to every connected client.

        Silently removes any client whose connection has broken mid-send
        so one dead connection doesn't crash the broadcast loop.
        """
        dead: list[WebSocket] = []
        data = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception:
                logger.warning("Failed to send to a client, marking for removal")
                dead.append(connection)
        for connection in dead:
            self.active_connections.remove(connection)

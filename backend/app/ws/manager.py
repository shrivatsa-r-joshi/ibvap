"""
Owner: Backend

Tracks connected frontend WebSocket clients and broadcasts every `detection` and
`alert` message (docs/schema.md) to all of them as JSON in real time.
"""
from __future__ import annotations

import json
import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger("ibvap.ws")


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts and registers a new WebSocket client connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Client connected. Total active connections: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Removes a disconnected WebSocket client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("Client disconnected. Total active connections: %d", len(self.active_connections))

    async def broadcast(self, message: dict) -> None:
        """
        Broadcasts message to all active WebSocket connections.
        Matches `detection` or `alert` schema in docs/schema.md.
        """
        if not self.active_connections:
            return

        json_data = json.dumps(message)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json_data)
            except Exception as e:
                logger.warning("Error broadcasting to client: %s", e)
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

"""
Owner: Backend

Goal
----
Track connected frontend WebSocket clients and broadcast every `detection` and
`alert` message (docs/schema.md) to all of them as JSON, in real time.

Frontend side: frontend/src/api/socket.js connects to this endpoint and routes
incoming messages by their "type" field.
"""
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        # TODO: accept + register the connection
        raise NotImplementedError

    def disconnect(self, websocket: WebSocket) -> None:
        # TODO: remove the connection
        raise NotImplementedError

    async def broadcast(self, message: dict) -> None:
        """message matches the `detection` or `alert` schema in docs/schema.md"""
        # TODO: send JSON to every active connection
        raise NotImplementedError

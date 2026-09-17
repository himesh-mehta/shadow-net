"""
WebSocket Connection Manager for SHADOW-NET.
Manages live client connections mapped by session_id, streaming real-time
predictions, audio analysis frames, and high-priority security alerts.
"""

import logging
from typing import Dict, List, Any
from fastapi import WebSocket

logger = logging.getLogger("shadow_net.ws")


class ConnectionManager:
    """
    Tracks and broadcasts to active WebSocket connections per session.
    """

    def __init__(self):
        # Map of session_id -> list of active WebSocket connections
        self._connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept incoming connection and register under session_id."""
        await websocket.accept()
        if session_id not in self._connections:
            self._connections[session_id] = []
        self._connections[session_id].append(websocket)
        logger.info(f"WebSocket connected for session: {session_id} (total clients: {len(self._connections[session_id])})")

    def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove disconnected client cleanly."""
        if session_id in self._connections:
            if websocket in self._connections[session_id]:
                self._connections[session_id].remove(websocket)
            if not self._connections[session_id]:
                del self._connections[session_id]
        logger.info(f"WebSocket disconnected for session: {session_id}")

    async def send_to_client(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send JSON message directly to a single client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send to client: {e}")

    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """Broadcasts a JSON message to all active listeners for this session."""
        if session_id not in self._connections:
            return

        dead_connections = []
        for ws in self._connections[session_id]:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Error broadcasting to WebSocket in session {session_id}: {e}")
                dead_connections.append(ws)

        # Clean up stale connections
        for dead in dead_connections:
            self.disconnect(dead, session_id)


ws_manager = ConnectionManager()

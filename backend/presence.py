import asyncio
from datetime import datetime
from typing import Any

from fastapi import WebSocket


class PresenceManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._ws_to_user: dict[WebSocket, dict[str, Any]] = {}
        self._user_counts: dict[int, int] = {}
        self._active_users: dict[int, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self, websocket: WebSocket, user: dict[str, Any], connected_at: datetime
    ) -> None:
        async with self._lock:
            self._connections.add(websocket)
            self._ws_to_user[websocket] = user
            user_id = user["id"]
            self._user_counts[user_id] = self._user_counts.get(user_id, 0) + 1
            if user_id not in self._active_users:
                self._active_users[user_id] = {
                    "id": user_id,
                    "email": user["email"],
                    "name": user["name"],
                    "role": user["role"],
                    "connected_at": connected_at.isoformat(),
                    "connections": self._user_counts[user_id],
                }
            else:
                self._active_users[user_id]["connections"] = self._user_counts[user_id]
        await self.broadcast()

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            user = self._ws_to_user.pop(websocket, None)
            self._connections.discard(websocket)
            if not user:
                return
            user_id = user["id"]
            count = max(self._user_counts.get(user_id, 1) - 1, 0)
            if count <= 0:
                self._user_counts.pop(user_id, None)
                self._active_users.pop(user_id, None)
            else:
                self._user_counts[user_id] = count
                if user_id in self._active_users:
                    self._active_users[user_id]["connections"] = count
        await self.broadcast()

    async def broadcast(self) -> None:
        payload = {"type": "presence", "users": list(self._active_users.values())}
        stale: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            await self.disconnect(ws)

    async def snapshot(self) -> list[dict[str, Any]]:
        async with self._lock:
            return list(self._active_users.values())

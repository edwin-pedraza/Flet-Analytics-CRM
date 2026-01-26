import asyncio
import json
from typing import Awaitable, Callable, Optional

import httpx
import websockets

LogCallback = Callable[[str], Awaitable[None]]
PresenceCallback = Callable[[list[dict]], Awaitable[None]]
DisconnectCallback = Callable[[], Awaitable[None]]


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._token: Optional[str] = None
        self._client = httpx.AsyncClient(timeout=10)

    @property
    def token(self) -> Optional[str]:
        return self._token

    def set_token(self, token: str) -> None:
        self._token = token

    def _auth_headers(self) -> dict[str, str]:
        if not self._token:
            return {}
        return {"Authorization": f"Bearer {self._token}"}

    async def login(self, email: str, password: str) -> dict:
        response = await self._client.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password},
        )
        response.raise_for_status()
        data = response.json()
        self._token = data.get("access_token")
        return data

    async def create_user(self, email: str, name: str, password: str, role: str) -> dict:
        response = await self._client.post(
            f"{self.base_url}/users",
            json={"email": email, "name": name, "password": password, "role": role},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def list_my_clients(self) -> list[dict]:
        response = await self._client.get(
            f"{self.base_url}/clients/mine",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def list_clients(self) -> list[dict]:
        response = await self._client.get(
            f"{self.base_url}/clients",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def create_client(self, name: str, code: str, description: str | None) -> dict:
        response = await self._client.post(
            f"{self.base_url}/clients",
            json={"name": name, "code": code, "description": description},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def assign_user(self, client_id: int, user_email: str) -> dict:
        response = await self._client.post(
            f"{self.base_url}/clients/{client_id}/assign",
            json={"user_email": user_email},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def list_files(self, client_id: int) -> list[dict]:
        response = await self._client.get(
            f"{self.base_url}/clients/{client_id}/files",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def register_file(self, client_id: int, payload: dict) -> dict:
        response = await self._client.post(
            f"{self.base_url}/clients/{client_id}/files",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def preview_file(self, file_id: int, limit: int = 25) -> dict:
        response = await self._client.get(
            f"{self.base_url}/files/{file_id}/preview",
            params={"limit": limit},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def get_dashboard(self, client_id: int, force: bool = False) -> dict:
        response = await self._client.get(
            f"{self.base_url}/clients/{client_id}/dashboard",
            params={"force": "1"} if force else None,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def create_report(self, payload: dict) -> dict:
        response = await self._client.post(
            f"{self.base_url}/reports",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def list_reports(self, client_id: int | None = None) -> list[dict]:
        params = {"client_id": client_id} if client_id is not None else None
        response = await self._client.get(
            f"{self.base_url}/reports",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def run_report(self, report_id: int) -> dict:
        response = await self._client.get(
            f"{self.base_url}/reports/{report_id}/run",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()
    async def close(self) -> None:
        await self._client.aclose()


class PresenceClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        on_presence: PresenceCallback,
        on_log: LogCallback,
        on_disconnect: DisconnectCallback,
        auto_reconnect: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._on_presence = on_presence
        self._on_log = on_log
        self._on_disconnect = on_disconnect
        self._auto_reconnect = auto_reconnect
        self._stop = False
        self._task: Optional[asyncio.Task] = None

    def _ws_url(self) -> str:
        ws_base = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        return f"{ws_base}/ws/presence?token={self.token}"

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop = False
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop = True
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None

    async def _run(self) -> None:
        delay = 1.0
        while not self._stop:
            try:
                await self._on_log(f"Presence connecting to {self._ws_url()}...")
                async with websockets.connect(
                    self._ws_url(),
                    proxy=None,
                    ping_interval=20,
                    ping_timeout=20,
                ) as ws:
                    await self._on_log("Presence connected.")
                    async for message in ws:
                        try:
                            payload = json.loads(message)
                        except json.JSONDecodeError:
                            continue
                        if payload.get("type") == "presence":
                            await self._on_presence(payload.get("users", []))
                await self._on_log("Presence connection closed.")
            except Exception as exc:
                await self._on_log(f"Presence error: {exc}")
            finally:
                await self._on_disconnect()

            if not self._auto_reconnect or self._stop:
                return
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 10.0)

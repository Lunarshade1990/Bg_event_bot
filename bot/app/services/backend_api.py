import httpx

from backend.app.core.config import get_settings


class BackendAPIClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.backend_base_url.rstrip("/")
        self._headers = {"X-Internal-Token": settings.internal_api_token}

    async def get_health(self) -> dict:
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as client:
            response = await client.get("/health")
            response.raise_for_status()
            return response.json()

    async def sync_telegram_user(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        display_name: str | None = None,
        bgg_username: str | None = None,
    ) -> dict:
        payload = {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "display_name": display_name,
            "bgg_username": bgg_username,
        }
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as client:
            response = await client.post("/api/users/telegram", json=payload)
            response.raise_for_status()
            return response.json()

    async def get_user_by_telegram_id(self, telegram_id: int) -> dict | None:
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as client:
            response = await client.get(f"/api/users/by-telegram/{telegram_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    async def list_games(
        self,
        *,
        title: str | None = None,
        owner_id: int | None = None,
        players_count: int | None = None,
        max_play_time_minutes: int | None = None,
        game_type: str | None = None,
        has_campaign: bool | None = None,
        available_only: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        params = {
            "title": title,
            "owner_id": owner_id,
            "players_count": players_count,
            "max_play_time_minutes": max_play_time_minutes,
            "game_type": game_type,
            "has_campaign": has_campaign,
            "available_only": available_only,
            "limit": limit,
            "offset": offset,
        }
        filtered_params = {key: value for key, value in params.items() if value is not None}

        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as client:
            response = await client.get("/api/games", params=filtered_params)
            response.raise_for_status()
            return response.json()

    async def import_bgg_collection(
        self,
        *,
        telegram_id: int,
        bgg_username: str | None = None,
    ) -> dict:
        payload = {"telegram_id": telegram_id, "bgg_username": bgg_username}
        async with httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=120.0,
        ) as client:
            response = await client.post("/api/imports/bgg/collection", json=payload)
            response.raise_for_status()
            return response.json()

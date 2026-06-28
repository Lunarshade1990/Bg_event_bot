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
            timeout=httpx.Timeout(None),
        ) as client:
            response = await client.post("/api/imports/bgg/collection", json=payload)
            response.raise_for_status()
            return response.json()

    async def create_meetup(
        self,
        *,
        creator_user_id: int,
        scheduled_at: str,
        capacity_total: int,
        comment: str | None = None,
        telegram_chat_id: int | None = None,
        telegram_thread_id: int | None = None,
    ) -> dict:
        payload = {
            "creator_user_id": creator_user_id,
            "scheduled_at": scheduled_at,
            "capacity_total": capacity_total,
            "comment": comment,
            "telegram_chat_id": telegram_chat_id,
            "telegram_thread_id": telegram_thread_id,
        }
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as client:
            response = await client.post("/api/meetups", json=payload)
            response.raise_for_status()
            return response.json()

    async def list_meetups(
        self,
        *,
        telegram_chat_id: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        params = {"limit": limit, "offset": offset}
        if telegram_chat_id is not None:
            params["telegram_chat_id"] = telegram_chat_id
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as client:
            response = await client.get("/api/meetups", params=params)
            response.raise_for_status()
            return response.json()

    async def get_telegram_topic(self, telegram_chat_id: int) -> dict | None:
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as client:
            response = await client.get(f"/api/meetups/telegram-topics/{telegram_chat_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    async def upsert_telegram_topic(
        self,
        telegram_chat_id: int,
        *,
        telegram_thread_id: int,
        title: str | None = None,
    ) -> dict:
        payload = {
            "telegram_chat_id": telegram_chat_id,
            "telegram_thread_id": telegram_thread_id,
            "title": title,
        }
        filtered_payload = {key: value for key, value in payload.items() if value is not None}
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as client:
            response = await client.post("/api/meetups/telegram-topics", json=filtered_payload)
            response.raise_for_status()
            return response.json()

    async def register_telegram_chat_membership(
        self,
        *,
        user_id: int,
        telegram_chat_id: int,
        telegram_thread_id: int,
        title: str | None = None,
    ) -> dict:
        payload = {
            "user_id": user_id,
            "telegram_chat_id": telegram_chat_id,
            "telegram_thread_id": telegram_thread_id,
            "title": title,
        }
        filtered_payload = {key: value for key, value in payload.items() if value is not None}
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as client:
            response = await client.post(
                "/api/meetups/telegram-chat-memberships",
                json=filtered_payload,
            )
            response.raise_for_status()
            return response.json()

    async def list_telegram_chat_memberships(self, user_id: int) -> list[dict]:
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as client:
            response = await client.get(f"/api/meetups/telegram-chat-memberships/users/{user_id}")
            response.raise_for_status()
            return response.json()

    async def get_meetup(self, meetup_id: int) -> dict:
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as client:
            response = await client.get(f"/api/meetups/{meetup_id}")
            response.raise_for_status()
            return response.json()

    async def join_meetup(self, meetup_id: int, *, user_id: int) -> dict:
        payload = {"user_id": user_id}
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as client:
            response = await client.post(f"/api/meetups/{meetup_id}/join", json=payload)
            response.raise_for_status()
            return response.json()

    async def leave_meetup(self, meetup_id: int, *, user_id: int) -> dict:
        payload = {"user_id": user_id}
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as client:
            response = await client.post(f"/api/meetups/{meetup_id}/leave", json=payload)
            response.raise_for_status()
            return response.json()

    async def set_meetup_telegram_message_id(self, meetup_id: int, *, telegram_message_id: int) -> dict:
        payload = {"telegram_message_id": telegram_message_id}
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as client:
            response = await client.post(
                f"/api/meetups/{meetup_id}/telegram-message",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def delete_meetup(self, meetup_id: int, *, requesting_user_id: int) -> None:
        payload = {"requesting_user_id": requesting_user_id}
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers) as client:
            response = await client.request(
                "DELETE",
                f"/api/meetups/{meetup_id}",
                json=payload,
            )
            response.raise_for_status()

from fastapi.testclient import TestClient


def test_sync_telegram_user_creates_user(client: TestClient, api_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/users/telegram",
        headers=api_headers,
        json={
            "telegram_id": 123456,
            "username": "alice",
            "first_name": "Alice",
            "last_name": "Smith",
            "bgg_username": "alice_bgg",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["telegram_id"] == 123456
    assert body["display_name"] == "Alice Smith"
    assert body["bgg_username"] == "alice_bgg"


def test_get_user_by_telegram_id_returns_synced_user(
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/users/telegram",
        headers=api_headers,
        json={
            "telegram_id": 555001,
            "username": "boardgamer",
            "display_name": "Board Gamer",
        },
    )
    created_user = create_response.json()

    response = client.get(
        f"/api/users/by-telegram/{created_user['telegram_id']}",
        headers=api_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == created_user["id"]

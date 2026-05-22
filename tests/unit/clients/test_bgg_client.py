from backend.app.clients.bgg import get_bgg_client


def test_bgg_client_factory_returns_client() -> None:
    client = get_bgg_client()

    assert client is not None

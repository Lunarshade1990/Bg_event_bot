from time import sleep

from boardgamegeek import BGGClient
from boardgamegeek.api import BGGRestrictCollectionTo
from boardgamegeek.exceptions import BGGApiRetryError

from backend.app.core.config import get_settings


def get_bgg_client() -> BGGClient:
    settings = get_settings()
    return BGGClient(settings.bgg_access_token)


def fetch_owned_collection(
    client: BGGClient,
    *,
    bgg_username: str,
    subtype: str,
    retries: int = 3,
    retry_delay_seconds: float = 2.0,
):
    for attempt in range(1, retries + 1):
        try:
            return client.collection(user_name=bgg_username, subtype=subtype)
        except BGGApiRetryError:
            if attempt == retries:
                raise
            sleep(retry_delay_seconds)

    return client.collection(user_name=bgg_username, subtype=subtype)


def _should_include_collection_item(item) -> bool:
    if bool(getattr(item, "owned", False)):
        return True

    status_flags = [
        bool(getattr(item, "preordered", False)),
        bool(getattr(item, "prev_owned", False)),
        bool(getattr(item, "want", False)),
        bool(getattr(item, "want_to_buy", False)),
        bool(getattr(item, "want_to_play", False)),
        bool(getattr(item, "for_trade", False)),
        bool(getattr(item, "wishlist", False)),
    ]
    return not any(status_flags)


def iter_owned_collection_items(client: BGGClient, *, bgg_username: str):
    collections = [
        (
            BGGRestrictCollectionTo.BOARD_GAME,
            fetch_owned_collection(
                client,
                bgg_username=bgg_username,
                subtype=BGGRestrictCollectionTo.BOARD_GAME,
            ),
        ),
        (
            BGGRestrictCollectionTo.BOARD_GAME_EXTENSION,
            fetch_owned_collection(
                client,
                bgg_username=bgg_username,
                subtype=BGGRestrictCollectionTo.BOARD_GAME_EXTENSION,
            ),
        ),
    ]

    for subtype, collection in collections:
        for item in collection:
            if _should_include_collection_item(item):
                yield subtype, item

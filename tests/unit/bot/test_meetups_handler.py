from types import SimpleNamespace

import pytest

from bot.app.handlers.meetups import (
    _format_actor_display_name,
    _format_create_meetup_confirmation,
    _format_creator_participation_notification,
    _format_group_meetup_card,
    _format_meetup_details,
    _get_creation_message_ids,
    _parse_chat_id,
    _start_private_chat_meetup_creation,
    receive_meetup_date,
    skip_game_selection,
)


def test_format_meetup_details_escapes_user_content() -> None:
    text = _format_meetup_details(
        {
            "id": 1,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "comment": "Играем в _Catan_ и *Azul* <test>",
            "participants": [
                {
                    "telegram_id": 100,
                    "display_name": "Anna & Co",
                    "username": None,
                    "status": "joined",
                }
            ],
        }
    )

    assert text.startswith("<b>в понедельник в 19:30</b>"), text
    assert "Играем в _Catan_ и *Azul* <test>" not in text
    assert "Играем в _Catan_ и *Azul* &lt;test&gt;" in text
    assert "Anna & Co" not in text
    assert "Anna &amp; Co" in text


def test_format_create_meetup_confirmation_escapes_comment() -> None:
    text = _format_create_meetup_confirmation(
        scheduled_at="2026-06-15T19:30:00+00:00",
        capacity_total=4,
        comment="Catan <Azul> & tea",
    )

    assert "Дата: <code>15.06.2026 19:30</code>" in text
    assert "Игроков: 4" in text
    assert "Catan &lt;Azul&gt; &amp; tea" in text


def test_format_create_meetup_confirmation_omits_empty_comment() -> None:
    text = _format_create_meetup_confirmation(
        scheduled_at="2026-06-15T19:30:00+00:00",
        capacity_total=4,
        comment=None,
    )

    assert "Комментарий:" not in text
    assert "без комментария" not in text


def test_format_create_meetup_confirmation_includes_selected_games() -> None:
    text = _format_create_meetup_confirmation(
        scheduled_at="2026-06-15T19:30:00+00:00",
        capacity_total=4,
        comment=None,
        selected_games=[
            {"id": 1, "title": "Catan"},
            {"id": 2, "title": "Azul"},
        ],
    )

    assert "Игры:" in text
    assert "- Catan" in text
    assert "- Azul" in text


def test_get_creation_message_ids_deduplicates_extra_message_ids() -> None:
    message_ids = _get_creation_message_ids(
        {"creation_message_ids": [10, 11, 10, "bad"]},
        11,
        12,
    )

    assert message_ids == [10, 11, 12]


def test_format_meetup_details_omits_empty_comment() -> None:
    text = _format_meetup_details(
        {
            "id": 1,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "comment": None,
            "participants": [],
        }
    )

    assert "Комментарий:" not in text
    assert "без комментария" not in text


def test_format_group_meetup_card_omits_empty_comment() -> None:
    text = _format_group_meetup_card(
        {
            "id": 1,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "comment": None,
            "participants": [],
        }
    )

    assert "Комментарий:" not in text
    assert "без комментария" not in text
    assert text.startswith("<b>в понедельник в 19:30</b>"), text


def test_format_group_meetup_card_includes_selected_games() -> None:
    text = _format_group_meetup_card(
        {
            "id": 1,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "comment": None,
            "participants": [],
        },
        selected_games=[
            {"id": 1, "title": "Catan"},
            {"id": 2, "title": "Azul"},
        ],
    )

    assert "Игры:" in text
    assert "- Catan" in text
    assert "- Azul" in text
    assert text.startswith("<b>Catan в понедельник в 19:30</b>"), text


def test_format_meetup_details_includes_selected_games() -> None:
    text = _format_meetup_details(
        {
            "id": 1,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "comment": None,
            "participants": [],
        },
        selected_games=[
            {"id": 1, "title": "Catan"},
            {"id": 2, "title": "Azul"},
        ],
    )

    assert "Игры:" in text
    assert "- Catan" in text
    assert "- Azul" in text
    assert text.startswith("<b>Catan в понедельник в 19:30</b>"), text


def test_parse_chat_id_accepts_positive_and_negative_values() -> None:
    assert _parse_chat_id("meetup_chat_select:123", "meetup_chat_select") == 123
    assert _parse_chat_id("meetup_chat_select:-100123", "meetup_chat_select") == -100123
    assert _parse_chat_id("meetup_chat_select:abc", "meetup_chat_select") is None
    assert _parse_chat_id("other_prefix:123", "meetup_chat_select") is None


def test_get_meetup_chat_selection_keyboard_truncates_long_titles() -> None:
    from bot.app.keyboards.meetups import get_meetup_chat_selection_keyboard

    keyboard = get_meetup_chat_selection_keyboard(
        [
            {"telegram_chat_id": -1001, "title": "A" * 100},
            {"telegram_chat_id": -1002, "title": "Short name"},
        ]
    )

    labels = [row[0].text for row in keyboard.inline_keyboard]

    assert labels[0].endswith("...")
    assert len(labels[0]) <= 50
    assert labels[1] == "Short name"


class DummyState:
    def __init__(self):
        self.data = {}
        self.state = None

    async def clear(self) -> None:
        self.data.clear()
        self.state = None

    async def update_data(self, **data) -> None:
        self.data.update(data)

    async def set_state(self, state) -> None:
        self.state = state

    async def get_data(self) -> dict:
        return self.data


class DummyMessage:
    def __init__(self):
        self.chat = SimpleNamespace(type="private", id=-1)
        self.from_user = SimpleNamespace(
            id=123,
            username="testuser",
            first_name="Test",
            last_name="User",
        )
        self.last_answer = None

    async def answer(self, text: str, parse_mode: str | None = None, reply_markup=None):
        self.last_answer = SimpleNamespace(text=text, reply_markup=reply_markup, message_id=1)
        return self.last_answer

    async def edit_text(self, text: str, parse_mode: str | None = None, reply_markup=None):
        self.last_edited = SimpleNamespace(text=text, reply_markup=reply_markup)
        return self.last_edited


class FakeBackendAPIClient:
    async def sync_telegram_user(self, **kwargs):
        return {}

    async def get_user_by_telegram_id(self, telegram_id: int):
        return {"id": 1}


@pytest.mark.asyncio
async def test_start_private_chat_meetup_creation_single_chat_sets_group_mode(monkeypatch) -> None:
    class SingleChatBackend(FakeBackendAPIClient):
        async def list_telegram_chat_memberships(self, user_id: int):
            return [
                {"telegram_chat_id": -1001, "telegram_thread_id": 111, "title": "Test Chat"},
            ]

    monkeypatch.setattr("bot.app.handlers.meetups.BackendAPIClient", SingleChatBackend)

    state = DummyState()
    message = DummyMessage()

    await _start_private_chat_meetup_creation(message, state)

    assert state.state is not None
    assert state.data["telegram_chat_id"] == -1001
    assert state.data["telegram_thread_id"] == 111
    assert state.data["group_mode"] is True
    assert message.last_answer is not None
    assert "Укажи дату" in message.last_answer.text


@pytest.mark.asyncio
async def test_start_private_chat_meetup_creation_multiple_chats_shows_selection(
    monkeypatch,
) -> None:
    class MultipleChatsBackend(FakeBackendAPIClient):
        async def list_telegram_chat_memberships(self, user_id: int):
            return [
                {"telegram_chat_id": -1001, "telegram_thread_id": 111, "title": "First Chat"},
                {"telegram_chat_id": -1002, "telegram_thread_id": 222, "title": "Second Chat"},
            ]

    monkeypatch.setattr("bot.app.handlers.meetups.BackendAPIClient", MultipleChatsBackend)

    state = DummyState()
    message = DummyMessage()

    await _start_private_chat_meetup_creation(message, state)

    assert state.state is not None
    assert "waiting_for_chat_selection" in str(state.state)
    assert message.last_answer is not None
    assert "Выбери чат" in message.last_answer.text
    assert len(message.last_answer.reply_markup.inline_keyboard) == 2


@pytest.mark.asyncio
async def test_skip_game_selection_moves_to_capacity() -> None:
    state = DummyState()
    message = DummyMessage()
    # Simulate a callback query-like object
    callback = SimpleNamespace(
        data="meetup_game_skip",
        message=message,
        from_user=SimpleNamespace(id=123),
    )

    await skip_game_selection(callback, state)

    assert state.state is not None
    assert "waiting_for_capacity" in str(state.state)
    assert hasattr(message, "last_edited")
    assert "Сколько всего игроков" in message.last_edited.text


@pytest.mark.asyncio
async def test_receive_meetup_date_builds_letters(monkeypatch) -> None:
    class GamesBackend(FakeBackendAPIClient):
        async def list_games(self, owner_id: int, game_type: str, limit: int, offset: int):
            return [
                {"id": 1, "title": "Arcs", "min_players": 1, "max_players": 4},
                {"id": 2, "title": "Iss Vanguard", "min_players": 1, "max_players": 4},
            ]

    monkeypatch.setattr("bot.app.handlers.meetups.BackendAPIClient", GamesBackend)

    state = DummyState()
    message = DummyMessage()
    message.text = "15.06.2099 19:30"
    message.message_id = 1

    await receive_meetup_date(message, state)

    data = await state.get_data()
    assert "letters_map" in data
    assert set(data["letters_map"].keys()) == {"A", "I"}
    assert hasattr(message, "last_edited") or hasattr(message, "last_answer")


def test_format_actor_display_name_prefers_username() -> None:
    assert _format_actor_display_name({"username": "boardgamer", "display_name": "Board Gamer"}) == (
        "@boardgamer"
    )


def test_format_actor_display_name_escapes_display_name() -> None:
    assert _format_actor_display_name({"username": None, "display_name": "Anna & Co"}) == (
        "Anna &amp; Co"
    )


def test_format_creator_participation_notification_join() -> None:
    text = _format_creator_participation_notification(
        meetup={
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 6,
            "comment": "Играем в _Catan_",
            "participants": [{"telegram_id": 1}, {"telegram_id": 2}],
        },
        actor_display="@alice",
        action="join",
    )

    assert "<b>@alice</b> записался на встречу." in text
    assert "Участников: 2/6" in text
    assert "Играем в _Catan_" in text


def test_format_creator_participation_notification_leave_omits_comment() -> None:
    text = _format_creator_participation_notification(
        meetup={
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "comment": None,
            "participants": [],
        },
        actor_display="Bob",
        action="leave",
    )

    assert "<b>Bob</b> отписался от встречи." in text
    assert "Участников: 0/4" in text
    assert "Комментарий:" not in text

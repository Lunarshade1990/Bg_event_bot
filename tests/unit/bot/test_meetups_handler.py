from bot.app.handlers.meetups import (
    _format_create_meetup_confirmation,
    _format_group_meetup_card,
    _format_meetup_details,
    _get_creation_message_ids,
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

    assert "<b>Встреча #1</b>" in text
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

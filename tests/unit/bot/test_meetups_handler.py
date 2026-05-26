from bot.app.handlers.meetups import _format_meetup_details


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

from bot.app.handlers.meetups import _format_group_meetup_card


def test_group_meetup_card_does_not_contain_ids() -> None:
    text = _format_group_meetup_card(
        {
            "id": 1,
            "scheduled_at": "2026-06-15T19:30:00+00:00",
            "capacity_total": 4,
            "comment": "Test",
            "participants": [
                {
                    "telegram_id": 100,
                    "display_name": "Anna",
                    "username": "anna_test",
                    "status": "joined",
                }
            ],
        }
    )

    assert "100" not in text
    assert "@anna_test" in text


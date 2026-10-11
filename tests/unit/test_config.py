import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings


def test_internal_api_token_is_required() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, DB_PASSWORD="db-test")


def test_internal_api_token_must_not_be_a_placeholder() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            DB_PASSWORD="db-test",
            INTERNAL_API_TOKEN="replace_me",
        )


def test_internal_api_token_accepts_32_character_secret() -> None:
    settings = Settings(
        _env_file=None,
        DB_PASSWORD="db-test",
        INTERNAL_API_TOKEN="x" * 32,
    )

    assert len(settings.internal_api_token) == 32

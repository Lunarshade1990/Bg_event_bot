from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="dev", alias="APP_ENV")

    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="boardgames_meetup_bot", alias="DB_NAME")
    db_user: str = Field(default="boardgames_user", alias="DB_USER")
    db_password: str = Field(default="change_me", alias="DB_PASSWORD")

    telegram_bot_token: str = Field(default="replace_me", alias="TELEGRAM_BOT_TOKEN")
    bgg_access_token: str = Field(default="replace_me", alias="BGG_ACCESS_TOKEN")
    internal_api_token: str = Field(default="replace_me", alias="INTERNAL_API_TOKEN")

    backend_host: str = Field(default="127.0.0.1", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    backend_base_url: str = Field(default="http://127.0.0.1:8000", alias="BACKEND_BASE_URL")

    telegram_group_id: int | None = Field(default=None, alias="TELEGRAM_GROUP_ID")
    telegram_topic_name: str | None = Field(default=None, alias="TELEGRAM_TOPIC_NAME")

    @property
    def sqlalchemy_database_uri(self) -> str:
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        ).render_as_string(hide_password=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()

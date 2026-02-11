from __future__ import annotations

import pathlib

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = pathlib.Path(__file__).parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
    )

    openai_api_key: str
    discord_guild_id: int
    marketplace_channel_name: str = "the-marketplace"
    database_path: str = "moltbook.db"
    host: str = "0.0.0.0"
    port: int = 8000

    conversation_min_interval: int = 30
    conversation_max_interval: int = 120
    conversation_turns: int = 4

    openai_model: str = "gpt-4o-mini"


settings = Settings()  # type: ignore[call-arg]

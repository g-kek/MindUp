from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    gemini_api_key: str = Field(alias="GEMINI_API_KEY")

    database_path: Path = Field(default=Path("data/mindup.sqlite3"), alias="DATABASE_PATH")
    audio_dir: Path = Field(default=Path("data/audio"), alias="AUDIO_DIR")
    app_timezone: str = Field(default="Asia/Novosibirsk", alias="APP_TIMEZONE")

    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    gemini_stt_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_STT_MODEL")
    gemini_fallback_models: str = Field(
        default="gemini-2.5-flash-lite",
        alias="GEMINI_FALLBACK_MODELS",
    )
    gemini_stt_fallback_models: str = Field(
        default="gemini-2.5-flash-lite",
        alias="GEMINI_STT_FALLBACK_MODELS",
    )
    tts_voice: str = Field(default="en-US-JennyNeural", alias="TTS_VOICE")
    tts_rate: str = Field(default="+0%", alias="TTS_RATE")
    support_chat_id: str = Field(default="", alias="SUPPORT_CHAT_ID")
    feedback_chat_id: str = Field(default="", alias="FEEDBACK_CHAT_ID")

    min_dialogue_turns: int = Field(default=3, alias="MIN_DIALOGUE_TURNS")
    max_dialogue_turns: int = Field(default=4, alias="MAX_DIALOGUE_TURNS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def ensure_runtime_dirs(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_dirs()
    return settings

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator
from urllib.parse import urlparse
from pathlib import Path


# Корневая папка приложения backend/app
BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # Секретный токен бота MAX.
    MAX_BOT_TOKEN: str = Field(
        min_length=5,
        description="Секретный токен бота MAX",
    )

    # Публичный URL нашего приложения.
    APP_URL: str = "http://localhost:8000"

    # База данных SQLite для MVP.
    DATABASE_URL: str = "sqlite:///./data/businesscontrol.db"

    # Базовый URL API MAX.
    MAX_API_BASE_URL: str = "https://platform-api2.max.ru"

    # Папка для фотографий пользователей.
    UPLOAD_DIR: Path = BASE_DIR / "uploads"

    # Источники, которым разрешены запросы к API.
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "https://web.max.ru",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("APP_URL", "MAX_API_BASE_URL")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Проверяем, что URL содержит схему и домен."""
        parsed = urlparse(v)

        if not parsed.scheme or not parsed.netloc:
            raise ValueError(
                f"Некорректный URL: {v!r}. "
                "Должен содержать схему (http/https) и домен."
            )

        return v

    @model_validator(mode="after")
    def ensure_upload_dir_exists(self) -> "Settings":
        """Создаём папку для загрузок, если её ещё нет."""
        self.UPLOAD_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )
        return self


settings = Settings()
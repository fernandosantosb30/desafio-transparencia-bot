from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "transparencia-bot"
    PORT: int = Field(default=8000, ge=1, le=65535)
    PLAYWRIGHT_HEADLESS: bool = True
    MAX_CONCURRENT_REQUESTS: int = Field(default=5, ge=1)
    REQUEST_TIMEOUT_SECONDS: float = Field(default=120, gt=0)
    NAVIGATION_TIMEOUT_MS: int = Field(default=30000, gt=0)
    PORTAL_URL: str = "https://portaldatransparencia.gov.br"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()

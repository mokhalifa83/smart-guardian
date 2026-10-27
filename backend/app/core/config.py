from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Guardian"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    # Safety Barrier - Smart Guardian is strictly a surveillance and decision support system.
    ALLOW_FIELD_CONTROL_COMMANDS: bool = False  # NEVER allowed in Phase 1

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/smart_guardian"
    )
    SYNC_DATABASE_URL: Optional[str] = Field(
        default="postgresql://postgres:postgres@localhost:5432/smart_guardian"
    )

    # Ingestion & Infrastructure Rate Limiting
    RATE_LIMIT_PER_SOURCE_PER_MINUTE: int = Field(default=300)
    RATE_LIMIT_PER_WELL_PER_MINUTE: int = Field(default=60)

    # Production Surveillance Defaults (stored per well in DB, these are fallbacks for initial well creation)
    DEFAULT_WC_THRESHOLD_PERCENT: float = 80.0
    DEFAULT_WC_TREND_WINDOW_HOURS: int = 24
    DEFAULT_ALERT_COOLDOWN_MINUTES: int = 60
    DEFAULT_SURVEILLANCE_INTERVAL_MINUTES: int = 5

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # Security
    API_KEY_HEADER: str = "X-API-Key"
    API_KEYS: List[str] = ["sg-dev-key-2026", "control-room-key-read-only"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@db:5432/crm"
    )
    secret_key: str = Field(default="change-me")
    access_token_expire_minutes: int = Field(default=60 * 24)
    enforce_lan_only: bool = Field(default=True)
    allowed_subnets: str = Field(
        default="127.0.0.0/8,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
    )
    cors_origins: str = Field(default="*")
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    data_root: str = Field(default="./data/network_share")
    excel_cache_ttl_seconds: int = Field(default=300)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

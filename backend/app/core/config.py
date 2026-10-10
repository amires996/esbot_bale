from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "ESBot API"
    app_env: str = "development"
    database_url: str = "sqlite:///./esbot.db"
    secret_key: str = ""
    access_token_minutes: int = 30
    cors_origins: str = "http://localhost:5173"
    business_timezone: str = "Asia/Tehran"
    bale_bot_token: str = ""
    bale_admin_chat_id: str = ""
    bale_polling_enabled: bool = True
    bale_poll_timeout_seconds: int = 20
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

settings = Settings()

def validate_production_settings() -> None:
    if settings.app_env.lower() == "production":
        if len(settings.secret_key) < 32:
            raise RuntimeError("SECRET_KEY must contain at least 32 characters in production")
        if settings.database_url.startswith("sqlite"):
            raise RuntimeError("PostgreSQL is required in production; configure DATABASE_URL")

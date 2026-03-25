from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Activity Registration and Funding Audit Platform"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = "postgresql+psycopg2://platform_user:platform_pass@postgres:5432/platform_db"

    jwt_access_secret: str = "change_me_access_secret"
    jwt_refresh_secret: str = "change_me_refresh_secret"
    jwt_access_exp_minutes: int = 60
    jwt_refresh_exp_minutes: int = 4320

    login_window_minutes: int = 5
    login_max_attempts: int = 10
    login_lock_minutes: int = 30

    cors_origins: str = "http://localhost:5173"
    storage_root: str = "/data/storage"
    backup_root: str = "/data/backups"
    export_root: str = "/data/exports"
    backup_schedule_enabled: bool = True
    backup_schedule_hour_utc: int = 2
    upload_chunk_max_bytes: int = 5242880
    upload_session_ttl_minutes: int = 120

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()

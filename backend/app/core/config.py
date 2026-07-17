from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "ProductStudio AI"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@db:5432/productstudio"
    SECRET_KEY: str = "dummy-dev-secret-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    UPLOAD_DIR: str = "/data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 15
    REDIS_URL: str = "redis://redis:6379/0"
    AI_SERVICE_URL: str = "http://ai-service:8100"
    CORS_ORIGINS: str = "http://localhost:5174,http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()

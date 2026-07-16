from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_secret_key: str = "dev-secret-change-me"
    app_domain: str = "localhost"

    database_url: str = "postgresql://agentlab:agentlab@localhost:5432/agentlab"
    redis_url: str = "redis://localhost:6379/0"

    owner_email: str = "owner@agentlab.local"
    owner_password: str = "changeme"

    cors_origins: str = "http://localhost:3000"

    session_cookie_name: str = "agentlab_session"
    session_max_age_seconds: int = 86400

    ai_base_url: str = "https://api.openai.com"
    ai_api_key: str = ""
    ai_default_model: str = "gpt-4o-mini"

    embedding_base_url: str = "https://api.openai.com"
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    uploads_dir: str = "uploads"
    celery_broker_url: str = ""
    celery_result_backend: str = ""

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

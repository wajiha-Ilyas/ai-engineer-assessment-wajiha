from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    groq_api_key: str
    groq_model: str = "llama-3.1-8b-instant"
    superhero_api_token: str
    app_log_level: str = "INFO"
    allowed_origins: str = ""

    # Memory
    redis_url: str = ""           # leave empty to use in-memory fallback
    session_ttl_seconds: int = 3600  # 1 hour


settings = Settings()

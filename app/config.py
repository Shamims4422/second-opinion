from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, overridable via CRITICLOOP_-prefixed environment variables."""

    database_url: str = "sqlite:///./criticloop.db"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    min_similarity: float = 0.3
    retrieval_limit: int = 5

    model_config = SettingsConfigDict(env_prefix="CRITICLOOP_", env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()

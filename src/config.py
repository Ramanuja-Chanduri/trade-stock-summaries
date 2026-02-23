from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    GROQ_API_KEY: str
    HF_TOKEN: str

@lru_cache()
def get_settings() -> Settings:
    return Settings()
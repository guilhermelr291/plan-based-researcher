from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str
    database_url: str
    api_host: str = "127.0.0.1"
    api_port: int = 8001
    research_timeout_seconds: int = 120

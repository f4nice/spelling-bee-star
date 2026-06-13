from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "拼词之星"
    database_url: str = "mysql+pymysql://root:password@127.0.0.1:3306/spelling_bee?charset=utf8mb4"
    merriam_webster_api_key: str = ""
    merriam_webster_reference: str = "collegiate"
    translation_provider: str = "mymemory"
    libretranslate_url: str = ""
    libretranslate_api_key: str = ""
    image_provider: str = "wikimedia"
    list_delete_password: str = "841108"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()

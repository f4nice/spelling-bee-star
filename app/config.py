from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SpeakEasy"
    database_url: str = "mysql+pymysql://root:password@127.0.0.1:3306/spelling_bee?charset=utf8mb4"
    merriam_webster_api_key: str = ""
    merriam_webster_reference: str = "collegiate"
    translation_provider: str = "mymemory"
    libretranslate_url: str = ""
    libretranslate_api_key: str = ""
    image_provider: str = "wikimedia"
    list_delete_password: str = "841108"
    ai_image_provider: str = "tencent_hunyuan"
    openai_api_key: str = ""
    openai_image_model: str = "gpt-image-1"
    ai_tts_provider: str = "openai"
    openai_tts_model: str = "gpt-4o-mini-tts"
    openai_tts_voice_us: str = "marin"
    openai_tts_voice_gb: str = "cedar"
    tencentcloud_secret_id: str = ""
    tencentcloud_secret_key: str = ""
    tencentcloud_region: str = "ap-guangzhou"
    tencent_hunyuan_image_action: str = "TextToImageRapid"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

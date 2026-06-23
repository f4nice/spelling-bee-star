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
    ai_image_provider: str = "dashscope"
    openai_api_key: str = ""
    openai_image_model: str = "gpt-image-1"
    dashscope_api_key: str = ""
    dashscope_image_endpoint: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
    dashscope_task_endpoint: str = "https://dashscope.aliyuncs.com/api/v1/tasks"
    dashscope_image_poll_seconds: float = 2.0
    dashscope_image_timeout_seconds: int = 180
    ai_tts_provider: str = "openai"
    openai_tts_model: str = "gpt-4o-mini-tts"
    openai_tts_voice_us: str = "alloy"
    openai_tts_voice_gb: str = "alloy"
    aliyun_nls_appkey: str = ""
    aliyun_nls_token: str = ""
    aliyun_access_key_id: str = ""
    aliyun_access_key_secret: str = ""
    aliyun_token_region: str = "cn-shanghai"
    aliyun_token_endpoint: str = "https://nls-meta.cn-shanghai.aliyuncs.com/"
    aliyun_tts_gateway: str = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/tts"
    aliyun_tts_format: str = "mp3"
    aliyun_tts_sample_rate: int = 16000
    aliyun_tts_voice_us: str = "betty"
    aliyun_tts_voice_gb: str = "beth"
    aliyun_tts_voice_us_female: str = "betty"
    aliyun_tts_voice_us_male: str = "brian"
    aliyun_tts_voice_gb_female: str = "beth"
    aliyun_tts_voice_gb_male: str = "david"
    aliyun_tts_volume: int = 50
    aliyun_tts_speech_rate: int = 0
    aliyun_tts_pitch_rate: int = 0
    tencentcloud_secret_id: str = ""
    tencentcloud_secret_key: str = ""
    tencentcloud_region: str = "ap-guangzhou"
    tencent_hunyuan_image_action: str = "TextToImageRapid"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

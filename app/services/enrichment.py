from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Word
from app.services.audio_storage import is_local_audio_url, store_first_available_audio
from app.services.dictionary import FreeDictionaryAudioClient, FreeDictionaryClient, MerriamWebsterClient
from app.services.image_storage import is_local_media_url, store_word_image
from app.services.images import ImageClient
from app.services.translation import TranslationClient


UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
IMAGE_DIR = UPLOAD_DIR / "images"
AUDIO_DIR = UPLOAD_DIR / "audio"


async def enrich_word(db: Session, word: Word) -> Word:
    settings = get_settings()
    merriam_webster = MerriamWebsterClient(settings)
    free_dictionary = FreeDictionaryClient()
    audio_client = FreeDictionaryAudioClient()
    translator = TranslationClient(settings)
    images = ImageClient()

    try:
        if settings.merriam_webster_api_key:
            try:
                entry = await merriam_webster.lookup(word.word)
            except Exception:
                entry = await free_dictionary.lookup(word.word)
        else:
            entry = await free_dictionary.lookup(word.word)

        word.phonetic = word.phonetic or entry.phonetic
        if not word.american_audio_locked:
            word.american_audio_url = entry.american_audio_url
        if not word.british_audio_locked:
            word.british_audio_url = entry.british_audio_url
        if not word.english_definition_locked:
            word.english_definition = entry.english_definition
        if not word.english_example_locked:
            word.english_example = entry.english_example
        word.source = entry.source

        american_audio, british_audio = await audio_client.lookup_audio(word.word)
        if not word.american_audio_locked:
            word.american_audio_url = word.american_audio_url or american_audio
        if not word.british_audio_locked:
            word.british_audio_url = word.british_audio_url or british_audio

        optional_errors: list[str] = []
        if not word.chinese_definition and not word.chinese_definition_locked:
            try:
                word.chinese_definition = await translator.translate_definition(entry.english_definition)
            except Exception as exc:
                optional_errors.append(f"中文翻译暂不可用: {exc}")

        if word.image_url and not word.image_locked and not is_local_media_url(word.image_url):
            try:
                word.image_url = await store_word_image(word.word, word.image_url, IMAGE_DIR)
            except Exception as exc:
                optional_errors.append(f"图片本地化暂不可用: {exc}")
        if not word.image_url and not word.image_locked:
            try:
                remote_image_url = await images.find_image(word.word)
                if remote_image_url:
                    word.image_url = await store_word_image(word.word, remote_image_url, IMAGE_DIR)
            except Exception as exc:
                optional_errors.append(f"图片搜索暂不可用: {exc}")

        if not word.american_audio_locked and not is_local_audio_url(word.american_audio_url):
            try:
                word.american_audio_url = await store_first_available_audio(word.word, "us", AUDIO_DIR) or word.american_audio_url
            except Exception as exc:
                optional_errors.append(f"美式音频本地化暂不可用: {exc}")
        if not word.british_audio_locked and not is_local_audio_url(word.british_audio_url):
            try:
                word.british_audio_url = await store_first_available_audio(word.word, "gb", AUDIO_DIR) or word.british_audio_url
            except Exception as exc:
                optional_errors.append(f"英式音频本地化暂不可用: {exc}")

        word.enrichment_status = "done"
        word.enrichment_error = "\n".join(optional_errors) or None
    except Exception as exc:
        word.enrichment_status = "failed"
        word.enrichment_error = str(exc)

    db.add(word)
    db.commit()
    db.refresh(word)
    return word

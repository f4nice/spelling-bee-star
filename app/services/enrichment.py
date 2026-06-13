from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Word
from app.services.dictionary import FreeDictionaryAudioClient, FreeDictionaryClient, MerriamWebsterClient
from app.services.image_storage import is_local_media_url, store_word_image
from app.services.images import ImageClient
from app.services.translation import TranslationClient


IMAGE_DIR = Path(__file__).resolve().parents[2] / "uploads" / "images"


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
        word.american_audio_url = entry.american_audio_url
        word.british_audio_url = entry.british_audio_url
        word.english_definition = entry.english_definition
        word.english_example = entry.english_example
        word.source = entry.source

        american_audio, british_audio = await audio_client.lookup_audio(word.word)
        word.american_audio_url = word.american_audio_url or american_audio
        word.british_audio_url = british_audio

        optional_errors: list[str] = []
        if not word.chinese_definition:
            try:
                word.chinese_definition = await translator.translate_definition(entry.english_definition)
            except Exception as exc:
                optional_errors.append(f"中文翻译暂不可用: {exc}")
        if word.image_url and not is_local_media_url(word.image_url):
            try:
                word.image_url = await store_word_image(word.word, word.image_url, IMAGE_DIR)
            except Exception as exc:
                optional_errors.append(f"图片本地化暂不可用: {exc}")
        if not word.image_url:
            try:
                remote_image_url = await images.find_image(word.word)
                if remote_image_url:
                    word.image_url = await store_word_image(word.word, remote_image_url, IMAGE_DIR)
            except Exception as exc:
                optional_errors.append(f"图片搜索暂不可用: {exc}")

        word.enrichment_status = "done"
        word.enrichment_error = "\n".join(optional_errors) or None
    except Exception as exc:
        word.enrichment_status = "failed"
        word.enrichment_error = str(exc)

    db.add(word)
    db.commit()
    db.refresh(word)
    return word

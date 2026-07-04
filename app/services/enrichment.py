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


NATURAL_CHINESE_DEFINITION_OVERRIDES = {
    "abandon": "放弃；抛弃；停止支持或使用。",
    "abandoned": "被遗弃的；无人照管的；废弃不用的。",
    "abandonment": "放弃；抛弃；遗弃。",
}


BAD_CHINESE_DEFINITION_PATTERNS = (
    "放弃或放弃对自己的控制",
    "屈服于自己的情绪",
    "屈服于自己",
)


async def enrich_word(db: Session, word: Word, *, include_images: bool = True) -> Word:
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
        word.part_of_speech = word.part_of_speech or entry.part_of_speech
        if not word.american_audio_locked:
            word.american_audio_url = entry.american_audio_url
        if not word.british_audio_locked:
            word.british_audio_url = entry.british_audio_url
        if entry.english_definition and not word.english_definition_locked:
            word.english_definition = word.english_definition or entry.english_definition
        if entry.english_example and not word.english_example_locked:
            word.english_example = word.english_example or entry.english_example
        word.source = entry.source

        american_audio, british_audio = await audio_client.lookup_audio(word.word)
        if not word.american_audio_locked:
            word.american_audio_url = word.american_audio_url or american_audio
        if not word.british_audio_locked:
            word.british_audio_url = word.british_audio_url or british_audio

        optional_errors: list[str] = []
        current_chinese_definition = word.chinese_definition
        natural_definition = naturalize_chinese_definition(word.word, entry.english_definition, None)
        if natural_definition and should_refresh_chinese_definition(
            word.word,
            current_chinese_definition,
            entry.english_definition,
        ):
            word.chinese_definition = natural_definition
        elif (
            not word.chinese_definition_locked
            and should_refresh_chinese_definition(word.word, current_chinese_definition, entry.english_definition)
        ):
            try:
                translated_definition = await translator.translate_definition(entry.english_definition)
                word.chinese_definition = (
                    naturalize_chinese_definition(word.word, entry.english_definition, translated_definition)
                    or translated_definition
                    or word.chinese_definition
                )
            except Exception as exc:
                optional_errors.append(f"中文翻译暂不可用: {exc}")

        if include_images and word.image_url and not word.image_locked and not is_local_media_url(word.image_url):
            try:
                word.image_url = await store_word_image(word.word, word.image_url, IMAGE_DIR)
            except Exception as exc:
                optional_errors.append(f"图片本地化暂不可用: {exc}")
        if include_images and not word.image_url and not word.image_locked:
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
        word.enrichment_error = _friendly_enrichment_error(str(exc))

    db.add(word)
    db.commit()
    db.refresh(word)
    return word


def _friendly_enrichment_error(error: str) -> str:
    lower_error = error.lower()
    if "api.dictionaryapi.dev" in lower_error and "404" in lower_error:
        return "开放词典暂未收录这个词，可以手动编辑定义、例句和音频。"
    if "client error" in lower_error and "404" in lower_error:
        return "词典暂未收录这个词，可以手动编辑定义、例句和音频。"
    return error


def naturalize_chinese_definition(
    word_text: str | None,
    english_definition: str | None,
    translated_definition: str | None,
) -> str | None:
    normalized_word = (word_text or "").strip().lower()
    if normalized_word in NATURAL_CHINESE_DEFINITION_OVERRIDES:
        return NATURAL_CHINESE_DEFINITION_OVERRIDES[normalized_word]

    text = _clean_chinese_definition(translated_definition)
    if not text:
        return None

    if _looks_like_literal_translation(text):
        return _fallback_chinese_gloss(normalized_word, english_definition) or text
    return text


def should_refresh_chinese_definition(
    word_text: str | None,
    chinese_definition: str | None,
    english_definition: str | None = None,
) -> bool:
    current = _clean_chinese_definition(chinese_definition)
    normalized_word = (word_text or "").strip().lower()
    if not current:
        return True
    override = NATURAL_CHINESE_DEFINITION_OVERRIDES.get(normalized_word)
    if override and current != override:
        return True
    return _looks_like_literal_translation(current)


def _clean_chinese_definition(text: str | None) -> str | None:
    cleaned = " ".join((text or "").replace("\r", "\n").split())
    return cleaned or None


def _looks_like_literal_translation(text: str) -> bool:
    if any(pattern in text for pattern in BAD_CHINESE_DEFINITION_PATTERNS):
        return True
    return text.count("自己") >= 2 and text.count("或") >= 2 and len(text) > 30


def _fallback_chinese_gloss(normalized_word: str, english_definition: str | None) -> str | None:
    lower_definition = (english_definition or "").lower()
    if "give up" in lower_definition and "control" in lower_definition:
        return "放弃；让出控制；不再坚持。"
    if normalized_word.endswith("ed") and "abandon" in lower_definition:
        return "被遗弃的；无人照管的。"
    return None

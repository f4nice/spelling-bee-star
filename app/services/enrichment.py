import asyncio
import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Word
from app.services.audio_storage import is_local_audio_url, store_audio_candidate, store_first_available_audio
from app.services.dictionary import FreeDictionaryAudioClient, FreeDictionaryClient, MerriamWebsterClient
from app.services.image_storage import is_local_media_url, store_word_image
from app.services.images import ImageClient
from app.services.translation import TranslationClient
from app.services.web_dictionary import CambridgeDictionaryClient
from app.services.youdao_dictionary import YoudaoDictionaryClient
from app.services.wordnik_dictionary import WordnikDictionaryClient
from app.services.reviewed_dictionary import lookup_reviewed_entry
from app.services.merriam_webster_web import MerriamWebsterWebClient
from app.services.teaching_example import TeachingExampleClient


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


DICTIONARY_FIELDS = (
    "phonetic", "part_of_speech", "english_definition", "chinese_definition",
    "english_example", "american_audio_url", "british_audio_url",
)


def missing_dictionary_fields(word: Word) -> list[str]:
    return [
        field for field in DICTIONARY_FIELDS
        if not str(getattr(word, field, None) or "").strip()
        and not getattr(word, field.removesuffix("_url") + "_locked", False)
    ]


TEXT_FIELD_LABELS = {
    "phonetic": "音标", "part_of_speech": "词性", "english_definition": "英文释义",
    "chinese_definition": "中文释义", "english_example": "英文例句",
}


def _normalized_definition(value):
    return " ".join(re.findall(r"[\w]+", (value or "").casefold()))


def _pos_family(value):
    text = (value or "").strip().lower().rstrip(".")
    for family, labels in {
        "verb": ("v", "vt", "vi", "verb", "transitive verb", "intransitive verb"),
        "noun": ("n", "noun"), "adjective": ("adj", "adjective"),
        "adverb": ("adv", "adverb"),
    }.items():
        if text in labels:
            return family
    return text


def _merge_dictionary_entry(word, entry):
    """Fill independent gaps, but never attach a different sense's example."""
    changed = []
    missing = set(missing_dictionary_fields(word))
    compatible_pos = not word.part_of_speech or not entry.part_of_speech or _pos_family(word.part_of_speech) == _pos_family(entry.part_of_speech)
    retained_definition = str(word.english_definition or "").strip()
    matches_retained_sense = bool(entry.english_definition) and _normalized_definition(retained_definition) == _normalized_definition(entry.english_definition)
    for field in ("phonetic", "american_audio_url", "british_audio_url"):
        value = getattr(entry, field, None)
        if field in missing and value:
            setattr(word, field, value)
            changed.append(field)
    if "part_of_speech" in missing and entry.part_of_speech and (not retained_definition or matches_retained_sense):
        word.part_of_speech = entry.part_of_speech
        changed.append("part_of_speech")
    if "english_definition" in missing and entry.english_definition and compatible_pos:
        word.english_definition = entry.english_definition
        changed.append("english_definition")
    same_sense = bool(entry.english_definition) and _normalized_definition(word.english_definition) == _normalized_definition(entry.english_definition)
    for field in ("english_example", "chinese_definition"):
        value = getattr(entry, field, None)
        # Chinese-only exact bilingual entries are useful when no English sense
        # exists yet; otherwise translate the retained sense instead of mixing.
        safe = same_sense or (field == "chinese_definition" and not word.english_definition and compatible_pos)
        if field in missing and value and safe:
            setattr(word, field, value)
            changed.append(field)
    if changed and entry.source:
        if not word.source:
            word.source = entry.source[:255]
        elif entry.source not in word.source:
            combined = f"{word.source} | {entry.source}"
            if len(combined) <= 255:
                word.source = combined
    return changed


async def _complete_dictionary_text(word, settings):
    """Keep querying after partial success; a missing field is not an exception."""
    reviewed = lookup_reviewed_entry(word.word)
    failures = []
    free_failed = False
    if reviewed:
        _merge_dictionary_entry(word, reviewed)
    providers = []
    if settings.merriam_webster_api_key:
        providers.append(("韦氏 API", MerriamWebsterClient(settings), 8))
    providers.extend([
        ("开放词典", FreeDictionaryClient(), 8),
        ("有道词典", YoudaoDictionaryClient(), 8),
        ("韦氏官网", MerriamWebsterWebClient(), 8),
        ("剑桥词典", CambridgeDictionaryClient(), 10),
        ("Wordnik", WordnikDictionaryClient(), 8),
    ])
    deadline = asyncio.get_running_loop().time() + 38
    for name, provider, timeout in providers:
        text_missing = set(missing_dictionary_fields(word)) & TEXT_FIELD_LABELS.keys()
        if not text_missing:
            break
        budget = deadline - asyncio.get_running_loop().time()
        if budget <= 0:
            failures.append("词典查询已超时")
            break
        try:
            entry = await asyncio.wait_for(provider.lookup(word.word), min(timeout, budget))
            _merge_dictionary_entry(word, entry)
        except Exception:
            if name == "开放词典":
                free_failed = True
            failures.append(f"{name}未返回可用词条")
    return free_failed, bool(reviewed), failures


async def enrich_word(
    db: Session, word: Word, *, include_images: bool = True, only_missing: bool = False,
) -> Word:
    settings = get_settings()
    audio_client = FreeDictionaryAudioClient()
    translator = TranslationClient(settings)
    images = ImageClient()

    if only_missing:
        for field in missing_dictionary_fields(word):
            if isinstance(getattr(word, field, None), str):
                setattr(word, field, None)

    try:
        free_dictionary_failed, reviewed_entry, source_failures = await _complete_dictionary_text(word, settings)
        optional_errors: list[str] = []

        # Older provider responses could contain encyclopedia abstracts instead
        # of dictionary senses. Preserve them for review, never derive new text.
        verified_context = _pos_family(word.part_of_speech) not in {"abstract:", "abstract", "unknown", "wikipedia"}
        if not verified_context:
            optional_errors.append("历史释义疑似百科内容，请先核对词性和英文释义")
        if verified_context and "chinese_definition" in missing_dictionary_fields(word) and word.english_definition:
            try:
                translated = await asyncio.wait_for(translator.translate_definition(word.english_definition), timeout=22)
                if translated:
                    word.chinese_definition = naturalize_chinese_definition(word.word, word.english_definition, translated) or translated
                else:
                    optional_errors.append("中文释义：翻译服务未返回有效结果（可能限流或未配置）")
            except Exception:
                optional_errors.append("中文释义：翻译服务暂不可用或限流，请稍后重试")
        if verified_context and "english_example" in missing_dictionary_fields(word) and word.english_definition:
            try:
                example = await asyncio.wait_for(TeachingExampleClient(settings).generate(
                    word.word, word.english_definition, word.part_of_speech,
                ), timeout=18)
                if example:
                    word.english_example = example
                else:
                    optional_errors.append("英文例句：未查到同义项例句，自编服务未返回可用结果")
            except Exception:
                optional_errors.append("英文例句：未查到同义项例句，自编服务暂不可用")

        # Save useful text before optional audio work can time out.
        db.add(word)
        db.commit()
        american_audio, british_audio = None, None
        if not free_dictionary_failed and not reviewed_entry and ((not word.american_audio_url and not word.american_audio_locked) or (not word.british_audio_url and not word.british_audio_locked)):
            try:
                american_audio, british_audio = await asyncio.wait_for(audio_client.lookup_audio(word.word), timeout=6)
            except Exception:
                optional_errors.append("在线词典音频暂不可用，将尝试其他发音来源。")
        if not word.american_audio_locked:
            word.american_audio_url = word.american_audio_url or american_audio
        if not word.british_audio_locked:
            word.british_audio_url = word.british_audio_url or british_audio

        if include_images and word.image_url and not word.image_locked and not is_local_media_url(word.image_url):
            try:
                word.image_url = await store_word_image(word.word, word.image_url, IMAGE_DIR)
            except Exception:
                optional_errors.append("图片本地化暂不可用")
        if include_images and not word.image_url and not word.image_locked:
            try:
                remote_image_url = await images.find_image(word.word)
                if remote_image_url:
                    word.image_url = await store_word_image(word.word, remote_image_url, IMAGE_DIR)
            except Exception:
                optional_errors.append("图片搜索暂不可用")

        if not word.american_audio_locked and not is_local_audio_url(word.american_audio_url):
            try:
                word.american_audio_url = await asyncio.wait_for(_store_dictionary_audio(
                    word.word, "us", word.american_audio_url,
                    include_dictionary=not free_dictionary_failed and not reviewed_entry,
                ), timeout=10) or word.american_audio_url
            except Exception:
                optional_errors.append("美式音频本地化暂不可用")
        if not word.british_audio_locked and not is_local_audio_url(word.british_audio_url):
            try:
                word.british_audio_url = await asyncio.wait_for(_store_dictionary_audio(
                    word.word, "gb", word.british_audio_url,
                    include_dictionary=not free_dictionary_failed and not reviewed_entry,
                ), timeout=10) or word.british_audio_url
            except Exception:
                optional_errors.append("英式音频本地化暂不可用")

        missing_text = [field for field in TEXT_FIELD_LABELS if field in missing_dictionary_fields(word)]
        has_text = any(str(getattr(word, field, None) or "").strip() for field in TEXT_FIELD_LABELS)
        word.enrichment_status = "partial" if missing_text and has_text else "failed" if missing_text else "done"
        if missing_text:
            detail = "、".join(TEXT_FIELD_LABELS[field] for field in missing_text)
            optional_errors.insert(0, f"仍缺{detail}；已继续查询可用词典，保留已获取的内容")
            optional_errors.extend(source_failures)
        if word.american_audio_url and word.british_audio_url:
            optional_errors = [error for error in optional_errors if error != "在线词典音频暂不可用，将尝试其他发音来源。"]
        word.enrichment_error = "\n".join(optional_errors) or None
    except Exception as exc:
        word.enrichment_status = "failed"
        word.enrichment_error = _friendly_enrichment_error(str(exc))

    db.add(word)
    db.commit()
    db.refresh(word)
    return word


async def _store_dictionary_audio(word: str, accent: str, remote_url: str | None, *, include_dictionary: bool = True) -> str | None:
    if remote_url:
        try:
            local_url = await store_audio_candidate(word, accent, "online-dictionary", remote_url, AUDIO_DIR)
            if local_url:
                return local_url
        except Exception:
            pass
    return await store_first_available_audio(word, accent, AUDIO_DIR, include_dictionary=include_dictionary)


def _friendly_enrichment_error(error: str) -> str:
    lower_error = error.lower()
    if "api.dictionaryapi.dev" in lower_error and "404" in lower_error:
        return "开放词典暂未收录这个词，可以手动编辑定义、例句和音频。"
    if "client error" in lower_error and "404" in lower_error:
        return "词典暂未收录这个词，可以手动编辑定义、例句和音频。"
    return "词典补全暂未完成，已保存的内容会保留，请稍后重试。"


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

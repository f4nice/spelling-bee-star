import asyncio
from calendar import monthrange
from datetime import date, datetime, timedelta
import html
from io import BytesIO
import json
from pathlib import Path
import random
import re
import sys
from threading import Lock, Thread
from typing import Any
from urllib.parse import quote_plus
from uuid import uuid4
import zipfile

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, func, inspect, or_, select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, SessionLocal, engine, get_db
from app.models import (
    CacheEntry,
    ChallengeDailyStat,
    ChallengeDailyWord,
    ChallengeProgress,
    ChallengeSpellingAttempt,
    DailyQuote,
    Word,
    WordList,
    WordListItem,
    WrongWord,
)
from app.services.enrichment import enrich_word
from app.services.excel_importer import parse_preview_from_excel, parse_words_from_preview
from app.services.audio_storage import audio_candidates_with_dictionary, is_local_audio_url, store_audio_candidate
from app.services.ai_image_generation import generate_dashscope_prompt_image, generate_word_image
from app.services.ai_tts import generate_word_ai_audio
from app.services.chinadaily import get_chinadaily_article, load_chinadaily_articles
from app.services.image_storage import is_local_media_url, remove_local_image, store_uploaded_word_image, store_word_image
from app.services.images import ImageClient


BASE_DIR = Path(__file__).resolve().parent
GOOD_WORDS_DIR = BASE_DIR.parent / "\u597d\u8bcd\u597d\u53e5"
if str(GOOD_WORDS_DIR) not in sys.path:
    sys.path.insert(0, str(GOOD_WORDS_DIR))

from booklearner.analyzer import (
    analyze_query as analyze_good_words_query,
    analyze_text as analyze_good_words_text,
    suggest_books as suggest_good_words_books,
)
from booklearner.storage import (
    get_analysis as get_good_words_analysis,
    get_storage_status as get_good_words_storage_status,
    list_featured_quotes as list_featured_good_words_quotes,
    list_recent_analyses as list_recent_good_words_analyses,
    save_analysis as save_good_words_analysis,
    save_clicked_word as save_good_words_clicked_word,
)


PREVIEW_DIR = BASE_DIR.parent / "uploads" / "previews"
MEDIA_DIR = BASE_DIR.parent / "uploads"
IMAGE_DIR = MEDIA_DIR / "images"
AUDIO_DIR = MEDIA_DIR / "audio"
BOOK_COVER_DIR = MEDIA_DIR / "book-covers"
VERSION_MATRIX_PATH = MEDIA_DIR / "version_matrix.json"
DEFAULT_VERSION_MATRIX_PATH = BASE_DIR.parent / "VERSION_MATRIX.default.json"
settings = get_settings()
DEFAULT_RELEASE_VERSION = "BIZ-REL-20260627-002"
DEFAULT_PAGE_VERSION = "v20260624.0"
LEGACY_MACHINE_CODE_FIELD = "machine" + "Code"
PUBLIC_ASSET_DIR = MEDIA_DIR / "generated-assets"
IMAGE_SYNC_JOBS: dict[str, dict] = {}


def is_ai_quota_error(detail: str) -> bool:
    lowered = (detail or "").lower()
    keywords = [
        "quota",
        "insufficient",
        "balance",
        "billing",
        "payment",
        "arrear",
        "throttl",
        "rate limit",
        "too many requests",
        "exceed",
        "limited",
        "余额",
        "额度",
        "欠费",
        "限流",
        "超限",
        "用量",
    ]
    return any(keyword in lowered for keyword in keywords)


def public_asset_extension(content: bytes) -> str:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content.startswith(b"\xff\xd8"):
        return ".jpg"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    return ".png"


def public_asset_slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value.lower()).strip("-") or "asset"


IMAGE_SYNC_LOCK = Lock()
CACHE_REFRESHING: set[str] = set()
CACHE_REFRESH_LOCK = Lock()

MEDIA_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
BOOK_COVER_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_ASSET_DIR.mkdir(parents=True, exist_ok=True)
app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/static/") or path.startswith("/media/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif path == "/tts" or re.fullmatch(r"/words/\d+/(tts|audio)", path):
        response.headers["Cache-Control"] = "public, max-age=2592000"
    elif re.fullmatch(r"/words/\d+/image-view", path):
        response.headers["Cache-Control"] = "public, max-age=600"
    return response


def static_asset_version() -> str:
    assets = [
        BASE_DIR / "static" / "styles.css",
        BASE_DIR / "static" / "vue" / "speakeasy-app.js",
    ]
    mtimes = [path.stat().st_mtime_ns for path in assets if path.exists()]
    return str(max(mtimes)) if mtimes else str(int(datetime.utcnow().timestamp()))


def default_version_matrix() -> dict[str, Any]:
    fallback = {
        "version": DEFAULT_RELEASE_VERSION,
        "releaseName": "Vue 全站版",
        "pageVersion": DEFAULT_PAGE_VERSION,
        "footerText": settings.app_name,
        "modules": [],
    }
    if not DEFAULT_VERSION_MATRIX_PATH.exists():
        return fallback
    try:
        data = json.loads(DEFAULT_VERSION_MATRIX_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback
    return data if isinstance(data, dict) else fallback


def normalize_version_matrix(data: dict[str, Any]) -> dict[str, Any]:
    matrix = dict(data)
    modules = matrix.get("modules")
    if not isinstance(modules, list):
        modules = []
    matrix["version"] = normalize_version_number(str(matrix.get("version") or "").strip())
    matrix["releaseName"] = str(matrix.get("releaseName") or "Vue 全站版").strip()
    matrix["pageVersion"] = normalize_page_version(str(matrix.get("pageVersion") or "").strip())
    matrix.pop(LEGACY_MACHINE_CODE_FIELD, None)
    matrix["footerText"] = str(matrix.get("footerText") or settings.app_name).strip()
    matrix["modules"] = [
        {
            "label": str(item.get("label") or "").strip(),
            "version": normalize_page_version(str(item.get("version") or "").strip()),
            "status": str(item.get("status") or "").strip(),
        }
        for item in modules
        if isinstance(item, dict) and str(item.get("label") or "").strip()
    ]
    return matrix


def normalize_version_number(version: str) -> str:
    if not version or version in {"v0.1", "v0.1.0"} or re.fullmatch(r"v\d{8}\.\d+", version):
        return DEFAULT_RELEASE_VERSION
    return version


def normalize_page_version(version: str) -> str:
    if not version or version in {"v0.1", "v0.1.0"}:
        return DEFAULT_PAGE_VERSION
    return version


def release_version_sort_key(version: str) -> tuple[int, int]:
    match = re.fullmatch(r"BIZ-REL-(\d{8})-(\d{3})", version.strip())
    if not match:
        return (0, 0)
    return (int(match.group(1)), int(match.group(2)))


def is_default_release_newer(matrix: dict[str, Any]) -> bool:
    current_version = normalize_version_number(str(matrix.get("version") or "").strip())
    return release_version_sort_key(DEFAULT_RELEASE_VERSION) > release_version_sort_key(current_version)


def ensure_version_matrix_file() -> dict[str, Any]:
    raw_data = default_version_matrix()
    if VERSION_MATRIX_PATH.exists():
        try:
            loaded = json.loads(VERSION_MATRIX_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                raw_data = loaded
        except (OSError, json.JSONDecodeError):
            pass
    matrix = normalize_version_matrix(raw_data)
    old_style_version = str(raw_data.get("version") or "").strip() in {"", "v0.1", "v0.1.0"}
    page_version = str(raw_data.get("pageVersion") or "").strip()
    old_style_page_version = page_version in {"", "v0.1", "v0.1.0"}
    old_style_modules = any(
        isinstance(item, dict) and str(item.get("version") or "").strip() in {"", "v0.1", "v0.1.0"}
        for item in (raw_data.get("modules") if isinstance(raw_data.get("modules"), list) else [])
    )
    default_release_newer = is_default_release_newer(raw_data)
    if default_release_newer:
        matrix = normalize_version_matrix(default_version_matrix())
    if (
        not VERSION_MATRIX_PATH.exists()
        or LEGACY_MACHINE_CODE_FIELD in raw_data
        or old_style_version
        or old_style_page_version
        or old_style_modules
        or default_release_newer
    ):
        try:
            VERSION_MATRIX_PATH.write_text(
                json.dumps(matrix, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass
    return matrix


def load_version_matrix() -> dict[str, Any]:
    source = VERSION_MATRIX_PATH if VERSION_MATRIX_PATH.exists() else DEFAULT_VERSION_MATRIX_PATH
    if source.exists():
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return normalize_version_matrix(data)
        except (OSError, json.JSONDecodeError):
            pass
    return normalize_version_matrix(default_version_matrix())


def vue_shell(request: Request, db: Session, vue_path: str = ""):
    return templates.TemplateResponse("vue_app.html", page_context(request, db, {"vue_path": vue_path}))


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return RedirectResponse(url="/static/speakeasy-mouth-logo.svg", status_code=302)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema_columns()
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    BOOK_COVER_DIR.mkdir(parents=True, exist_ok=True)
    ensure_version_matrix_file()
    with SessionLocal() as db:
        seed_daily_quotes(db)
        ensure_default_word_list(db)


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    return vue_shell(request, db)


@app.get("/booklearner", response_class=HTMLResponse)
def good_words_index(request: Request, db: Session = Depends(get_db)):
    return vue_shell(request, db, "booklearner")


@app.get("/booklearner/upload", response_class=HTMLResponse)
def good_words_upload_page(request: Request, db: Session = Depends(get_db)):
    return vue_shell(request, db, "booklearner/upload")


@app.get("/booklearner/quotes", response_class=HTMLResponse)
def good_words_quotes_page(request: Request, db: Session = Depends(get_db)):
    return vue_shell(request, db, "booklearner/quotes")


@app.get("/booklearner/detail/{analysis_id}", response_class=HTMLResponse)
def good_words_detail_page(analysis_id: int, request: Request, db: Session = Depends(get_db)):
    item = get_good_words_analysis(analysis_id)
    if not item:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return vue_shell(request, db, f"booklearner/detail/{analysis_id}")


@app.get("/newspaper", response_class=HTMLResponse)
def newspaper_page(request: Request, db: Session = Depends(get_db)):
    return vue_shell(request, db, "newspaper")


@app.get("/newspaper/{section_key}/{article_index}", response_class=HTMLResponse)
def newspaper_article_page(
    section_key: str,
    article_index: int,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        cached_json(
            db,
            cache_key=f"chinadaily:detail:{date.today().isoformat()}:{section_key}:{article_index}",
            ttl=timedelta(hours=6),
            producer=lambda: get_chinadaily_article(section_key, article_index),
        )
    except (ValueError, IndexError):
        raise HTTPException(status_code=404, detail="Article not found")
    return vue_shell(request, db, f"newspaper/{section_key}/{article_index}")


@app.get("/lists", response_class=HTMLResponse)
def word_lists_page(
    request: Request,
    image_matched: int = Query(default=0, ge=0),
    image_unmatched: int = Query(default=0, ge=0),
    image_failed: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return vue_shell(request, db, "lists")


async def batch_upload_word_images_result(
    word_list_id: int = Form(...),
    image_files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> dict:
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")

    words = get_words_for_list_sequence(db, word_list_id)
    return await apply_uploaded_images_to_words(words, image_files, db)


@app.post("/api/vue/lists/batch-images")
async def vue_batch_upload_word_images(
    word_list_id: int = Form(...),
    image_files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    result = await batch_upload_word_images_result(word_list_id, image_files, db)
    return {"ok": True, **result}


@app.get("/booklearner/", response_class=HTMLResponse, include_in_schema=False)
def booklearner_index_slash():
    return RedirectResponse(url="/booklearner", status_code=301)


@app.get("/好词好句", include_in_schema=False)
@app.get("/好词好句/", include_in_schema=False)
def good_words_redirect_index():
    return RedirectResponse(url="/booklearner", status_code=301)


@app.get("/booklearner/api/health")
def good_words_health():
    return {"ok": True, "service": "好词好句"}


@app.get("/booklearner/api/storage")
def good_words_storage():
    return get_good_words_storage_status()


@app.get("/booklearner/api/history")
def good_words_history():
    return {"items": list_recent_good_words_analyses()}


@app.get("/booklearner/api/featured")
def good_words_featured(
    limit: int = Query(default=12, ge=1, le=80),
    analysis_id: int | None = Query(default=None, ge=1),
):
    return {"items": list_featured_good_words_quotes(limit=limit, analysis_id=analysis_id)}


@app.get("/booklearner/api/history/{analysis_id}")
def good_words_history_detail(analysis_id: int):
    item = get_good_words_analysis(analysis_id)
    if not item:
        raise HTTPException(status_code=404, detail="记录不存在，或 MySQL 未启用。")
    return item


@app.post("/booklearner/api/clicked-word")
async def good_words_clicked_word(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求内容不是有效 JSON。")

    raw_analysis_id = payload.get("analysisId")
    try:
        analysis_id = int(raw_analysis_id) if raw_analysis_id else None
    except (TypeError, ValueError):
        analysis_id = None

    result = save_good_words_clicked_word(analysis_id, payload)
    if not result.get("saved"):
        raise HTTPException(status_code=400, detail=result.get("message") or "保存失败")
    return result


@app.get("/booklearner/api/suggest")
def good_words_suggest(q: str = ""):
    return {"items": suggest_good_words_books(q)}


@app.get("/booklearner/api/analyze")
def good_words_analyze(q: str = ""):
    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="请输入书名或作者名。")
    result = analyze_good_words_query(query)
    return result


@app.post("/booklearner/api/analyze-text")
async def good_words_analyze_text(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求内容不是有效 JSON。")

    source_text = str(payload.get("text", "")).strip()
    if len(source_text) < 300:
        raise HTTPException(status_code=400, detail="文本太短，至少粘贴 300 个字符。")

    title = str(payload.get("title", "")).strip() or "粘贴文本"
    author = str(payload.get("author", "")).strip()
    result = analyze_good_words_text(title=title, author=author, text=source_text)
    return result


@app.post("/booklearner/api/analyze-file")
async def good_words_analyze_file(
    title: str = Form(default=""),
    author: str = Form(default=""),
    file: UploadFile = File(...),
):
    content = await file.read()
    try:
        extracted_book = extract_book_file(file.filename or "", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    source_text = extracted_book["text"]

    if len(source_text) < 300:
        raise HTTPException(status_code=400, detail="书籍正文太短，至少需要 300 个字符。")

    book_title = title.strip() or Path(file.filename or "上传书籍").stem
    result = analyze_good_words_text(title=book_title, author=author.strip(), text=source_text)
    if extracted_book.get("cover_url"):
        result.setdefault("book", {})["coverUrl"] = extracted_book["cover_url"]
    return result


@app.post("/booklearner/api/book-preview")
async def good_words_book_preview(file: UploadFile = File(...)):
    content = await file.read()
    filename = file.filename or "上传书籍"
    suffix = Path(filename).suffix.lower()
    cover_url = None
    if suffix == ".epub":
        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                cover_url = save_first_epub_image(archive, filename)
        except zipfile.BadZipFile as exc:
            raise HTTPException(status_code=400, detail="EPUB 文件无法打开，请确认文件没有损坏。") from exc
    elif suffix != ".txt" and file.content_type != "text/plain":
        raise HTTPException(status_code=400, detail="当前支持 txt 和 epub 书籍文件。")
    return {
        "filename": filename,
        "title": Path(filename).stem,
        "coverUrl": cover_url,
    }


@app.post("/booklearner/api/save-analysis")
async def good_words_save_analysis(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求内容不是有效 JSON。")

    result = payload.get("result")
    if not isinstance(result, dict):
        raise HTTPException(status_code=400, detail="没有可保存的分析结果。")
    book = result.get("book") or {}
    query = str(payload.get("query") or book.get("title") or result.get("query") or "上传书籍").strip()
    storage = save_good_words_analysis(query=query, result=result)
    if not storage.get("saved"):
        raise HTTPException(status_code=400, detail=storage.get("message") or "保存失败")
    return {"ok": True, "storage": storage}


@app.post("/booklearner/api/word-list")
async def good_words_create_word_list(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求内容不是有效 JSON。")

    title = clean_list_name(str(payload.get("title") or "BookLearner 单词表"))
    vocabulary = payload.get("vocabulary") or []
    if not isinstance(vocabulary, list):
        raise HTTPException(status_code=400, detail="单词数据格式不正确。")

    word_list = WordList(name=title)
    db.add(word_list)
    db.commit()
    db.refresh(word_list)

    created = 0
    for item in vocabulary:
        if not isinstance(item, dict):
            continue
        word_text = " ".join(str(item.get("word") or "").strip().split())
        word_key = word_text.lower()
        if not word_text or not re.fullmatch(r"[a-z][a-z'-]{1,127}", word_key):
            continue

        word = db.scalar(select(Word).where(func.lower(Word.word) == word_key))
        if word:
            if word.word != word_text:
                word.word = word_text
            word.part_of_speech = word.part_of_speech or item.get("partOfSpeech")
            word.english_definition = word.english_definition or item.get("definition")
            word.english_example = word.english_example or item.get("example")
            word.note = word.note or item.get("memoryHint")
            word.enrichment_status = word.enrichment_status or "pending"
        else:
            word = Word(
                word=word_text,
                part_of_speech=(str(item.get("partOfSpeech") or "").strip() or None),
                english_definition=(str(item.get("definition") or "").strip() or None),
                english_example=(str(item.get("example") or "").strip() or None),
                note=(str(item.get("memoryHint") or "").strip() or None),
                source="BookLearner",
                enrichment_status="pending",
            )
            db.add(word)
            db.commit()
            db.refresh(word)

        link_word_to_list(db, word_list.id, word.id)
        created += 1

    db.commit()
    return {"ok": True, "word_list_id": word_list.id, "name": word_list.name, "count": created}


@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request, db: Session = Depends(get_db)):
    return vue_shell(request, db, "upload")


@app.get("/lists/{word_list_id}", response_class=HTMLResponse)
def list_detail(
    word_list_id: int,
    request: Request,
    delete_error: int = Query(default=0),
    db: Session = Depends(get_db),
):
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")
    return vue_shell(request, db, f"lists/{word_list_id}")


@app.get("/challenge/{word_list_id}", response_class=HTMLResponse)
def challenge_page(
    word_list_id: int,
    request: Request,
    daily_count: int = Query(default=20, ge=1, le=500),
    start_count: int | None = Query(default=None),
    session_correct: int = Query(default=0, ge=0),
    session_wrong: int = Query(default=0, ge=0),
    wrong_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")
    return vue_shell(request, db, f"challenge/{word_list_id}")


@app.get("/api/vue/home")
def vue_home_api(db: Session = Depends(get_db)):
    today = date.today()
    word_lists = regular_word_lists(db)
    cards = [serialize_word_list_card(word_list_card(db, word_list)) for word_list in word_lists]
    today_stat = db.scalar(select(ChallengeDailyStat).where(ChallengeDailyStat.stat_date == today))
    today_wrong_list = get_wrong_word_list(db, today)
    today_wrong_count = db.scalar(select(func.count(WrongWord.id)).where(WrongWord.wrong_date == today)) or 0
    today_wrong_words = db.execute(
        select(WrongWord, Word)
        .join(Word, Word.id == WrongWord.word_id)
        .where(WrongWord.wrong_date == today)
        .order_by(WrongWord.updated_at.desc(), WrongWord.id.desc())
        .limit(12)
    ).all()
    return {
        "today": today.isoformat(),
        "cards": cards,
        "featured_cards": cards[:4],
        "calendar": challenge_calendar(db),
        "stats": {
            "word_lists": len(word_lists),
            "words": db.scalar(select(func.count(Word.id))) or 0,
            "wrong_words": wrong_word_count(db),
            "today_correct": today_stat.correct_count if today_stat else 0,
            "today_wrong": today_stat.wrong_count if today_stat else 0,
            "today_total": (today_stat.correct_count + today_stat.wrong_count) if today_stat else 0,
            "today_wrong_count": today_wrong_count,
            "today_wrong_list_id": today_wrong_list.id if today_wrong_list else None,
            "today_wrong_words": [
                {"word": serialize_word(word), "wrong_count": wrong_word.wrong_count}
                for wrong_word, word in today_wrong_words
            ],
        },
    }


@app.get("/api/vue/shell")
def vue_shell_api(db: Session = Depends(get_db)):
    return serialize_shell_context({
        "app_name": settings.app_name,
        "daily_quote": get_daily_quote(db),
        "sidebar_challenges": sidebar_challenge_progress(db),
        "wrong_word_count": wrong_word_count(db),
    })


@app.get("/api/vue/lists")
def vue_lists_api(db: Session = Depends(get_db)):
    cards = [serialize_word_list_card(word_list_card(db, word_list)) for word_list in regular_word_lists(db)]
    return {"cards": cards}


@app.get("/api/vue/lists/{word_list_id}")
def vue_list_detail_api(word_list_id: int, db: Session = Depends(get_db)):
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")
    words = db.scalars(
        select(Word)
        .join(WordListItem, WordListItem.word_id == Word.id)
        .where(WordListItem.word_list_id == word_list_id)
        .order_by(WordListItem.id.asc())
    ).all()
    stats = challenge_counts_for_words(db, [word.id for word in words])
    return {
        "word_list": {"id": word_list.id, "name": word_list.name, "sequence_offset": word_list.sequence_offset},
        "challenge": challenge_state(db, word_list),
        "words": [
            {
                **serialize_word(word),
                "display_index": word_list.sequence_offset + index + 1,
                "detail_url": f"/words/{word.id}?edit=1&list_id={word_list.id}",
                "challenge_stats": stats.get(word.id, {"correct": 0, "wrong": 0}),
            }
            for index, word in enumerate(words)
        ],
    }


@app.get("/api/vue/wrong-words")
def vue_wrong_words_api(db: Session = Depends(get_db)):
    wrong_rows = db.execute(
        select(WrongWord, Word)
        .join(Word, Word.id == WrongWord.word_id)
        .order_by(WrongWord.wrong_date.desc(), WrongWord.updated_at.desc(), WrongWord.id.desc())
    ).all()
    groups: dict[str, dict[str, Any]] = {}
    for wrong_word, word in wrong_rows:
        day = (wrong_word.wrong_date or date.today()).isoformat()
        group = groups.setdefault(day, {"date": day, "count": 0, "wrong_total": 0, "cover_word": None, "words": []})
        group["count"] += 1
        group["wrong_total"] += wrong_word.wrong_count
        serialized_word = serialize_word(word)
        if not group["cover_word"] or (not group["cover_word"].get("image_url") and serialized_word.get("image_url")):
            group["cover_word"] = serialized_word
        group["words"].append({"word": serialized_word, "wrong_count": wrong_word.wrong_count})
    return {"groups": list(groups.values())}


@app.get("/api/vue/challenge-calendar/{day}")
def vue_challenge_day_api(day: str, db: Session = Depends(get_db)):
    challenge_date = parse_wrong_date(day)
    if not challenge_date:
        raise HTTPException(status_code=400, detail="Invalid date")
    return challenge_calendar_day_payload(db, challenge_date)


@app.get("/api/vue/words/{word_id}")
def vue_word_detail_api(
    word_id: int,
    edit: int = Query(default=0),
    list_id: int | None = Query(default=None),
    challenge_day: str | None = Query(default=None),
    challenge_status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    cleaned_error = friendly_enrichment_error(word.enrichment_error)
    if cleaned_error != word.enrichment_error:
        word.enrichment_error = cleaned_error
        db.add(word)
        db.commit()
        db.refresh(word)
    nav = word_navigation_context(db, word.id, list_id, challenge_day, challenge_status)
    nav_word_list = db.get(WordList, nav.get("list_id")) if nav.get("list_id") else None
    if nav_word_list:
        nav["word_list_name"] = nav_word_list.name
    audio_version = str(int(datetime.utcnow().timestamp()))
    return {
        "word": {
            **serialize_word(word),
            "alternate_spellings": word.alternate_spellings,
            "source": word.source,
            "note": word.note,
            "enrichment_error": word.enrichment_error,
            "image_locked": word.image_locked,
            "american_audio_locked": word.american_audio_locked,
            "british_audio_locked": word.british_audio_locked,
        },
        "can_edit": edit == 1,
        "audio_sources": {
            "us": word_audio_source(word, "us", audio_version),
            "gb": word_audio_source(word, "gb", audio_version),
        },
        "navigation": nav,
    }


def word_audio_source(word: Word, accent: str, audio_version: str | None = None) -> str:
    audio_url = word.british_audio_url if accent == "gb" else word.american_audio_url
    source = audio_url if is_local_audio_url(audio_url) else f"/tts?word={quote_plus(word.word)}&accent={accent}&v=2"
    if audio_version:
        separator = "&" if "?" in source else "?"
        return f"{source}{separator}av={audio_version}"
    return source


@app.post("/api/vue/words/{word_id}/field")
def vue_update_word_field(
    word_id: int,
    field: str = Form(...),
    value: str = Form(default=""),
    edit_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    allowed = {
        "alternate_spellings",
        "english_definition",
        "chinese_definition",
        "english_example",
    }
    if field not in allowed:
        raise HTTPException(status_code=400, detail="Invalid field")
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    next_value = value.strip() or None
    setattr(word, field, next_value)
    if field == "english_definition":
        word.english_definition_locked = True
    if field == "chinese_definition":
        word.chinese_definition_locked = True
    if field == "english_example":
        word.english_example_locked = True
    word.enrichment_error = None
    db.add(word)
    db.commit()
    return {"ok": True, "field": field, "value": next_value}


@app.post("/api/vue/words/{word_id}/refresh")
async def vue_refresh_word(
    word_id: int,
    edit_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    await enrich_word(db, word)
    return {"ok": True, "word": serialize_word(word)}


@app.get("/api/vue/newspaper")
def vue_newspaper_api(db: Session = Depends(get_db)):
    return cached_json(
        db,
        cache_key=f"chinadaily:list:{date.today().isoformat()}:6",
        ttl=timedelta(minutes=45),
        producer=lambda: load_chinadaily_articles(limit_per_feed=6),
        fallback={"sections": []},
    )


@app.get("/api/vue/newspaper/{section_key}/{article_index}")
def vue_newspaper_article_api(section_key: str, article_index: int, db: Session = Depends(get_db)):
    try:
        return cached_json(
            db,
            cache_key=f"chinadaily:detail:{date.today().isoformat()}:{section_key}:{article_index}",
            ttl=timedelta(hours=6),
            producer=lambda: get_chinadaily_article(section_key, article_index),
        )
    except (ValueError, IndexError):
        raise HTTPException(status_code=404, detail="Article not found")


@app.get("/api/vue/upload/options")
def vue_upload_options(db: Session = Depends(get_db)):
    return {
        "word_lists": [
            {"id": word_list.id, "name": word_list.name}
            for word_list in regular_word_lists(db)
        ]
    }


@app.post("/api/vue/upload")
async def vue_upload_excel(
    file: UploadFile = File(...),
    word_list_id: str = Form(default=""),
    word_list_name: str = Form(default=""),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        raise HTTPException(status_code=400, detail="请上传 .xlsx 格式的 Excel 文件")
    content = await file.read()
    preview = parse_preview_from_excel(content)
    preview_id = uuid4().hex
    preview["filename"] = file.filename
    preview["word_list_id"] = word_list_id
    preview["word_list_name"] = clean_list_name(word_list_name or Path(file.filename or "新单词表").stem)
    preview_path(preview_id).write_text(json.dumps(preview, ensure_ascii=False), encoding="utf-8")
    preview_excel_path(preview_id).write_bytes(content)
    return {"ok": True, "preview_id": preview_id, "preview": preview}


@app.get("/api/vue/upload/preview/{preview_id}")
def vue_upload_preview_api(
    preview_id: str,
    sheet_name: str = Query(default=""),
    word_list_id: str = Query(default=""),
    word_list_name: str = Query(default=""),
):
    excel_path = preview_excel_path(preview_id)
    if not excel_path.exists():
        raise HTTPException(status_code=404, detail="预览已过期，请重新上传 Excel")
    existing_preview: dict[str, Any] = {}
    path = preview_path(preview_id)
    if path.exists():
        existing_preview = json.loads(path.read_text(encoding="utf-8"))
    if sheet_name:
        preview = parse_preview_from_excel(excel_path.read_bytes(), sheet_name=sheet_name)
        preview["filename"] = existing_preview.get("filename", "Excel")
        preview["word_list_id"] = word_list_id or existing_preview.get("word_list_id", "")
        preview["word_list_name"] = clean_list_name(
            word_list_name or existing_preview.get("word_list_name") or Path(preview["filename"]).stem
        )
        path.write_text(json.dumps(preview, ensure_ascii=False), encoding="utf-8")
    elif existing_preview:
        preview = existing_preview
    else:
        preview = parse_preview_from_excel(excel_path.read_bytes())
        path.write_text(json.dumps(preview, ensure_ascii=False), encoding="utf-8")
    return {"preview_id": preview_id, "preview": preview}


@app.post("/api/vue/import-preview")
async def vue_import_preview(
    preview_id: str = Form(...),
    word_list_id: str = Form(default=""),
    word_list_name: str = Form(...),
    word_columns: list[str] = Form(default=[]),
    selected_rows: list[int] = Form(default=[]),
    selected_columns: list[str] = Form(default=[]),
    image_files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    path = preview_path(preview_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="预览已过期，请重新上传 Excel")
    preview = json.loads(path.read_text(encoding="utf-8"))
    selected_preview_rows = set(selected_rows) or {
        int(row.get("index", 0)) for row in preview.get("rows", [])
    }
    selected_preview_columns = set(selected_columns) or set(preview.get("columns", []))
    if not word_columns:
        word_columns = preview.get("inferred_word_columns") or [preview.get("inferred_word_column")]
        word_columns = [column for column in word_columns if column]
    rows = parse_words_from_preview(
        preview=preview,
        selected_row_indexes=selected_preview_rows,
        selected_columns=selected_preview_columns,
        word_columns=word_columns,
    )
    chunk_size = 500
    base_name = clean_list_name(word_list_name)
    word_ids: list[int] = []
    split_lists: list[WordList] = []
    if len(rows) > chunk_size:
        for chunk_index in range(0, len(rows), chunk_size):
            chunk_number = (chunk_index // chunk_size) + 1
            chunk_list = get_or_create_word_list_by_name(db, f"{base_name}-{chunk_number}")
            chunk_list.sequence_offset = chunk_index
            db.add(chunk_list)
            db.commit()
            split_lists.append(chunk_list)
            word_ids.extend(import_rows(rows[chunk_index : chunk_index + chunk_size], db, chunk_list))
        target_list = split_lists[0]
    else:
        target_list = get_or_create_word_list(db, word_list_id, base_name)
        if not word_list_id:
            target_list.sequence_offset = 0
            db.add(target_list)
            db.commit()
        word_ids = import_rows(rows, db, target_list)
    image_result = {"matched": 0, "unmatched": 0, "failed": 0}
    if image_files:
        imported_words = [word for word_id in word_ids if (word := db.get(Word, word_id))]
        image_result = await apply_uploaded_images_to_words(imported_words, image_files, db)
    if word_ids:
        start_enrichment_thread(word_ids)
    path.unlink(missing_ok=True)
    preview_excel_path(preview_id).unlink(missing_ok=True)
    return {
        "ok": True,
        "word_list_id": target_list.id,
        "word_list_name": target_list.name,
        "count": len(word_ids),
        "split_word_lists": [
            {"id": word_list.id, "name": word_list.name, "sequence_offset": word_list.sequence_offset}
            for word_list in split_lists
        ],
        "image_result": image_result,
    }


@app.get("/api/challenge/{word_list_id}/state")
def challenge_state_api(
    word_list_id: int,
    daily_count: int = Query(default=20, ge=1, le=500),
    start_count: int | None = Query(default=None),
    session_correct: int = Query(default=0, ge=0),
    session_wrong: int = Query(default=0, ge=0),
    wrong_date: str | None = Query(default=None),
    restart: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    return challenge_payload(
        db,
        word_list_id=word_list_id,
        daily_count=daily_count,
        start_count=start_count,
        session_correct=session_correct,
        session_wrong=session_wrong,
        wrong_date=wrong_date,
        restart=restart,
    )


@app.post("/api/challenge/{word_list_id}/answer")
def challenge_answer_api(
    word_list_id: int,
    action: str = Form(default="known"),
    daily_count: int = Form(default=20),
    start_count: int = Form(default=0),
    session_correct: int = Form(default=0),
    session_wrong: int = Form(default=0),
    spelling: str = Form(default=""),
    wrong_date: str = Form(default=""),
    db: Session = Depends(get_db),
):
    result = apply_challenge_answer(
        db,
        word_list_id=word_list_id,
        action=action,
        daily_count=daily_count,
        start_count=start_count,
        session_correct=session_correct,
        session_wrong=session_wrong,
        spelling=spelling,
        wrong_date=wrong_date,
    )
    query = {
        "daily_count": result["daily_count"],
        "start_count": result["start_count"],
        "session_correct": result["session_correct"],
        "session_wrong": result["session_wrong"],
    }
    if result["wrong_date"]:
        query["wrong_date"] = result["wrong_date"].isoformat()
    next_state = challenge_payload(
        db,
        word_list_id=word_list_id,
        daily_count=result["daily_count"],
        start_count=result["start_count"],
        session_correct=result["session_correct"],
        session_wrong=result["session_wrong"],
        wrong_date=result["wrong_date"].isoformat() if result["wrong_date"] else None,
    )
    return {"ok": True, "query": query, "state": next_state, "answer": result.get("answer")}


@app.get("/wrong-words", response_class=HTMLResponse)
def wrong_words_page(request: Request, db: Session = Depends(get_db)):
    return vue_shell(request, db, "wrong-words")


@app.get("/challenge-calendar/{day}", response_class=HTMLResponse)
def challenge_calendar_detail_page(day: str, request: Request, db: Session = Depends(get_db)):
    challenge_date = parse_wrong_date(day)
    if not challenge_date:
        raise HTTPException(status_code=404, detail="Date not found")
    return vue_shell(request, db, f"challenge-calendar/{day}")


def apply_challenge_answer(
    db: Session,
    word_list_id: int,
    action: str,
    daily_count: int,
    start_count: int,
    session_correct: int,
    session_wrong: int,
    spelling: str,
    wrong_date: str,
) -> dict[str, Any]:
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")

    words = get_words_for_list(db, word_list_id)
    progress = get_or_create_challenge_progress(db, word_list_id)
    total = len(words)
    wrong_date_value = parse_wrong_date(wrong_date)
    answer_feedback = None

    if action == "reset":
        progress.current_index = 0
        progress.completed_count = 0
        session_correct = 0
        session_wrong = 0
    elif total:
        current_word = words[progress.current_index] if 0 <= progress.current_index < total else None
        if action == "spell" and current_word:
            typed = normalize_spelling_answer(spelling)
            expected = spelling_answer_options(current_word)
            action = "known" if typed in expected else "wrong"
            answer_feedback = {
                "is_correct": action == "known",
                "typed": spelling,
                "correct_spelling": current_word.word,
                "accepted_spellings": sorted(expected),
            }
            record_spelling_attempt(
                db,
                word=current_word,
                word_list_id=word_list_id,
                typed_spelling=spelling,
                normalized_spelling=typed,
                expected_spellings=expected,
                is_correct=action == "known",
            )
        if action == "wrong" and current_word:
            record_wrong_word(db, current_word.id)
        if action == "known":
            if current_word:
                clear_wrong_word_if_passed(db, current_word.id, wrong_date_value)
        if action in {"known", "wrong"}:
            progress.completed_count = min(progress.completed_count + 1, total)
            if action == "known":
                session_correct += 1
            else:
                session_wrong += 1
            if current_word:
                record_challenge_daily_result(
                    db,
                    is_correct=action == "known",
                    word_id=current_word.id,
                    word_list_id=word_list_id,
                )
        if progress.completed_count < total:
            progress.current_index = (progress.current_index + 1) % total
        else:
            progress.current_index = max(total - 1, 0)

    db.add(progress)
    db.commit()
    daily_count = min(max(daily_count, 1), 500)
    start_count = max(start_count, 0)
    session_correct = max(session_correct, 0)
    session_wrong = max(session_wrong, 0)
    return {
        "daily_count": daily_count,
        "start_count": start_count,
        "session_correct": session_correct,
        "session_wrong": session_wrong,
        "wrong_date": wrong_date_value,
        "answer": answer_feedback,
    }


def challenge_payload(
    db: Session,
    word_list_id: int,
    daily_count: int,
    start_count: int | None,
    session_correct: int,
    session_wrong: int,
    wrong_date: str | None,
    restart: bool = False,
) -> dict[str, Any]:
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")
    wrong_date_value = parse_wrong_date(wrong_date)

    words = get_words_for_list(db, word_list_id)
    progress = get_or_create_challenge_progress(db, word_list_id)
    total = len(words)
    if restart:
        restart_index = min(max(start_count or 0, 0), max(total - 1, 0))
        progress.completed_count = restart_index
        progress.current_index = restart_index
    else:
        historical_completed = (
            challenged_word_count_for_list(db, word_list_id, total)
            if not progress.completed_rounds
            else 0
        )
        progress.completed_count = min(
            max(progress.completed_count, historical_completed),
            total,
        )
        progress.current_index = min(progress.current_index, max(total - 1, 0))
    db.add(progress)
    db.commit()

    start_count = progress.completed_count if start_count is None else start_count
    start_count = min(max(start_count, 0), total)
    daily_count = min(max(daily_count, 1), max(total, 1))
    daily_target = min(total, start_count + daily_count)
    daily_total = max(0, daily_target - start_count)
    session_correct = max(session_correct, 0)
    session_wrong = max(session_wrong, 0)
    session_answered = min(session_correct + session_wrong, daily_total) if daily_total else 0
    daily_done = session_answered
    daily_remaining = max(0, daily_total - session_answered)
    is_daily_complete = bool(total and daily_total and session_answered >= daily_total)

    current_word = None if is_daily_complete or progress.completed_count >= total or not words else words[progress.current_index]
    challenge_audio_sources = None
    challenge_image_url = None
    masked_example = None
    if current_word:
        audio_version = str(int(datetime.utcnow().timestamp()))
        challenge_audio_sources = {
            "us": word_audio_source(current_word, "us", audio_version),
            "gb": word_audio_source(current_word, "gb", audio_version),
        }
        challenge_image_url = f"/words/{current_word.id}/image-view" if current_word.image_url else None
        masked_example = mask_word_in_text(
            current_word.english_example,
            current_word.word,
            current_word.alternate_spellings,
        )

    state = challenge_state(db, word_list)
    today_challenge = {
        "daily_count": daily_count,
        "start_count": start_count,
        "target": daily_target,
        "done": daily_done,
        "total": daily_total,
        "percent": round((daily_done / daily_total) * 100) if daily_total else 100,
        "is_complete": is_daily_complete,
        "all_complete": bool(total and progress.completed_count >= total),
        "correct": session_correct,
        "wrong": session_wrong,
        "answered": session_answered,
        "remaining": daily_remaining,
        "accuracy": round((session_correct / session_answered) * 100) if session_answered else 0,
    }
    return {
        "word_list": {"id": word_list.id, "name": word_list.name},
        "current_word": serialize_challenge_word(current_word),
        "progress": {
            "current_index": progress.current_index,
            "completed_count": progress.completed_count,
            "completed_rounds": progress.completed_rounds,
        },
        "challenge": state,
        "today_challenge": today_challenge,
        "challenge_audio_sources": challenge_audio_sources,
        "challenge_image_url": challenge_image_url,
        "masked_example": masked_example,
        "wrong_date": wrong_date_value.isoformat() if wrong_date_value else None,
    }


def serialize_challenge_word(word: Word | None) -> dict[str, Any] | None:
    if not word:
        return None
    return {
        "id": word.id,
        "word": word.word,
        "phonetic": word.phonetic,
        "part_of_speech": word.part_of_speech,
        "english_definition": word.english_definition,
        "chinese_definition": word.chinese_definition,
        "english_example": word.english_example,
    }


def serialize_word(word: Word) -> dict[str, Any]:
    has_audio = is_local_audio_url(word.american_audio_url) or is_local_audio_url(word.british_audio_url)
    has_playable_audio = has_audio or bool((word.word or "").strip())
    return {
        "id": word.id,
        "word": word.word,
        "phonetic": word.phonetic,
        "part_of_speech": word.part_of_speech,
        "english_definition": word.english_definition,
        "chinese_definition": word.chinese_definition,
        "english_example": word.english_example,
        "image_url": word.image_url,
        "has_audio": has_audio,
        "has_playable_audio": has_playable_audio,
    }


def serialize_word_list_card(card: dict[str, Any]) -> dict[str, Any]:
    word_list = card["list"]
    cover_word = card.get("cover_word")
    return {
        "list": {"id": word_list.id, "name": word_list.name},
        "count": card["count"],
        "cover_word": serialize_word(cover_word) if cover_word else None,
        "challenge": card["challenge"],
    }


def challenge_calendar_day_payload(db: Session, challenge_date: date) -> dict:
    stat = db.scalar(select(ChallengeDailyStat).where(ChallengeDailyStat.stat_date == challenge_date))
    detail_rows = db.execute(
        select(ChallengeDailyWord, Word, WordList)
        .join(Word, Word.id == ChallengeDailyWord.word_id)
        .outerjoin(WordList, WordList.id == ChallengeDailyWord.word_list_id)
        .where(ChallengeDailyWord.challenge_date == challenge_date)
        .order_by(ChallengeDailyWord.updated_at.asc(), ChallengeDailyWord.id.asc())
    ).all()

    words = [
        {
            "id": word.id,
            "word": word.word,
            "status": detail.last_result,
            "correct_count": detail.correct_count,
            "wrong_count": detail.wrong_count,
            "word_list_id": word_list.id if word_list else None,
            "word_list_name": word_list.name if word_list else "",
            "image_url": word.image_url,
            "phonetic": word.phonetic,
            "part_of_speech": word.part_of_speech,
            "english_definition": word.english_definition,
            "chinese_definition": word.chinese_definition,
        }
        for detail, word, word_list in detail_rows
    ]

    correct = stat.correct_count if stat else sum(item["correct_count"] for item in words)
    wrong = stat.wrong_count if stat else sum(item["wrong_count"] for item in words)
    recovery_note = ""
    if not words and stat and (stat.correct_count or stat.wrong_count):
        recovered_wrong_words = []
        wrong_rows = db.execute(
            select(WrongWord, Word)
            .join(Word, Word.id == WrongWord.word_id)
            .where(WrongWord.wrong_date == challenge_date)
            .order_by(WrongWord.updated_at.desc(), WrongWord.id.desc())
            .limit(stat.wrong_count or 12)
        ).all()
        seen_word_ids = set()
        for wrong_word, word in wrong_rows:
            if word.id in seen_word_ids:
                continue
            seen_word_ids.add(word.id)
            recovered_wrong_words.append(
                {
                    "id": word.id,
                    "word": word.word,
                    "status": "wrong",
                    "correct_count": 0,
                    "wrong_count": wrong_word.wrong_count,
                    "word_list_id": None,
                    "word_list_name": "\u5f53\u65e5\u751f\u8bcd\u672c",
                    "image_url": word.image_url,
                    "phonetic": word.phonetic,
                    "part_of_speech": word.part_of_speech,
                    "english_definition": word.english_definition,
                    "chinese_definition": word.chinese_definition,
                }
            )

        recovered_correct_words = []
        if stat.correct_count:
            progress_rows = db.execute(
                select(ChallengeProgress, WordList)
                .join(WordList, WordList.id == ChallengeProgress.word_list_id)
                .where(ChallengeProgress.completed_count > 0)
                .order_by(ChallengeProgress.updated_at.desc(), ChallengeProgress.id.desc())
            ).all()
            progress_rows = sorted(
                progress_rows,
                key=lambda row: (
                    row[0].completed_count == stat.correct_count,
                    row[0].completed_count >= stat.correct_count,
                    row[0].updated_at or row[0].created_at,
                ),
                reverse=True,
            )
            for progress, word_list in progress_rows:
                limit_count = max(stat.correct_count + stat.wrong_count, progress.completed_count, 1)
                candidate_rows = db.execute(
                    select(WordListItem, Word)
                    .join(Word, Word.id == WordListItem.word_id)
                    .where(WordListItem.word_list_id == progress.word_list_id)
                    .order_by(WordListItem.id.asc())
                    .limit(limit_count)
                ).all()
                for _item, word in candidate_rows:
                    if word.id in seen_word_ids:
                        continue
                    seen_word_ids.add(word.id)
                    recovered_correct_words.append(
                        {
                            "id": word.id,
                            "word": word.word,
                            "status": "correct",
                            "correct_count": 1,
                            "wrong_count": 0,
                            "word_list_id": word_list.id,
                            "word_list_name": f"{word_list.name}\uff08\u65e7\u8bb0\u5f55\u6062\u590d\uff09",
                            "image_url": word.image_url,
                            "phonetic": word.phonetic,
                            "part_of_speech": word.part_of_speech,
                            "english_definition": word.english_definition,
                            "chinese_definition": word.chinese_definition,
                        }
                    )
                    if len(recovered_correct_words) >= stat.correct_count:
                        break
                if len(recovered_correct_words) >= stat.correct_count:
                    break

        words.extend(recovered_correct_words[: stat.correct_count])
        words.extend(recovered_wrong_words)
        recovery_note = (
            "\u8fd9\u4e00\u5929\u7684\u65e7\u6311\u6218\u8bb0\u5f55\u53ea\u4fdd\u5b58\u4e86\u603b\u6570\uff0c"
            "\u7b54\u5bf9\u5355\u8bcd\u5df2\u6309\u5f53\u65f6\u6311\u6218\u8fdb\u5ea6\u5c3d\u91cf\u6062\u590d\uff0c"
            "\u9519\u8bef\u5355\u8bcd\u5df2\u4ece\u5f53\u65e5\u751f\u8bcd\u672c\u6062\u590d\uff1b"
            "\u4e4b\u540e\u65b0\u7684\u6311\u6218\u4f1a\u81ea\u52a8\u5b8c\u6574\u8bb0\u5f55\u6bcf\u4e2a\u5355\u8bcd\u3002"
        )
    wrong_word_list = get_wrong_word_list(db, challenge_date)
    return {
        "date": challenge_date.isoformat(),
        "total": correct + wrong,
        "correct": correct,
        "wrong": wrong,
        "wrong_word_list_id": wrong_word_list.id if wrong_word_list else None,
        "words": words,
        "has_detail_rows": bool(detail_rows),
        "recovery_note": recovery_note,
    }


@app.get("/api/challenge-calendar/day")
def challenge_calendar_day(day: str = Query(...), db: Session = Depends(get_db)):
    challenge_date = parse_wrong_date(day)
    if not challenge_date:
        raise HTTPException(status_code=400, detail="Invalid date")
    return challenge_calendar_day_payload(db, challenge_date)


@app.post("/api/vue/lists/{word_list_id}/rename")
def rename_word_list(
    word_list_id: int,
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")
    word_list.name = clean_list_name(name)
    db.add(word_list)
    db.commit()
    return {"ok": True, "name": word_list.name}


def delete_word_list_record(word_list_id: int, password: str, db: Session) -> None:
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")
    if password != settings.list_delete_password:
        raise HTTPException(status_code=403, detail="删除密码不正确")

    word_ids = [
        row[0]
        for row in db.execute(
            select(WordListItem.word_id).where(WordListItem.word_list_id == word_list_id)
        ).all()
    ]
    exclusive_word_ids = []
    for word_id in word_ids:
        linked_count = db.scalar(select(func.count(WordListItem.id)).where(WordListItem.word_id == word_id)) or 0
        if linked_count <= 1:
            exclusive_word_ids.append(word_id)

    db.execute(delete(ChallengeProgress).where(ChallengeProgress.word_list_id == word_list_id))
    db.execute(delete(WordListItem).where(WordListItem.word_list_id == word_list_id))
    if exclusive_word_ids:
        db.execute(delete(WrongWord).where(WrongWord.word_id.in_(exclusive_word_ids)))
        db.execute(delete(Word).where(Word.id.in_(exclusive_word_ids)))
    db.delete(word_list)
    db.commit()


@app.post("/api/vue/lists/{word_list_id}/delete")
def vue_delete_word_list(
    word_list_id: int,
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    delete_word_list_record(word_list_id, password, db)
    return {"ok": True}


@app.post("/api/vue/words/{word_id}/image")
async def replace_word_image(
    word_id: int,
    file: UploadFile = File(...),
    edit_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="图片文件为空")
    if len(content) > 12 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片不能超过 12MB")

    previous_url = word.image_url
    try:
        word.image_url = store_uploaded_word_image(word.word, content, IMAGE_DIR)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"图片处理失败: {exc}") from exc

    word.image_locked = True
    word.enrichment_error = None
    db.add(word)
    db.commit()
    if previous_url != word.image_url:
        remove_local_image(previous_url, IMAGE_DIR)
    return {"ok": True, "word": word.word, "image_url": word.image_url}


@app.post("/api/vue/public-assets/ai-image")
async def generate_public_asset_image(
    edit_token: str = Form(default=""),
    name: str = Form(...),
    prompt: str = Form(...),
    model: str = Form(default="wan2.7-image-pro"),
):
    require_word_write_access(edit_token)
    selected_model = (model or "wan2.7-image-pro").strip()
    clean_name = " ".join((name or "").split())[:80]
    clean_prompt = " ".join((prompt or "").split())
    if not clean_name:
        raise HTTPException(status_code=400, detail="公共图片名称不能为空")
    if len(clean_prompt) < 8:
        raise HTTPException(status_code=400, detail="公共图片提示词太短")
    try:
        content = await generate_dashscope_prompt_image(
            api_key=settings.dashscope_api_key,
            endpoint=settings.dashscope_image_endpoint,
            task_endpoint=settings.dashscope_task_endpoint,
            poll_seconds=settings.dashscope_image_poll_seconds,
            timeout_seconds=settings.dashscope_image_timeout_seconds,
            model=selected_model,
            prompt=clean_prompt,
        )
    except RuntimeError as exc:
        detail = str(exc)
        if "not configured" in detail:
            raise HTTPException(status_code=400, detail=detail) from exc
        if is_ai_quota_error(detail):
            raise HTTPException(status_code=402, detail="额度已经用完") from exc
        raise HTTPException(status_code=502, detail=f"公共图片生成失败: {detail}") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:400] if exc.response is not None else str(exc)
        if is_ai_quota_error(detail):
            raise HTTPException(status_code=402, detail="额度已经用完") from exc
        raise HTTPException(status_code=502, detail=f"公共图片生成失败: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"公共图片生成失败: {exc}") from exc

    suffix = public_asset_extension(content)
    filename = f"{public_asset_slug(clean_name)}-{uuid4().hex[:8]}{suffix}"
    target = PUBLIC_ASSET_DIR / filename
    target.write_bytes(content)
    return {
        "ok": True,
        "name": clean_name,
        "model": selected_model,
        "image_url": f"/media/generated-assets/{filename}",
    }


@app.post("/api/vue/words/{word_id}/ai-image")
async def generate_ai_word_image(
    word_id: int,
    edit_token: str = Form(default=""),
    provider: str = Form(default=""),
    model: str = Form(default=""),
    theme: str = Form(default=""),
    style: str = Form(default=""),
    meaning: str = Form(default=""),
    commit: str = Form(default="1"),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    selected_provider = (provider or settings.ai_image_provider).strip()
    selected_model = (model or "").strip()
    selected_openai_model = settings.openai_image_model
    selected_tencent_action = settings.tencent_hunyuan_image_action
    selected_dashscope_model = selected_model or "wan2.7-image-pro"
    if selected_provider == "openai" and selected_model:
        selected_openai_model = selected_model
    elif selected_provider == "dashscope" and selected_model:
        selected_dashscope_model = selected_model
    elif selected_provider == "tencent_hunyuan" and selected_model:
        selected_tencent_action = selected_model

    previous_url = word.image_url
    try:
        content = await generate_word_image(
            provider=selected_provider,
            word=word.word,
            english_definition=word.english_definition,
            chinese_definition=meaning or word.chinese_definition,
            theme=theme,
            style=style,
            openai_api_key=settings.openai_api_key,
            openai_model=selected_openai_model,
            dashscope_api_key=settings.dashscope_api_key,
            dashscope_endpoint=settings.dashscope_image_endpoint,
            dashscope_task_endpoint=settings.dashscope_task_endpoint,
            dashscope_poll_seconds=settings.dashscope_image_poll_seconds,
            dashscope_timeout_seconds=settings.dashscope_image_timeout_seconds,
            dashscope_model=selected_dashscope_model,
            tencent_secret_id=settings.tencentcloud_secret_id,
            tencent_secret_key=settings.tencentcloud_secret_key,
            tencent_region=settings.tencentcloud_region,
            tencent_action=selected_tencent_action,
        )
        image_url = store_uploaded_word_image(word.word, content, IMAGE_DIR)
    except RuntimeError as exc:
        detail = str(exc)
        if "not configured" in detail:
            raise HTTPException(status_code=400, detail=detail) from exc
        if is_ai_quota_error(detail):
            raise HTTPException(status_code=402, detail="额度已经用完") from exc
        raise HTTPException(status_code=502, detail=f"AI 生图失败: {detail}") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:400] if exc.response is not None else str(exc)
        if is_ai_quota_error(detail):
            raise HTTPException(status_code=402, detail="额度已经用完") from exc
        raise HTTPException(status_code=502, detail=f"AI 生图失败: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI 生图失败: {exc}") from exc

    should_commit = commit not in {"0", "false", "False", "no"}
    if should_commit:
        word.image_url = image_url
        word.image_locked = True
        word.enrichment_error = None
        db.add(word)
        db.commit()
        if previous_url != word.image_url:
            remove_local_image(previous_url, IMAGE_DIR)
    return {
        "ok": True,
        "word": word.word,
        "image_url": image_url,
        "provider": selected_provider,
        "model": selected_openai_model
        if selected_provider == "openai"
        else selected_dashscope_model
        if selected_provider == "dashscope"
        else selected_tencent_action,
        "committed": should_commit,
    }


@app.post("/api/vue/words/{word_id}/image-candidates")
async def word_image_candidates(
    word_id: int,
    edit_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    try:
        images = await ImageClient().find_images(word.word, limit=8)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"网络找图失败: {exc}") from exc
    return {"ok": True, "word": word.word, "images": images}


@app.post("/api/vue/words/{word_id}/network-image")
async def replace_word_image_from_network(
    word_id: int,
    edit_token: str = Form(default=""),
    image_url: str = Form(default=""),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    try:
        found_image_url = image_url.strip() or await ImageClient().find_image(word.word)
        if not found_image_url:
            raise RuntimeError("没有找到可用图片")
        local_url = await store_word_image(word.word, found_image_url, IMAGE_DIR)
        if not local_url:
            raise RuntimeError("图片下载失败")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"网络找图失败: {exc}") from exc

    previous_url = word.image_url
    word.image_url = local_url
    word.image_locked = True
    word.enrichment_error = None
    db.add(word)
    db.commit()
    if previous_url != word.image_url:
        remove_local_image(previous_url, IMAGE_DIR)
    return {"ok": True, "word": word.word, "image_url": word.image_url}


@app.post("/api/vue/words/{word_id}/sync-image")
async def sync_word_image(word_id: int, db: Session = Depends(get_db)):
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    return await sync_word_image_record(db, word)


async def sync_word_image_record(db: Session, word: Word) -> dict:
    if is_local_media_url(word.image_url):
        return {"ok": True, "id": word.id, "word": word.word, "image_url": word.image_url, "skipped": True}

    if word.image_locked:
        return {"ok": True, "id": word.id, "word": word.word, "image_url": word.image_url, "skipped": True, "locked": True}

    candidates = []
    if word.image_url:
        candidates.append(word.image_url)

    try:
        found_image_url = await ImageClient().find_image(word.word)
        if found_image_url:
            candidates.append(found_image_url)
    except Exception as exc:
        word.enrichment_error = f"图片搜索失败: {exc}"

    errors: list[str] = []
    for image_url in candidates:
        try:
            local_url = await store_word_image(word.word, image_url, IMAGE_DIR)
            if local_url:
                word.image_url = local_url
                word.enrichment_error = None
                db.add(word)
                db.commit()
                return {"ok": True, "id": word.id, "word": word.word, "image_url": local_url, "skipped": False}
        except Exception as exc:
            errors.append(str(exc))

    word.enrichment_error = "图片同步失败: " + ("; ".join(errors[:2]) or "未找到可用图片")
    db.add(word)
    db.commit()
    return {"ok": False, "id": word.id, "word": word.word, "error": word.enrichment_error}


@app.post("/api/vue/lists/{word_list_id}/sync-images/start")
def start_list_image_sync(word_list_id: int, db: Session = Depends(get_db)):
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")

    pending_words = get_pending_image_words(db, word_list_id)
    job_id = uuid4().hex
    job = {
        "id": job_id,
        "word_list_id": word_list_id,
        "status": "queued",
        "total": len(pending_words),
        "done": 0,
        "failed": 0,
        "current_word": "",
        "results": [],
        "message": "图片同步任务已创建",
    }
    with IMAGE_SYNC_LOCK:
        IMAGE_SYNC_JOBS[job_id] = job

    Thread(target=run_image_sync_job, args=(job_id, word_list_id), daemon=True).start()
    return job


@app.get("/api/vue/lists/{word_list_id}/sync-images/{job_id}")
def list_image_sync_status(word_list_id: int, job_id: str):
    with IMAGE_SYNC_LOCK:
        job = IMAGE_SYNC_JOBS.get(job_id)
        if not job or job.get("word_list_id") != word_list_id:
            raise HTTPException(status_code=404, detail="Sync job not found")
        return dict(job)


@app.get("/words/{word_id}/image-view")
def word_image_view(word_id: int, db: Session = Depends(get_db)):
    word = db.get(Word, word_id)
    if not word or not word.image_url:
        raise HTTPException(status_code=404, detail="Image not found")
    return RedirectResponse(url=word.image_url, status_code=302)


@app.post("/api/vue/words/{word_id}/audio-options")
async def word_audio_options(
    word_id: int,
    accent: str = Form(...),
    edit_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    if accent not in {"us", "gb"}:
        raise HTTPException(status_code=400, detail="Invalid accent")
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    options = []
    current_audio_url = word.british_audio_url if accent == "gb" else word.american_audio_url
    if is_local_audio_url(current_audio_url):
        options.append({
            "label": "当前英式音源" if accent == "gb" else "当前美式音源",
            "url": current_audio_url,
        })

    for candidate in await audio_candidates_with_dictionary(word.word, accent):
        try:
            local_url = await store_audio_candidate(word.word, accent, candidate["key"], candidate["url"], AUDIO_DIR)
        except Exception:
            local_url = None
        if local_url and all(option["url"] != local_url for option in options):
            options.append({"label": candidate["label"], "url": local_url})

    if not options:
        return {"ok": False, "word": word.word, "accent": accent, "options": [], "error": "没有找到可用音频"}
    return {"ok": True, "word": word.word, "accent": accent, "options": options}


@app.post("/api/vue/words/{word_id}/audio-choice")
async def word_audio_choice(
    word_id: int,
    accent: str = Form(...),
    audio_url: str = Form(...),
    edit_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    if accent not in {"us", "gb"}:
        raise HTTPException(status_code=400, detail="Invalid accent")
    if not is_local_audio_url(audio_url):
        raise HTTPException(status_code=400, detail="请先选择服务器上的音频")

    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    if accent == "gb":
        word.british_audio_url = audio_url
        word.british_audio_locked = True
    else:
        word.american_audio_url = audio_url
        word.american_audio_locked = True
    word.enrichment_error = None
    db.add(word)
    db.commit()
    return {"ok": True, "word": word.word, "accent": accent, "audio_url": audio_url}


@app.post("/api/vue/words/{word_id}/recorded-audio")
async def word_recorded_audio(
    word_id: int,
    accent: str = Form(...),
    audio_file: UploadFile = File(...),
    edit_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    if accent not in {"us", "gb"}:
        raise HTTPException(status_code=400, detail="Invalid accent")

    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    content = await audio_file.read()
    if len(content) < 1000:
        raise HTTPException(status_code=400, detail="录音太短，请重新录制。")
    if len(content) > 12 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="录音文件太大，请控制在 12MB 以内。")

    content_type = (audio_file.content_type or "").lower()
    suffix = recorded_audio_suffix(content_type, audio_file.filename or "")
    safe_word = re.sub(r"[^a-zA-Z0-9_-]+", "-", word.word.lower()).strip("-") or "word"
    target = AUDIO_DIR / f"{safe_word}-{accent}-recorded-{uuid4().hex[:8]}{suffix}"
    target.write_bytes(content)
    audio_url = f"/media/audio/{target.name}"

    if accent == "gb":
        word.british_audio_url = audio_url
        word.british_audio_locked = True
    else:
        word.american_audio_url = audio_url
        word.american_audio_locked = True
    word.enrichment_error = None
    db.add(word)
    db.commit()
    return {"ok": True, "word": word.word, "accent": accent, "audio_url": audio_url}


@app.post("/api/vue/words/{word_id}/ai-audio")
async def word_ai_audio(
    word_id: int,
    accent: str = Form(...),
    voice_gender: str = Form(default="female"),
    commit: str = Form(default="1"),
    edit_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    if accent not in {"us", "gb"}:
        raise HTTPException(status_code=400, detail="Invalid accent")
    if voice_gender not in {"female", "male"}:
        raise HTTPException(status_code=400, detail="Invalid voice gender")

    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    try:
        audio_url = await generate_word_ai_audio(
            provider=settings.ai_tts_provider,
            api_key=settings.openai_api_key,
            model=settings.openai_tts_model,
            word=word.word,
            accent=accent,
            voice_gender=voice_gender,
            audio_dir=AUDIO_DIR,
            voice_us=settings.openai_tts_voice_us,
            voice_gb=settings.openai_tts_voice_gb,
            aliyun_appkey=settings.aliyun_nls_appkey,
            aliyun_token=settings.aliyun_nls_token,
            aliyun_access_key_id=settings.aliyun_access_key_id,
            aliyun_access_key_secret=settings.aliyun_access_key_secret,
            aliyun_token_region=settings.aliyun_token_region,
            aliyun_token_endpoint=settings.aliyun_token_endpoint,
            aliyun_gateway=settings.aliyun_tts_gateway,
            aliyun_format=settings.aliyun_tts_format,
            aliyun_sample_rate=settings.aliyun_tts_sample_rate,
            aliyun_voice_us=settings.aliyun_tts_voice_us,
            aliyun_voice_gb=settings.aliyun_tts_voice_gb,
            aliyun_voice_us_female=settings.aliyun_tts_voice_us_female,
            aliyun_voice_us_male=settings.aliyun_tts_voice_us_male,
            aliyun_voice_gb_female=settings.aliyun_tts_voice_gb_female,
            aliyun_voice_gb_male=settings.aliyun_tts_voice_gb_male,
            aliyun_volume=settings.aliyun_tts_volume,
            aliyun_speech_rate=settings.aliyun_tts_speech_rate,
            aliyun_pitch_rate=settings.aliyun_tts_pitch_rate,
        )
    except RuntimeError as exc:
        detail = str(exc)
        if "not configured" in detail:
            raise HTTPException(status_code=400, detail=detail) from exc
        raise HTTPException(status_code=502, detail=f"AI 朗读失败: {detail}") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:400] if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"AI 朗读失败: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI 朗读失败: {exc}") from exc

    should_commit = commit not in {"0", "false", "False", "no"}
    if should_commit:
        if accent == "gb":
            word.british_audio_url = audio_url
            word.british_audio_locked = True
        else:
            word.american_audio_url = audio_url
            word.american_audio_locked = True
        word.enrichment_error = None
        db.add(word)
        db.commit()
    return {
        "ok": True,
        "word": word.word,
        "accent": accent,
        "voice_gender": voice_gender,
        "committed": should_commit,
        "audio_url": audio_url,
    }


@app.get("/words/{word_id}", response_class=HTMLResponse)
def word_detail(
    word_id: int,
    request: Request,
    edit: int = Query(default=0),
    list_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    cleaned_error = friendly_enrichment_error(word.enrichment_error)
    if cleaned_error != word.enrichment_error:
        word.enrichment_error = cleaned_error
        db.add(word)
        db.commit()
    return vue_shell(request, db, f"words/{word_id}")


@app.get("/upload/preview/{preview_id}", response_class=HTMLResponse)
def upload_preview_sheet(
    preview_id: str,
    request: Request,
    sheet_name: str = Query(default=""),
    word_list_id: str = Query(default=""),
    word_list_name: str = Query(default=""),
    db: Session = Depends(get_db),
):
    excel_path = preview_excel_path(preview_id)
    if not excel_path.exists():
        raise HTTPException(status_code=404, detail="预览已过期，请重新上传 Excel")

    existing_preview: dict[str, Any] = {}
    path = preview_path(preview_id)
    if path.exists():
        existing_preview = json.loads(path.read_text(encoding="utf-8"))

    preview = parse_preview_from_excel(excel_path.read_bytes(), sheet_name=sheet_name or None)
    preview["filename"] = existing_preview.get("filename", "Excel")
    preview["word_list_id"] = word_list_id or existing_preview.get("word_list_id", "")
    preview["word_list_name"] = clean_list_name(
        word_list_name or existing_preview.get("word_list_name") or Path(preview["filename"]).stem
    )
    path.write_text(json.dumps(preview, ensure_ascii=False), encoding="utf-8")

    return vue_shell(request, db, f"upload/preview/{preview_id}")


def import_rows(rows: list[dict], db: Session, word_list: WordList) -> list[int]:
    created = updated = skipped = 0
    errors: list[str] = []
    word_ids: list[int] = []

    for row in rows:
        word_text = row["word"]
        existing = db.scalar(select(Word).where(func.lower(Word.word) == word_text.lower()))
        if existing:
            if existing.word != word_text:
                existing.word = word_text
            existing.phonetic = row.get("phonetic") or existing.phonetic
            existing.alternate_spellings = merge_spellings(existing.alternate_spellings, row.get("alternate_spellings"))
            existing.part_of_speech = row.get("part_of_speech") or existing.part_of_speech
            existing.english_definition = row.get("english_definition") or existing.english_definition
            existing.english_definition_locked = existing.english_definition_locked or bool(row.get("english_definition"))
            existing.chinese_definition = row.get("chinese_definition") or existing.chinese_definition
            existing.chinese_definition_locked = existing.chinese_definition_locked or bool(row.get("chinese_definition"))
            existing.english_example = row.get("english_example") or existing.english_example
            existing.english_example_locked = existing.english_example_locked or bool(row.get("english_example"))
            existing.note = row.get("note") or existing.note
            word = existing
            word.enrichment_status = "pending"
            updated += 1
        else:
            word = Word(
                word=word_text,
                phonetic=row.get("phonetic"),
                alternate_spellings=row.get("alternate_spellings"),
                part_of_speech=row.get("part_of_speech"),
                english_definition=row.get("english_definition"),
                english_definition_locked=bool(row.get("english_definition")),
                chinese_definition=row.get("chinese_definition"),
                chinese_definition_locked=bool(row.get("chinese_definition")),
                english_example=row.get("english_example"),
                english_example_locked=bool(row.get("english_example")),
                note=row.get("note"),
                enrichment_status="pending",
            )
            db.add(word)
            created += 1

        try:
            db.commit()
            db.refresh(word)
            link_word_to_list(db, word_list.id, word.id)
            word_ids.append(word.id)
        except Exception as exc:
            db.rollback()
            skipped += 1
            errors.append(f"第 {row.get('row_number')} 行 {word_text}: {exc}")

    return word_ids


def merge_spellings(existing: str | None, incoming: str | None) -> str | None:
    values: list[str] = []
    seen: set[str] = set()
    for text in (existing, incoming):
        if not text:
            continue
        for item in re.split(r"[,;/；，、\n\r]+", text):
            spelling = item.strip()
            normalized = spelling.lower()
            if spelling and normalized not in seen:
                seen.add(normalized)
                values.append(spelling)
    return "\n".join(values) if values else None


def normalize_spelling_answer(value: str) -> str:
    return " ".join(re.sub(r"\d+", "", value).strip().lower().split())


def spelling_answer_options(word: Word) -> set[str]:
    options = {normalize_spelling_answer(word.word)}
    if word.alternate_spellings:
        for item in re.split(r"[,;/；，、\n\r]+", word.alternate_spellings):
            normalized = normalize_spelling_answer(item)
            if normalized:
                options.add(normalized)
    return options


def recorded_audio_suffix(content_type: str, filename: str) -> str:
    if "webm" in content_type:
        return ".webm"
    if "ogg" in content_type or "opus" in content_type:
        return ".ogg"
    if "mpeg" in content_type or "mp3" in content_type:
        return ".mp3"
    if "mp4" in content_type or "m4a" in content_type:
        return ".m4a"
    suffix = Path(filename).suffix.lower()
    if suffix in {".webm", ".ogg", ".mp3", ".m4a", ".mp4", ".wav"}:
        return suffix
    return ".webm"


def extract_book_file(filename: str, content: bytes) -> dict:
    suffix = Path(filename or "").suffix.lower()
    if suffix == ".txt":
        return {"text": decode_text_file(content), "cover_url": None}
    if suffix == ".epub":
        return extract_epub_book(content, filename)
    raise ValueError("当前支持 txt 和 epub 书籍文件。")


def decode_text_file(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            return content.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore").strip()


def extract_epub_book(content: bytes, filename: str) -> dict:
    try:
        archive = zipfile.ZipFile(BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise ValueError("EPUB 文件无法打开，请确认文件没有损坏。") from exc

    text_parts: list[str] = []
    cover_url = save_first_epub_image(archive, filename)
    names = sorted(
        name
        for name in archive.namelist()
        if name.lower().endswith((".xhtml", ".html", ".htm"))
        and "meta-inf/" not in name.lower()
        and not re.search(r"(^|/)(nav|toc|cover|titlepage)\.", name.lower())
    )
    for name in names:
        try:
            raw = archive.read(name)
        except KeyError:
            continue
        fragment = html_to_text(decode_text_file(raw))
        if len(fragment) >= 80:
            text_parts.append(fragment)

    text_value = "\n\n".join(text_parts).strip()
    if not text_value:
        raise ValueError("没有从 EPUB 里读取到正文，请换一本书或转成 txt 后上传。")
    return {"text": text_value[:1_200_000], "cover_url": cover_url}


def save_first_epub_image(archive: zipfile.ZipFile, filename: str) -> str | None:
    image_names = [
        name
        for name in archive.namelist()
        if name.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif"))
        and "__macosx/" not in name.lower()
    ]
    if not image_names:
        return None

    image_names.sort(key=lambda name: (0 if "cover" in name.lower() else 1, len(name), name))
    source_name = image_names[0]
    suffix = Path(source_name).suffix.lower() or ".jpg"
    if suffix == ".jpeg":
        suffix = ".jpg"
    try:
        image_bytes = archive.read(source_name)
    except KeyError:
        return None
    if len(image_bytes) < 1000:
        return None

    safe_stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", Path(filename or "book").stem).strip("-") or "book"
    target = BOOK_COVER_DIR / f"{safe_stem}-{uuid4().hex[:8]}{suffix}"
    target.write_bytes(image_bytes)
    return f"/media/book-covers/{target.name}"


def html_to_text(value: str) -> str:
    value = re.sub(r"(?is)<(script|style|svg|math).*?</\1>", " ", value)
    value = re.sub(r"(?i)<br\s*/?>", "\n", value)
    value = re.sub(r"(?i)</p\s*>|</div\s*>|</h[1-6]\s*>|</li\s*>", "\n", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r"\n\s*\n\s*\n+", "\n\n", value)
    return value.strip()


def start_enrichment_thread(word_ids: list[int]) -> None:
    worker = Thread(target=lambda: asyncio.run(enrich_word_ids(word_ids)), daemon=True)
    worker.start()


def clean_list_name(name: str) -> str:
    text = " ".join((name or "").split())
    return text[:255] or "新单词表"


def page_context(request: Request, db: Session, extra: dict | None = None) -> dict:
    context = {
        "request": request,
        "app_name": settings.app_name,
        "daily_quote": get_daily_quote(db),
        "sidebar_challenges": sidebar_challenge_progress(db),
        "wrong_word_count": wrong_word_count(db),
        "version_matrix": ensure_version_matrix_file(),
        "static_version": static_asset_version(),
    }
    context["shell_context"] = serialize_shell_context(context)
    if extra:
        context.update(extra)
    return context


def serialize_shell_context(context: dict[str, Any]) -> dict[str, Any]:
    daily_quote = context.get("daily_quote")
    return {
        "appName": context.get("app_name", settings.app_name),
        "dailyQuote": {
            "content": daily_quote.content,
            "author": daily_quote.author,
        }
        if daily_quote
        else None,
        "wrongWordCount": context.get("wrong_word_count", 0),
        "versionMatrix": context.get("version_matrix") or ensure_version_matrix_file(),
        "sidebarChallenges": [
            {
                "id": item["list"].id,
                "name": item["list"].name,
                "completed": item["challenge"]["completed"],
                "total": item["challenge"]["total"],
                "percent": item["challenge"]["percent"],
            }
            for item in context.get("sidebar_challenges", [])
        ],
    }


def cached_json(
    db: Session,
    cache_key: str,
    ttl: timedelta,
    producer,
    fallback: dict | list | None = None,
):
    now = datetime.utcnow()
    entry = db.get(CacheEntry, cache_key)
    if entry and entry.expires_at > now:
        return json.loads(entry.payload)
    if entry:
        schedule_cache_refresh(cache_key, ttl, producer)
        return json.loads(entry.payload)

    try:
        payload = producer()
    except Exception:
        if entry:
            return json.loads(entry.payload)
        if fallback is not None:
            return fallback
        raise

    encoded = json.dumps(payload, ensure_ascii=False)
    if entry:
        entry.payload = encoded
        entry.expires_at = now + ttl
    else:
        db.add(CacheEntry(key=cache_key, payload=encoded, expires_at=now + ttl))
    db.commit()
    return payload


def schedule_cache_refresh(cache_key: str, ttl: timedelta, producer) -> None:
    with CACHE_REFRESH_LOCK:
        if cache_key in CACHE_REFRESHING:
            return
        CACHE_REFRESHING.add(cache_key)

    def refresh() -> None:
        db = SessionLocal()
        try:
            payload = producer()
            encoded = json.dumps(payload, ensure_ascii=False)
            now = datetime.utcnow()
            entry = db.get(CacheEntry, cache_key)
            if entry:
                entry.payload = encoded
                entry.expires_at = now + ttl
            else:
                db.add(CacheEntry(key=cache_key, payload=encoded, expires_at=now + ttl))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
            with CACHE_REFRESH_LOCK:
                CACHE_REFRESHING.discard(cache_key)

    Thread(target=refresh, daemon=True).start()


def require_word_write_access(edit_token: str) -> None:
    if edit_token != "1":
        raise HTTPException(status_code=403, detail="当前入口为只读模式，请从我的单词表进入后编辑")


def friendly_enrichment_error(error: str | None) -> str | None:
    if not error:
        return None
    lower_error = error.lower()
    if "api.dictionaryapi.dev" in lower_error and "404" in lower_error:
        return "开放词典暂未收录这个词，可以手动编辑定义、例句和音频。"
    if "client error" in lower_error and "404" in lower_error:
        return "词典暂未收录这个词，可以手动编辑定义、例句和音频。"
    return error


def ensure_schema_columns() -> None:
    inspector = inspect(engine)
    word_columns = {column["name"] for column in inspector.get_columns("words")}
    dialect = engine.dialect.name
    boolean_type = "TINYINT(1)" if dialect == "mysql" else "BOOLEAN"
    missing_boolean_columns = [
        column
        for column in (
            "image_locked",
            "american_audio_locked",
            "british_audio_locked",
            "english_definition_locked",
            "chinese_definition_locked",
            "english_example_locked",
        )
        if column not in word_columns
    ]
    missing_text_columns = [column for column in ("alternate_spellings",) if column not in word_columns]
    missing_string_columns = [column for column in ("part_of_speech",) if column not in word_columns]
    table_names = set(inspector.get_table_names())
    wrong_columns = {column["name"] for column in inspector.get_columns("wrong_words")} if "wrong_words" in table_names else set()
    word_list_columns = {column["name"] for column in inspector.get_columns("word_lists")} if "word_lists" in table_names else set()
    challenge_progress_columns = (
        {column["name"] for column in inspector.get_columns("challenge_progress")}
        if "challenge_progress" in table_names
        else set()
    )

    with engine.begin() as connection:
        for column in missing_boolean_columns:
            connection.execute(text(f"ALTER TABLE words ADD COLUMN {column} {boolean_type} NOT NULL DEFAULT 0"))
        for column in missing_text_columns:
            connection.execute(text(f"ALTER TABLE words ADD COLUMN {column} TEXT NULL"))
        for column in missing_string_columns:
            connection.execute(text(f"ALTER TABLE words ADD COLUMN {column} VARCHAR(120) NULL"))
        if "word_lists" in table_names and "sequence_offset" not in word_list_columns:
            connection.execute(text("ALTER TABLE word_lists ADD COLUMN sequence_offset INTEGER NOT NULL DEFAULT 0"))
        if "challenge_progress" in table_names and "completed_rounds" not in challenge_progress_columns:
            connection.execute(text("ALTER TABLE challenge_progress ADD COLUMN completed_rounds INTEGER NOT NULL DEFAULT 0"))
        if "wrong_words" in table_names and "wrong_date" not in wrong_columns:
            if dialect == "mysql":
                connection.execute(text("ALTER TABLE wrong_words ADD COLUMN wrong_date DATE NULL"))
                connection.execute(text("UPDATE wrong_words SET wrong_date = CURDATE() WHERE wrong_date IS NULL"))
                connection.execute(text("ALTER TABLE wrong_words MODIFY wrong_date DATE NOT NULL"))
            else:
                connection.execute(text("ALTER TABLE wrong_words ADD COLUMN wrong_date DATE NULL"))
                connection.execute(text("UPDATE wrong_words SET wrong_date = DATE('now') WHERE wrong_date IS NULL"))
        if "wrong_words" in table_names and dialect == "mysql":
            indexes = {index["name"] for index in inspector.get_indexes("wrong_words")}
            if "uq_wrong_words_word" in indexes:
                connection.execute(text("ALTER TABLE wrong_words DROP INDEX uq_wrong_words_word"))
            if "uq_wrong_words_word_date" not in indexes:
                connection.execute(text("ALTER TABLE wrong_words ADD UNIQUE INDEX uq_wrong_words_word_date (word_id, wrong_date)"))
        if "challenge_daily_stats" in table_names:
            connection.execute(text("UPDATE challenge_daily_stats SET correct_count = 0 WHERE correct_count IS NULL"))
            connection.execute(text("UPDATE challenge_daily_stats SET wrong_count = 0 WHERE wrong_count IS NULL"))
        if "challenge_daily_words" in table_names:
            connection.execute(text("UPDATE challenge_daily_words SET correct_count = 0 WHERE correct_count IS NULL"))
            connection.execute(text("UPDATE challenge_daily_words SET wrong_count = 0 WHERE wrong_count IS NULL"))


def seed_daily_quotes(db: Session) -> None:
    if db.scalar(select(func.count(DailyQuote.id))) > 0:
        return
    quotes = [
        ("The limits of my language mean the limits of my world.", "Ludwig Wittgenstein"),
        ("One language sets you in a corridor for life. Two languages open every door along the way.", "Frank Smith"),
        ("To learn a language is to have one more window from which to look at the world.", "Chinese proverb"),
        ("Language is the road map of a culture.", "Rita Mae Brown"),
        ("Learning never exhausts the mind.", "Leonardo da Vinci"),
    ]
    for content, author in quotes:
        db.add(DailyQuote(content=content, author=author))
    db.commit()


def get_daily_quote(db: Session) -> DailyQuote | None:
    quotes = db.scalars(select(DailyQuote).order_by(DailyQuote.id.asc())).all()
    if not quotes:
        return None
    index = date.today().toordinal() % len(quotes)
    return quotes[index]


def get_or_create_word_list(db: Session, word_list_id: str, name: str) -> WordList:
    word_list = db.get(WordList, int(word_list_id)) if word_list_id.isdigit() else None
    if word_list:
        word_list.name = clean_list_name(name)
    else:
        word_list = WordList(name=clean_list_name(name))
        db.add(word_list)
    db.commit()
    db.refresh(word_list)
    return word_list


def get_or_create_word_list_by_name(db: Session, name: str) -> WordList:
    cleaned_name = clean_list_name(name)
    word_list = db.scalar(
        select(WordList).where(WordList.name == cleaned_name).order_by(WordList.id.asc()).limit(1)
    )
    if not word_list:
        word_list = WordList(name=cleaned_name)
        db.add(word_list)
        db.commit()
        db.refresh(word_list)
    return word_list


def link_word_to_list(db: Session, word_list_id: int, word_id: int) -> None:
    existing = db.scalar(
        select(WordListItem).where(
            WordListItem.word_list_id == word_list_id,
            WordListItem.word_id == word_id,
        )
    )
    if not existing:
        db.add(WordListItem(word_list_id=word_list_id, word_id=word_id))
        db.commit()


def ensure_default_word_list(db: Session) -> None:
    if db.scalar(select(func.count(WordList.id))) == 0:
        default_list = WordList(name="默认单词表")
        db.add(default_list)
        db.commit()
        db.refresh(default_list)
    else:
        default_list = db.scalars(select(WordList).order_by(WordList.created_at.asc()).limit(1)).first()

    orphan_words = db.scalars(
        select(Word).where(
            ~select(WordListItem.id).where(WordListItem.word_id == Word.id).exists()
        )
    ).all()
    for word in orphan_words:
        db.add(WordListItem(word_list_id=default_list.id, word_id=word.id))
    if orphan_words:
        db.commit()


def word_list_card(db: Session, word_list: WordList) -> dict:
    words = get_words_for_list(db, word_list.id, order_by_created=True)
    image_words = [word for word in words if word.image_url]
    cover_word = random.choice(image_words) if image_words else (words[0] if words else None)
    return {
        "list": word_list,
        "count": len(words),
        "cover_word": cover_word,
        "preview_words": words[:6],
        "challenge": challenge_state(db, word_list),
    }


def get_words_for_list(db: Session, word_list_id: int, order_by_created: bool = False) -> list[Word]:
    order_column = Word.created_at.desc() if order_by_created else WordListItem.id.asc()
    return db.scalars(
        select(Word)
        .join(WordListItem, WordListItem.word_id == Word.id)
        .where(WordListItem.word_list_id == word_list_id)
        .order_by(order_column)
    ).all()


def get_words_for_list_sequence(db: Session, word_list_id: int) -> list[Word]:
    return db.scalars(
        select(Word)
        .join(WordListItem, WordListItem.word_id == Word.id)
        .where(WordListItem.word_list_id == word_list_id)
        .order_by(WordListItem.id.asc())
    ).all()


def is_wrong_word_list_name(name: str | None) -> bool:
    return bool(name and re.fullmatch(r"生词本 \d{4}-\d{2}-\d{2}", name.strip()))


def regular_word_lists(db: Session) -> list[WordList]:
    word_lists = db.scalars(select(WordList).order_by(WordList.created_at.desc())).all()
    return [word_list for word_list in word_lists if not is_wrong_word_list_name(word_list.name)]


def normalize_image_match_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def spelling_values_for_match(word: Word) -> set[str]:
    values = {word.word}
    if word.alternate_spellings:
        values.update(
            item.strip()
            for item in re.split(r"[,;/；，、\r\n]+", word.alternate_spellings)
            if item.strip()
        )
    return values


def build_word_image_match_maps(words: list[Word]) -> tuple[dict[int, Word], dict[str, Word]]:
    by_index = {index: word for index, word in enumerate(words, start=1)}
    by_name: dict[str, Word] = {}
    for word in words:
        for spelling in spelling_values_for_match(word):
            key = normalize_image_match_key(spelling)
            if key and key not in by_name:
                by_name[key] = word
    return by_index, by_name


def is_supported_image_filename(filename: str) -> bool:
    return Path(filename).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


def filename_match_candidates(filename: str) -> tuple[int | None, list[str]]:
    stem = Path(filename).stem.strip()
    index_match = re.match(r"^\D*0*(\d+)(?:\D|$)", stem)
    index_value = int(index_match.group(1)) if index_match else None
    parts = [part for part in re.split(r"[\s._\-()（）\[\]【】]+", stem) if part]
    name_candidates = [stem, *parts]
    if parts and parts[0].isdigit() and len(parts) > 1:
        name_candidates.append(parts[1])
    normalized = []
    seen = set()
    for item in name_candidates:
        key = normalize_image_match_key(item)
        if key and not key.isdigit() and key not in seen:
            normalized.append(key)
            seen.add(key)
    return index_value, normalized


def match_word_image_filename(filename: str, by_index: dict[int, Word], by_name: dict[str, Word]) -> Word | None:
    index_value, name_candidates = filename_match_candidates(filename)
    if index_value and index_value in by_index:
        return by_index[index_value]
    for key in name_candidates:
        if key in by_name:
            return by_name[key]
    return None


async def apply_uploaded_images_to_words(
    words: list[Word],
    image_files: list[UploadFile],
    db: Session,
) -> dict[str, int]:
    by_index, by_name = build_word_image_match_maps(words)
    result = {"matched": 0, "unmatched": 0, "failed": 0}

    for upload in image_files:
        filename = Path((upload.filename or "").replace("\\", "/")).name
        if not is_supported_image_filename(filename):
            continue

        word = match_word_image_filename(filename, by_index, by_name)
        if not word:
            result["unmatched"] += 1
            continue

        content = await upload.read()
        if not content:
            result["failed"] += 1
            continue

        previous_url = word.image_url
        try:
            word.image_url = store_uploaded_word_image(word.word, content, IMAGE_DIR)
        except Exception:
            result["failed"] += 1
            continue

        word.image_locked = True
        word.enrichment_error = None
        db.add(word)
        db.commit()
        if previous_url != word.image_url:
            remove_local_image(previous_url, IMAGE_DIR)
        result["matched"] += 1

    return result


def get_or_create_challenge_progress(db: Session, word_list_id: int) -> ChallengeProgress:
    progress = db.scalar(select(ChallengeProgress).where(ChallengeProgress.word_list_id == word_list_id))
    if progress:
        return progress
    progress = ChallengeProgress(word_list_id=word_list_id)
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress


def wrong_list_name(wrong_date: date) -> str:
    return f"生词本 {wrong_date.isoformat()}"


def get_wrong_word_list(db: Session, wrong_date: date) -> WordList | None:
    return db.scalar(select(WordList).where(WordList.name == wrong_list_name(wrong_date)))


def get_or_create_wrong_word_list(db: Session, wrong_date: date) -> WordList:
    word_list = get_wrong_word_list(db, wrong_date)
    if word_list:
        return word_list
    word_list = WordList(name=wrong_list_name(wrong_date))
    db.add(word_list)
    db.flush()
    return word_list


def parse_wrong_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def record_wrong_word(db: Session, word_id: int) -> None:
    today = date.today()
    wrong_word = db.scalar(
        select(WrongWord).where(
            WrongWord.word_id == word_id,
            WrongWord.wrong_date == today,
        )
    )
    if wrong_word:
        wrong_word.wrong_count += 1
    else:
        wrong_word = WrongWord(word_id=word_id, wrong_date=today)
    db.add(wrong_word)
    word_list = get_or_create_wrong_word_list(db, today)
    existing_item = db.scalar(
        select(WordListItem).where(
            WordListItem.word_list_id == word_list.id,
            WordListItem.word_id == word_id,
        )
    )
    if not existing_item:
        db.add(WordListItem(word_list_id=word_list.id, word_id=word_id))
    db.flush()


def clear_wrong_word_if_passed(db: Session, word_id: int, wrong_date: date | None) -> None:
    if not wrong_date:
        return
    db.execute(
        delete(WrongWord).where(
            WrongWord.word_id == word_id,
            WrongWord.wrong_date == wrong_date,
        )
    )


def wrong_word_count(db: Session) -> int:
    return db.scalar(select(func.count(WrongWord.id))) or 0


def needs_image_sync(word: Word) -> bool:
    return not word.image_locked and not is_local_media_url(word.image_url)


def get_pending_image_words(db: Session, word_list_id: int) -> list[Word]:
    words = db.scalars(
        select(Word)
        .join(WordListItem, WordListItem.word_id == Word.id)
        .where(WordListItem.word_list_id == word_list_id)
        .order_by(Word.word.asc())
    ).all()
    return [word for word in words if needs_image_sync(word)]


def update_image_sync_job(job_id: str, **changes) -> None:
    with IMAGE_SYNC_LOCK:
        job = IMAGE_SYNC_JOBS.get(job_id)
        if not job:
            return
        job.update(changes)


def append_image_sync_result(job_id: str, result: dict) -> None:
    with IMAGE_SYNC_LOCK:
        job = IMAGE_SYNC_JOBS.get(job_id)
        if not job:
            return
        job["results"].append(result)
        job["done"] += 1
        if not result.get("ok"):
            job["failed"] += 1


def run_image_sync_job(job_id: str, word_list_id: int) -> None:
    db = SessionLocal()
    try:
        pending_words = get_pending_image_words(db, word_list_id)
        update_image_sync_job(
            job_id,
            status="running",
            total=len(pending_words),
            done=0,
            failed=0,
            message="正在查找并下载图片",
        )
        if not pending_words:
            update_image_sync_job(job_id, status="complete", message="当前单词表没有缺失图片。")
            return

        for word in pending_words:
            update_image_sync_job(job_id, current_word=word.word)
            try:
                result = asyncio.run(sync_word_image_record(db, word))
            except Exception as exc:
                result = {"ok": False, "id": word.id, "word": word.word, "error": str(exc)}
            append_image_sync_result(job_id, result)

        with IMAGE_SYNC_LOCK:
            job = IMAGE_SYNC_JOBS.get(job_id)
            failed = job.get("failed", 0) if job else 0
        update_image_sync_job(
            job_id,
            status="failed" if failed else "complete",
            current_word="",
            message="部分图片未找到。" if failed else "图片已下载并压缩到服务器图片库。",
        )
    finally:
        db.close()


def record_challenge_daily_result(
    db: Session,
    is_correct: bool,
    word_id: int | None = None,
    word_list_id: int | None = None,
) -> None:
    today = date.today()
    stat = db.scalar(select(ChallengeDailyStat).where(ChallengeDailyStat.stat_date == today))
    if not stat:
        stat = ChallengeDailyStat(stat_date=today, correct_count=0, wrong_count=0)
    if is_correct:
        stat.correct_count = (stat.correct_count or 0) + 1
    else:
        stat.wrong_count = (stat.wrong_count or 0) + 1
    db.add(stat)
    if word_id:
        detail = db.scalar(
            select(ChallengeDailyWord).where(
                ChallengeDailyWord.challenge_date == today,
                ChallengeDailyWord.word_id == word_id,
            )
        )
        if not detail:
            detail = ChallengeDailyWord(challenge_date=today, word_id=word_id, word_list_id=word_list_id)
        elif word_list_id:
            detail.word_list_id = word_list_id
        if is_correct:
            detail.correct_count = (detail.correct_count or 0) + 1
            detail.last_result = "correct"
        else:
            detail.wrong_count = (detail.wrong_count or 0) + 1
            detail.last_result = "wrong"
        db.add(detail)
    db.flush()


def record_spelling_attempt(
    db: Session,
    word: Word,
    word_list_id: int | None,
    typed_spelling: str,
    normalized_spelling: str,
    expected_spellings: set[str],
    is_correct: bool,
) -> None:
    db.add(
        ChallengeSpellingAttempt(
            word_id=word.id,
            word_list_id=word_list_id,
            typed_spelling=typed_spelling.strip(),
            normalized_spelling=normalized_spelling,
            expected_spellings=json.dumps(sorted(expected_spellings), ensure_ascii=False),
            is_correct=is_correct,
        )
    )


def challenge_calendar(db: Session) -> dict:
    today = date.today()
    first_day = today.replace(day=1)
    days_in_month = monthrange(today.year, today.month)[1]
    last_day = today.replace(day=days_in_month)
    stats = db.scalars(
        select(ChallengeDailyStat)
        .where(ChallengeDailyStat.stat_date >= first_day)
        .where(ChallengeDailyStat.stat_date <= last_day)
        .order_by(ChallengeDailyStat.stat_date.asc())
    ).all()
    stats_by_date = {item.stat_date: item for item in stats}
    cells = []
    for _ in range(first_day.weekday()):
        cells.append({"day": "", "is_today": False, "correct": 0, "wrong": 0, "total": 0})
    for day_number in range(1, days_in_month + 1):
        current_day = today.replace(day=day_number)
        stat = stats_by_date.get(current_day)
        correct = stat.correct_count if stat else 0
        wrong = stat.wrong_count if stat else 0
        cells.append(
            {
                "day": day_number,
                "date": current_day.isoformat(),
                "is_today": current_day == today,
                "correct": correct,
                "wrong": wrong,
                "total": correct + wrong,
            }
        )
    while len(cells) % 7:
        cells.append({"day": "", "is_today": False, "correct": 0, "wrong": 0, "total": 0})
    weeks = [cells[index : index + 7] for index in range(0, len(cells), 7)]
    return {
        "title": f"{today.year} 年 {today.month} 月",
        "weekdays": ["一", "二", "三", "四", "五", "六", "日"],
        "weeks": weeks,
        "month_correct": sum(item.correct_count for item in stats),
        "month_wrong": sum(item.wrong_count for item in stats),
    }


def challenge_state(db: Session, word_list: WordList) -> dict:
    total = db.scalar(
        select(func.count(WordListItem.id)).where(WordListItem.word_list_id == word_list.id)
    ) or 0
    progress = db.scalar(select(ChallengeProgress).where(ChallengeProgress.word_list_id == word_list.id))
    created_progress = False
    if not progress and total:
        progress = ChallengeProgress(word_list_id=word_list.id, current_index=0, completed_count=0, completed_rounds=0)
        db.add(progress)
        db.flush()
        created_progress = True
    historical_completed = challenged_word_count_for_list(db, word_list.id, total) if not progress or not progress.completed_rounds else 0
    completed = min(
        max(progress.completed_count if progress else 0, historical_completed),
        total,
    )
    completed_rounds = progress.completed_rounds if progress else 0
    if total and completed >= total and progress:
        progress.completed_rounds = (progress.completed_rounds or 0) + 1
        progress.completed_count = 0
        progress.current_index = 0
        db.add(progress)
        db.commit()
        db.refresh(progress)
        completed = 0
        completed_rounds = progress.completed_rounds
    elif created_progress:
        db.commit()
        db.refresh(progress)
    percent = round((completed / total) * 100) if total else 0
    return {
        "completed": completed,
        "total": total,
        "percent": percent,
        "is_complete": bool(total and completed >= total),
        "completed_rounds": completed_rounds,
    }


def challenged_word_count_for_list(db: Session, word_list_id: int, total: int | None = None) -> int:
    word_ids = select(WordListItem.word_id).where(WordListItem.word_list_id == word_list_id)
    daily_count = db.scalar(
        select(func.count(func.distinct(ChallengeDailyWord.word_id)))
        .where(ChallengeDailyWord.word_id.in_(word_ids))
        .where(or_(ChallengeDailyWord.word_list_id == word_list_id, ChallengeDailyWord.word_list_id.is_(None)))
    ) or 0
    attempt_count = db.scalar(
        select(func.count(func.distinct(ChallengeSpellingAttempt.word_id)))
        .where(ChallengeSpellingAttempt.word_id.in_(word_ids))
        .where(or_(ChallengeSpellingAttempt.word_list_id == word_list_id, ChallengeSpellingAttempt.word_list_id.is_(None)))
    ) or 0
    count = max(int(daily_count), int(attempt_count))
    if total is not None:
        return min(count, total)
    return count


def challenge_counts_for_words(db: Session, word_ids: list[int]) -> dict[int, dict[str, int]]:
    if not word_ids:
        return {}
    rows = db.execute(
        select(
            ChallengeDailyWord.word_id,
            func.coalesce(func.sum(ChallengeDailyWord.correct_count), 0),
            func.coalesce(func.sum(ChallengeDailyWord.wrong_count), 0),
        )
        .where(ChallengeDailyWord.word_id.in_(word_ids))
        .group_by(ChallengeDailyWord.word_id)
    ).all()
    return {
        word_id: {"correct": int(correct or 0), "wrong": int(wrong or 0)}
        for word_id, correct, wrong in rows
    }


def word_navigation_context(
    db: Session,
    word_id: int,
    list_id: int | None = None,
    challenge_day: str | None = None,
    challenge_status: str | None = None,
) -> dict:
    challenge_date = parse_wrong_date(challenge_day)
    if challenge_date:
        day_query = (
            select(Word.id)
            .join(ChallengeDailyWord, ChallengeDailyWord.word_id == Word.id)
            .where(ChallengeDailyWord.challenge_date == challenge_date)
        )
        if challenge_status in {"correct", "wrong"}:
            day_query = day_query.where(ChallengeDailyWord.last_result == challenge_status)
        day_word_ids = db.scalars(
            day_query.order_by(ChallengeDailyWord.updated_at.asc(), ChallengeDailyWord.id.asc())
        ).all()
        if word_id in day_word_ids:
            current_index = list(day_word_ids).index(word_id)
            previous_index = current_index - 1
            next_index = current_index + 1
            previous_word_id = day_word_ids[previous_index] if previous_index >= 0 else day_word_ids[current_index]
            next_word_id = day_word_ids[next_index] if next_index < len(day_word_ids) else day_word_ids[current_index]
            return {
                "list_id": list_id,
                "index": current_index + 1,
                "previous_word_id": previous_word_id,
                "next_word_id": next_word_id,
            }

    if list_id:
        linked = db.scalar(
            select(WordListItem.id)
            .where(WordListItem.word_list_id == list_id)
            .where(WordListItem.word_id == word_id)
            .limit(1)
        )
        if not linked:
            list_id = None

    if not list_id:
        list_id = db.scalar(
            select(WordListItem.word_list_id)
            .where(WordListItem.word_id == word_id)
            .order_by(WordListItem.word_list_id.asc())
            .limit(1)
        )
    if not list_id:
        return {"list_id": None, "index": None, "previous_word_id": max(word_id - 1, 1), "next_word_id": word_id + 1}

    word_ids = db.scalars(
        select(Word.id)
        .join(WordListItem, WordListItem.word_id == Word.id)
        .where(WordListItem.word_list_id == list_id)
        .order_by(Word.word.asc())
    ).all()
    try:
        current_index = list(word_ids).index(word_id)
    except ValueError:
        return {"list_id": list_id, "index": None, "previous_word_id": max(word_id - 1, 1), "next_word_id": word_id + 1}

    previous_index = current_index - 1
    next_index = current_index + 1
    previous_word_id = word_ids[previous_index] if previous_index >= 0 else word_ids[current_index]
    next_word_id = word_ids[next_index] if next_index < len(word_ids) else word_ids[current_index]
    return {
        "list_id": list_id,
        "index": current_index + 1,
        "previous_word_id": previous_word_id,
        "next_word_id": next_word_id,
    }


def sidebar_challenge_progress(db: Session) -> list[dict]:
    word_lists = regular_word_lists(db)
    items = []
    for word_list in word_lists:
        state = challenge_state(db, word_list)
        if 0 < state["completed"] < state["total"]:
            items.append({"list": word_list, "challenge": state})
    return items


async def enrich_word_ids(word_ids: list[int]) -> None:
    db = SessionLocal()
    try:
        for word_id in word_ids:
            word = db.get(Word, word_id)
            if word:
                await enrich_word(db, word)
    finally:
        db.close()


@app.get("/tts")
async def tts_audio(word: str = Query(..., min_length=1, max_length=80), accent: str = "us"):
    headers = {"User-Agent": "Mozilla/5.0"}
    youdao_type = "1" if accent == "gb" else "2"
    fallback_youdao_type = "2" if youdao_type == "1" else "1"
    google_lang = "en-GB" if accent == "gb" else "en-US"
    candidates = [
        (
            "https://dict.youdao.com/dictvoice",
            {"audio": word, "type": youdao_type},
        ),
        (
            "https://dict.youdao.com/dictvoice",
            {"audio": word, "type": fallback_youdao_type},
        ),
        (
            "https://translate.google.com/translate_tts",
            {"ie": "UTF-8", "client": "tw-ob", "q": word, "tl": google_lang},
        ),
    ]

    last_error = None
    fallback_response = None
    async with httpx.AsyncClient(timeout=20, headers=headers) as client:
        for url, params in candidates:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                if response.content and len(response.content) >= 9000:
                    return Response(
                        content=response.content,
                        media_type=response.headers.get("content-type", "audio/mpeg"),
                        headers={"Cache-Control": "public, max-age=2592000"},
                    )
                if response.content and fallback_response is None:
                    fallback_response = response
            except Exception as exc:
                last_error = exc

        if fallback_response is not None:
            return Response(
                content=fallback_response.content,
                media_type=fallback_response.headers.get("content-type", "audio/mpeg"),
                headers={"Cache-Control": "public, max-age=2592000"},
            )

    raise HTTPException(status_code=502, detail=f"朗读音频暂不可用: {last_error}")


@app.get("/words/{word_id}/tts")
async def word_id_tts_audio(word_id: int, accent: str = "us", db: Session = Depends(get_db)):
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    return await tts_audio(word.word, accent)


@app.get("/words/{word_id}/audio")
async def word_audio(word_id: int, accent: str = "us", db: Session = Depends(get_db)):
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    audio_url = word.british_audio_url if accent == "gb" else word.american_audio_url
    if is_local_audio_url(audio_url):
        return RedirectResponse(url=audio_url, status_code=302)
    return await tts_audio(word.word, accent)


def mask_word_in_text(
    text_value: str | None,
    word_value: str | None,
    alternate_spellings: str | None = None,
) -> str | None:
    text_value = (text_value or "").strip()
    word_value = (word_value or "").strip()
    if not text_value:
        return None
    if not word_value:
        return text_value

    candidates = {word_value}
    if alternate_spellings:
        candidates.update(
            item.strip()
            for item in re.split(r"[,;/；，、\r\n]+", alternate_spellings)
            if item.strip()
        )

    for candidate in list(candidates):
        lower_candidate = candidate.lower()
        if len(candidate) < 4:
            continue
        if lower_candidate.endswith("ies") and len(candidate) > 4:
            candidates.add(candidate[:-3] + "y")
        if lower_candidate.endswith("es") and len(candidate) > 4:
            candidates.add(candidate[:-2])
        if lower_candidate.endswith("s") and len(candidate) > 4:
            candidates.add(candidate[:-1])
        else:
            candidates.add(candidate + "s")
            candidates.add(candidate + "es")

    masked_text = text_value
    for candidate in sorted(candidates, key=len, reverse=True):
        pattern = re.compile(rf"(?<![A-Za-z]){re.escape(candidate)}(?![A-Za-z])", re.IGNORECASE)
        masked_text = pattern.sub("***", masked_text)
    return masked_text


def preview_path(preview_id: str) -> Path:
    if not preview_id.isalnum():
        raise HTTPException(status_code=400, detail="无效的预览编号")
    return PREVIEW_DIR / f"{preview_id}.json"


def preview_excel_path(preview_id: str) -> Path:
    if not preview_id.isalnum():
        raise HTTPException(status_code=400, detail="无效的预览编号")
    return PREVIEW_DIR / f"{preview_id}.xlsx"

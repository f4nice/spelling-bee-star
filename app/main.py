import asyncio
from datetime import date
import json
from pathlib import Path
import random
import re
from threading import Thread
from urllib.parse import quote_plus
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, SessionLocal, engine, get_db
from app.models import ChallengeProgress, DailyQuote, Word, WordList, WordListItem, WrongWord
from app.services.enrichment import enrich_word
from app.services.excel_importer import parse_preview_from_excel, parse_words_from_preview
from app.services.audio_storage import audio_candidates_with_dictionary, is_local_audio_url, store_audio_candidate
from app.services.image_storage import is_local_media_url, remove_local_image, store_uploaded_word_image, store_word_image
from app.services.images import ImageClient


BASE_DIR = Path(__file__).resolve().parent
PREVIEW_DIR = BASE_DIR.parent / "uploads" / "previews"
MEDIA_DIR = BASE_DIR.parent / "uploads"
IMAGE_DIR = MEDIA_DIR / "images"
AUDIO_DIR = MEDIA_DIR / "audio"
settings = get_settings()

MEDIA_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema_columns()
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        seed_daily_quotes(db)
        ensure_default_word_list(db)


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    word_lists = db.scalars(select(WordList).order_by(WordList.created_at.desc())).all()
    cards = [word_list_card(db, word_list) for word_list in word_lists]
    return templates.TemplateResponse(
        "index.html",
        page_context(request, db, {"cards": cards}),
    )


@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request, db: Session = Depends(get_db)):
    word_lists = db.scalars(select(WordList).order_by(WordList.created_at.desc())).all()
    return templates.TemplateResponse("upload.html", page_context(request, db, {"word_lists": word_lists}))


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
    words = db.scalars(
        select(Word)
        .join(WordListItem, WordListItem.word_id == Word.id)
        .where(WordListItem.word_list_id == word_list_id)
        .order_by(Word.word.asc())
    ).all()
    pending_image_words = [
        {"id": word.id, "word": word.word}
        for word in words
        if not word.image_locked and not is_local_media_url(word.image_url)
    ]
    return templates.TemplateResponse(
        "list_detail.html",
        page_context(
            request,
            db,
            {
                "word_list": word_list,
                "words": words,
                "pending_image_words": pending_image_words,
                "delete_error": bool(delete_error),
            },
        ),
    )


@app.get("/challenge/{word_list_id}", response_class=HTMLResponse)
def challenge_page(
    word_list_id: int,
    request: Request,
    daily_count: int = Query(default=20, ge=1, le=500),
    start_count: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")

    words = get_words_for_list(db, word_list_id)
    progress = get_or_create_challenge_progress(db, word_list_id)
    total = len(words)
    progress.completed_count = min(progress.completed_count, total)
    progress.current_index = min(progress.current_index, max(total - 1, 0))
    db.add(progress)
    db.commit()

    start_count = progress.completed_count if start_count is None else start_count
    start_count = min(max(start_count, 0), total)
    daily_count = min(max(daily_count, 1), max(total, 1))
    daily_target = min(total, start_count + daily_count)
    daily_done = max(0, min(progress.completed_count, daily_target) - start_count)
    daily_total = max(0, daily_target - start_count)
    is_daily_complete = bool(total and progress.completed_count >= daily_target)

    current_word = None if is_daily_complete or progress.completed_count >= total or not words else words[progress.current_index]
    challenge_audio_sources = None
    challenge_image_url = None
    masked_example = None
    if current_word:
        challenge_audio_sources = {
            "us": f"/words/{current_word.id}/audio?accent=us&v=2",
            "gb": f"/words/{current_word.id}/audio?accent=gb&v=2",
        }
        challenge_image_url = f"/words/{current_word.id}/image-view" if current_word.image_url else None
        masked_example = mask_word_in_text(current_word.english_example, current_word.word)
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
    }
    return templates.TemplateResponse(
        "challenge.html",
        page_context(
            request,
            db,
            {
                "word_list": word_list,
                "current_word": current_word,
                "progress": progress,
                "challenge": state,
                "today_challenge": today_challenge,
                "challenge_audio_sources": challenge_audio_sources,
                "challenge_image_url": challenge_image_url,
                "masked_example": masked_example,
            },
        ),
    )


@app.get("/wrong-words", response_class=HTMLResponse)
def wrong_words_page(request: Request, db: Session = Depends(get_db)):
    wrong_words = db.execute(
        select(WrongWord, Word)
        .join(Word, Word.id == WrongWord.word_id)
        .order_by(WrongWord.updated_at.desc(), WrongWord.id.desc())
    ).all()
    return templates.TemplateResponse(
        "wrong_words.html",
        page_context(request, db, {"wrong_words": wrong_words}),
    )


@app.post("/challenge/{word_list_id}/answer")
def challenge_answer(
    word_list_id: int,
    action: str = Form(default="known"),
    daily_count: int = Form(default=20),
    start_count: int = Form(default=0),
    spelling: str = Form(default=""),
    db: Session = Depends(get_db),
):
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")

    words = get_words_for_list(db, word_list_id)
    progress = get_or_create_challenge_progress(db, word_list_id)
    total = len(words)

    if action == "reset":
        progress.current_index = 0
        progress.completed_count = 0
    elif total:
        current_word = words[progress.current_index] if 0 <= progress.current_index < total else None
        if action == "spell" and current_word:
            typed = " ".join(spelling.strip().lower().split())
            expected = " ".join(current_word.word.strip().lower().split())
            action = "known" if typed == expected else "wrong"
        if action == "wrong" and current_word:
            record_wrong_word(db, current_word.id)
        if action == "known":
            progress.completed_count = min(progress.completed_count + 1, total)
        if progress.completed_count < total:
            progress.current_index = (progress.current_index + 1) % total
        else:
            progress.current_index = max(total - 1, 0)

    db.add(progress)
    db.commit()
    daily_count = min(max(daily_count, 1), 500)
    start_count = max(start_count, 0)
    return RedirectResponse(
        url=f"/challenge/{word_list_id}?daily_count={daily_count}&start_count={start_count}",
        status_code=303,
    )


@app.post("/lists/{word_list_id}/rename")
def rename_word_list(word_list_id: int, name: str = Form(...), db: Session = Depends(get_db)):
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")
    word_list.name = clean_list_name(name)
    db.add(word_list)
    db.commit()
    return RedirectResponse(url=f"/lists/{word_list_id}", status_code=303)


@app.post("/lists/{word_list_id}/delete")
def delete_word_list(
    word_list_id: int,
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")
    if password != settings.list_delete_password:
        return RedirectResponse(url=f"/lists/{word_list_id}?delete_error=1", status_code=303)

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
    return RedirectResponse(url="/", status_code=303)


@app.post("/words/{word_id}/image")
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
    remove_local_image(previous_url, IMAGE_DIR)
    return RedirectResponse(url=f"/words/{word_id}?edit=1", status_code=303)


@app.post("/words/{word_id}/sync-image")
async def sync_word_image(word_id: int, db: Session = Depends(get_db)):
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    if is_local_media_url(word.image_url):
        return {"ok": True, "word": word.word, "image_url": word.image_url, "skipped": True}

    if word.image_locked:
        return {"ok": True, "word": word.word, "image_url": word.image_url, "skipped": True, "locked": True}

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
                return {"ok": True, "word": word.word, "image_url": local_url, "skipped": False}
        except Exception as exc:
            errors.append(str(exc))

    word.enrichment_error = "图片同步失败: " + ("; ".join(errors[:2]) or "未找到可用图片")
    db.add(word)
    db.commit()
    return {"ok": False, "word": word.word, "error": word.enrichment_error}


@app.get("/words/{word_id}/image-view")
def word_image_view(word_id: int, db: Session = Depends(get_db)):
    word = db.get(Word, word_id)
    if not word or not word.image_url:
        raise HTTPException(status_code=404, detail="Image not found")
    return RedirectResponse(url=word.image_url, status_code=302)


@app.post("/words/{word_id}/audio-options")
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
    for candidate in await audio_candidates_with_dictionary(word.word, accent):
        try:
            local_url = await store_audio_candidate(word.word, accent, candidate["key"], candidate["url"], AUDIO_DIR)
        except Exception:
            local_url = None
        if local_url:
            options.append({"label": candidate["label"], "url": local_url})

    if not options:
        return {"ok": False, "word": word.word, "accent": accent, "options": [], "error": "没有找到可用音频"}
    return {"ok": True, "word": word.word, "accent": accent, "options": options}


@app.post("/words/{word_id}/audio-choice")
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


@app.post("/words/{word_id}/english-definition")
def update_english_definition(
    word_id: int,
    english_definition: str = Form(default=""),
    edit_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    word.english_definition = english_definition.strip() or None
    word.english_definition_locked = True
    word.enrichment_error = None
    db.add(word)
    db.commit()
    return RedirectResponse(url=f"/words/{word_id}?edit=1", status_code=303)


@app.post("/words/{word_id}/chinese-definition")
def update_chinese_definition(
    word_id: int,
    chinese_definition: str = Form(default=""),
    edit_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    word.chinese_definition = chinese_definition.strip() or None
    word.chinese_definition_locked = True
    word.enrichment_error = None
    db.add(word)
    db.commit()
    return RedirectResponse(url=f"/words/{word_id}?edit=1", status_code=303)


@app.post("/words/{word_id}/english-example")
def update_english_example(
    word_id: int,
    english_example: str = Form(default=""),
    edit_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    word.english_example = english_example.strip() or None
    word.english_example_locked = True
    word.enrichment_error = None
    db.add(word)
    db.commit()
    return RedirectResponse(url=f"/words/{word_id}?edit=1", status_code=303)


@app.get("/words/{word_id}", response_class=HTMLResponse)
def word_detail(
    word_id: int,
    request: Request,
    edit: int = Query(default=0),
    db: Session = Depends(get_db),
):
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    encoded_word = quote_plus(word.word)
    audio_sources = {
        "us": word.american_audio_url if is_local_audio_url(word.american_audio_url) else f"/tts?word={encoded_word}&accent=us&v=2",
        "gb": word.british_audio_url if is_local_audio_url(word.british_audio_url) else f"/tts?word={encoded_word}&accent=gb&v=2",
    }
    return templates.TemplateResponse(
        "detail.html",
        page_context(request, db, {"word": word, "audio_sources": audio_sources, "can_edit": edit == 1}),
    )


@app.post("/upload")
async def upload_excel(
    request: Request,
    file: UploadFile = File(...),
    word_list_id: str = Form(default=""),
    word_list_name: str = Form(default=""),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        raise HTTPException(status_code=400, detail="请上传 .xlsx 格式的 Excel 文件")

    preview = parse_preview_from_excel(await file.read())
    preview_id = uuid4().hex
    preview["filename"] = file.filename
    preview["word_list_id"] = word_list_id
    preview["word_list_name"] = clean_list_name(word_list_name or Path(file.filename or "新单词表").stem)
    preview_path(preview_id).write_text(json.dumps(preview, ensure_ascii=False), encoding="utf-8")

    return templates.TemplateResponse(
        "preview.html",
        page_context(request, db, {"preview_id": preview_id, "preview": preview}),
    )


@app.post("/import-preview")
async def import_preview(
    preview_id: str = Form(...),
    word_list_id: str = Form(default=""),
    word_list_name: str = Form(...),
    word_column: str = Form(...),
    selected_rows: list[int] = Form(default=[]),
    selected_columns: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
):
    path = preview_path(preview_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="预览已过期，请重新上传 Excel")

    preview = json.loads(path.read_text(encoding="utf-8"))
    target_list = get_or_create_word_list(db, word_list_id, word_list_name)
    rows = parse_words_from_preview(
        preview=preview,
        selected_row_indexes=set(selected_rows),
        selected_columns=set(selected_columns),
        word_column=word_column,
    )
    word_ids = import_rows(rows, db, target_list)
    if word_ids:
        start_enrichment_thread(word_ids)
    path.unlink(missing_ok=True)
    return RedirectResponse(url="/", status_code=303)


def import_rows(rows: list[dict], db: Session, word_list: WordList) -> list[int]:
    created = updated = skipped = 0
    errors: list[str] = []
    word_ids: list[int] = []

    for row in rows:
        existing = db.scalar(select(Word).where(Word.word == row["word"]))
        if existing:
            existing.phonetic = existing.phonetic or row.get("phonetic")
            existing.chinese_definition = existing.chinese_definition or row.get("chinese_definition")
            existing.note = existing.note or row.get("note")
            word = existing
            word.enrichment_status = "pending"
            updated += 1
        else:
            word = Word(
                word=row["word"],
                phonetic=row.get("phonetic"),
                chinese_definition=row.get("chinese_definition"),
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
            errors.append(f"第 {row.get('row_number')} 行 {row['word']}: {exc}")

    return word_ids


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
    }
    if extra:
        context.update(extra)
    return context


def require_word_write_access(edit_token: str) -> None:
    if edit_token != "1":
        raise HTTPException(status_code=403, detail="当前入口为只读模式，请从我的单词表进入后编辑")


def ensure_schema_columns() -> None:
    inspector = inspect(engine)
    word_columns = {column["name"] for column in inspector.get_columns("words")}
    dialect = engine.dialect.name
    boolean_type = "TINYINT(1)" if dialect == "mysql" else "BOOLEAN"
    missing_columns = [
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
    if not missing_columns:
        return

    with engine.begin() as connection:
        for column in missing_columns:
            connection.execute(text(f"ALTER TABLE words ADD COLUMN {column} {boolean_type} NOT NULL DEFAULT 0"))


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
    order_column = Word.created_at.desc() if order_by_created else Word.word.asc()
    return db.scalars(
        select(Word)
        .join(WordListItem, WordListItem.word_id == Word.id)
        .where(WordListItem.word_list_id == word_list_id)
        .order_by(order_column)
    ).all()


def get_or_create_challenge_progress(db: Session, word_list_id: int) -> ChallengeProgress:
    progress = db.scalar(select(ChallengeProgress).where(ChallengeProgress.word_list_id == word_list_id))
    if progress:
        return progress
    progress = ChallengeProgress(word_list_id=word_list_id)
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress


def record_wrong_word(db: Session, word_id: int) -> None:
    wrong_word = db.scalar(select(WrongWord).where(WrongWord.word_id == word_id))
    if wrong_word:
        wrong_word.wrong_count += 1
    else:
        wrong_word = WrongWord(word_id=word_id)
    db.add(wrong_word)
    db.flush()


def wrong_word_count(db: Session) -> int:
    return db.scalar(select(func.count(WrongWord.id))) or 0


def challenge_state(db: Session, word_list: WordList) -> dict:
    total = db.scalar(
        select(func.count(WordListItem.id)).where(WordListItem.word_list_id == word_list.id)
    ) or 0
    progress = db.scalar(select(ChallengeProgress).where(ChallengeProgress.word_list_id == word_list.id))
    completed = min(progress.completed_count if progress else 0, total)
    percent = round((completed / total) * 100) if total else 0
    return {
        "completed": completed,
        "total": total,
        "percent": percent,
        "is_complete": bool(total and completed >= total),
    }


def sidebar_challenge_progress(db: Session) -> list[dict]:
    word_lists = db.scalars(select(WordList).order_by(WordList.created_at.desc())).all()
    return [{"list": word_list, "challenge": challenge_state(db, word_list)} for word_list in word_lists]


async def enrich_word_ids(word_ids: list[int]) -> None:
    db = SessionLocal()
    try:
        for word_id in word_ids:
            word = db.get(Word, word_id)
            if word:
                await enrich_word(db, word)
    finally:
        db.close()


@app.post("/words/{word_id}/refresh")
async def refresh_word(
    word_id: int,
    edit_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    await enrich_word(db, word)
    return RedirectResponse(url=f"/words/{word_id}?edit=1", status_code=303)


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
                        headers={"Cache-Control": "no-store"},
                    )
                if response.content and fallback_response is None:
                    fallback_response = response
            except Exception as exc:
                last_error = exc

        if fallback_response is not None:
            return Response(
                content=fallback_response.content,
                media_type=fallback_response.headers.get("content-type", "audio/mpeg"),
                headers={"Cache-Control": "no-store"},
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


def mask_word_in_text(text_value: str | None, word_value: str | None) -> str | None:
    text_value = (text_value or "").strip()
    word_value = (word_value or "").strip()
    if not text_value:
        return None
    if not word_value:
        return text_value
    return re.sub(re.escape(word_value), "***", text_value, flags=re.IGNORECASE)


def preview_path(preview_id: str) -> Path:
    if not preview_id.isalnum():
        raise HTTPException(status_code=400, detail="无效的预览编号")
    return PREVIEW_DIR / f"{preview_id}.json"

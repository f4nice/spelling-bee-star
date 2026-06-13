import asyncio
from datetime import date
import json
from pathlib import Path
import random
from threading import Thread
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, SessionLocal, engine, get_db
from app.models import DailyQuote, Word, WordList, WordListItem
from app.services.enrichment import enrich_word
from app.services.excel_importer import parse_preview_from_excel, parse_words_from_preview


BASE_DIR = Path(__file__).resolve().parent
PREVIEW_DIR = BASE_DIR.parent / "uploads" / "previews"
settings = get_settings()

app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
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
def list_detail(word_list_id: int, request: Request, db: Session = Depends(get_db)):
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")
    words = db.scalars(
        select(Word)
        .join(WordListItem, WordListItem.word_id == Word.id)
        .where(WordListItem.word_list_id == word_list_id)
        .order_by(Word.word.asc())
    ).all()
    return templates.TemplateResponse(
        "list_detail.html",
        page_context(request, db, {"word_list": word_list, "words": words}),
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


@app.get("/words/{word_id}", response_class=HTMLResponse)
def word_detail(word_id: int, request: Request, db: Session = Depends(get_db)):
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    return templates.TemplateResponse("detail.html", page_context(request, db, {"word": word}))


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
    }
    if extra:
        context.update(extra)
    return context


def seed_daily_quotes(db: Session) -> None:
    if db.scalar(select(func.count(DailyQuote.id))) > 0:
        return
    quotes = [
        "不急于证明自己，只专注做好决策。",
        "每天记住一个词，就是给未来多开一扇窗。",
        "稳稳地学，慢慢地赢。",
        "看见一个陌生词，就是靠近一个新世界。",
        "今天的小进步，会在某天突然发光。",
    ]
    for quote in quotes:
        db.add(DailyQuote(content=quote))
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
    words = db.scalars(
        select(Word)
        .join(WordListItem, WordListItem.word_id == Word.id)
        .where(WordListItem.word_list_id == word_list.id)
        .order_by(Word.created_at.desc())
    ).all()
    image_words = [word for word in words if word.image_url]
    cover_word = random.choice(image_words) if image_words else (words[0] if words else None)
    return {
        "list": word_list,
        "count": len(words),
        "cover_word": cover_word,
        "preview_words": words[:6],
    }


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
async def refresh_word(word_id: int, db: Session = Depends(get_db)):
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    await enrich_word(db, word)
    return RedirectResponse(url=f"/words/{word_id}", status_code=303)


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


def preview_path(preview_id: str) -> Path:
    if not preview_id.isalnum():
        raise HTTPException(status_code=400, detail="无效的预览编号")
    return PREVIEW_DIR / f"{preview_id}.json"

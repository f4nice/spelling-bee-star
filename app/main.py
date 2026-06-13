import asyncio
import json
from pathlib import Path
from threading import Thread
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, SessionLocal, engine, get_db
from app.models import Word
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


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    words = db.scalars(select(Word).order_by(Word.created_at.desc()).limit(200)).all()
    return templates.TemplateResponse("index.html", {"request": request, "words": words, "app_name": settings.app_name})


@app.get("/words/{word_id}", response_class=HTMLResponse)
def word_detail(word_id: int, request: Request, db: Session = Depends(get_db)):
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    return templates.TemplateResponse("detail.html", {"request": request, "word": word, "app_name": settings.app_name})


@app.post("/upload")
async def upload_excel(request: Request, file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        raise HTTPException(status_code=400, detail="请上传 .xlsx 格式的 Excel 文件")

    preview = parse_preview_from_excel(await file.read())
    preview_id = uuid4().hex
    preview["filename"] = file.filename
    preview_path(preview_id).write_text(json.dumps(preview, ensure_ascii=False), encoding="utf-8")

    return templates.TemplateResponse(
        "preview.html",
        {
            "request": request,
            "preview_id": preview_id,
            "preview": preview,
            "app_name": settings.app_name,
        },
    )


@app.post("/import-preview")
async def import_preview(
    preview_id: str = Form(...),
    word_column: str = Form(...),
    selected_rows: list[int] = Form(default=[]),
    selected_columns: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
):
    path = preview_path(preview_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="预览已过期，请重新上传 Excel")

    preview = json.loads(path.read_text(encoding="utf-8"))
    rows = parse_words_from_preview(
        preview=preview,
        selected_row_indexes=set(selected_rows),
        selected_columns=set(selected_columns),
        word_column=word_column,
    )
    word_ids = import_rows(rows, db)
    if word_ids:
        start_enrichment_thread(word_ids)
    path.unlink(missing_ok=True)
    return RedirectResponse(url="/", status_code=303)


def import_rows(rows: list[dict], db: Session) -> list[int]:
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
            word_ids.append(word.id)
        except Exception as exc:
            db.rollback()
            skipped += 1
            errors.append(f"第 {row.get('row_number')} 行 {row['word']}: {exc}")

    return word_ids


def start_enrichment_thread(word_ids: list[int]) -> None:
    worker = Thread(target=lambda: asyncio.run(enrich_word_ids(word_ids)), daemon=True)
    worker.start()


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

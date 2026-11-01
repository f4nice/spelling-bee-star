"""Authorization for private media, including pre-ownership legacy filenames."""
from pathlib import PurePosixPath
import re
from urllib.parse import unquote

from fastapi import HTTPException
from sqlalchemy import or_, select

from app.data_context import PUBLIC_OWNER, current_data_context
from app.models import DataPermissionState, EssayEntry, Word

ALLOWED_SUFFIXES = {".jpg",".jpeg",".png",".webp",".gif",".svg",".mp3",".wav",".ogg",".m4a",".aac",".webm"}
FOLDER_MODULE = {"images":"words","audio":"words","book-covers":"books","essay-covers":"writing"}
WORD_URL_FIELDS = ("image_url","american_audio_url","british_audio_url","english_definition_audio_url","english_example_audio_url")


def assert_media_access(url,db,*,book_media_check=None):
    context = current_data_context()
    if context is None:
        raise HTTPException(403,"媒体访问缺少账号上下文。")
    clean = unquote(str(url).split("?",1)[0])
    if not clean.startswith("/media/") or "\\" in clean or "%" in clean or any(ord(char)<32 for char in clean) or any(part in {".",".."} for part in clean.split("/")):
        raise HTTPException(403,"无效的媒体路径。")
    path = PurePosixPath(clean)
    if path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise HTTPException(403,"此文件不允许直接访问。")
    parts = path.parts
    if len(parts)<4:
        raise HTTPException(403,"此媒体文件不可访问。")
    if parts[2] in {"generated-assets","science-discoveries"}:
        return
    if parts[2]=="users":
        if len(parts)!=6 or not re.fullmatch(r"u[1-9]\d*",parts[3]):
            raise HTTPException(403,"无效的个人媒体路径。")
        module = FOLDER_MODULE.get(parts[4])
        if not context.public_write and int(parts[3][1:])==context.owner_id and module in context.modules:
            return
        raise HTTPException(403,"不能访问其他账号的媒体。")
    if parts[2]=="public":
        if len(parts)!=5 or FOLDER_MODULE.get(parts[3])!="words" or "words" not in context.modules:
            raise HTTPException(403,"无效的公共媒体路径。")
        if context.public_write:
            return
        if db.scalar(select(Word.id).where(Word.owner_key==PUBLIC_OWNER,
            or_(*(getattr(Word,field)==clean for field in WORD_URL_FIELDS))).limit(1)):
            return
        raise HTTPException(403,"公共媒体尚未发布。")
    module=FOLDER_MODULE.get(parts[2])
    if module not in context.modules:
        raise HTTPException(403,"未获得此媒体模块的查看授权。")
    if context.public_write:
        raise HTTPException(403,"不能把历史个人媒体发布为公共词库资源。")
    if module=="words":
        if db.scalar(select(Word.id).where(or_(*(getattr(Word,field)==clean for field in WORD_URL_FIELDS))).limit(1)):
            return
    elif module=="writing":
        if db.scalar(select(EssayEntry.id).where(EssayEntry.cover_url==clean).limit(1)):
            return
    elif module=="books" and book_media_check and book_media_check(clean):
        return
    legacy_id=db.scalar(select(DataPermissionState.value).where(DataPermissionState.key=="legacy-owner-id"))
    if legacy_id==str(context.owner_id):
        return
    raise HTTPException(403,"此媒体文件不属于当前数据空间。")

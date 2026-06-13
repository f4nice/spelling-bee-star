from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Word(Base):
    __tablename__ = "words"
    __table_args__ = (UniqueConstraint("word", name="uq_words_word"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    word: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    phonetic: Mapped[str | None] = mapped_column(String(255))
    american_audio_url: Mapped[str | None] = mapped_column(String(1000))
    british_audio_url: Mapped[str | None] = mapped_column(String(1000))
    english_definition: Mapped[str | None] = mapped_column(Text)
    chinese_definition: Mapped[str | None] = mapped_column(Text)
    english_example: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(1000))
    source: Mapped[str | None] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text)
    enrichment_status: Mapped[str] = mapped_column(String(64), default="pending")
    enrichment_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Word(Base):
    __tablename__ = "words"
    __table_args__ = (UniqueConstraint("word", name="uq_words_word"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    word: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    phonetic: Mapped[str | None] = mapped_column(String(255))
    american_audio_url: Mapped[str | None] = mapped_column(String(1000))
    american_audio_locked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    british_audio_url: Mapped[str | None] = mapped_column(String(1000))
    british_audio_locked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    alternate_spellings: Mapped[str | None] = mapped_column(Text)
    part_of_speech: Mapped[str | None] = mapped_column(String(120))
    english_definition: Mapped[str | None] = mapped_column(Text)
    english_definition_locked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    chinese_definition: Mapped[str | None] = mapped_column(Text)
    chinese_definition_locked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    english_example: Mapped[str | None] = mapped_column(Text)
    english_example_locked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1000))
    image_locked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    source: Mapped[str | None] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text)
    enrichment_status: Mapped[str] = mapped_column(String(64), default="pending")
    enrichment_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class WordList(Base):
    __tablename__ = "word_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sequence_offset: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class WordListItem(Base):
    __tablename__ = "word_list_items"
    __table_args__ = (UniqueConstraint("word_list_id", "word_id", name="uq_word_list_items_list_word"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    word_list_id: Mapped[int] = mapped_column(ForeignKey("word_lists.id", ondelete="CASCADE"), nullable=False, index=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DailyQuote(Base):
    __tablename__ = "daily_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ChallengeProgress(Base):
    __tablename__ = "challenge_progress"
    __table_args__ = (UniqueConstraint("word_list_id", name="uq_challenge_progress_word_list"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    word_list_id: Mapped[int] = mapped_column(ForeignKey("word_lists.id", ondelete="CASCADE"), nullable=False, index=True)
    current_index: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    completed_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    completed_rounds: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ChallengeDailyStat(Base):
    __tablename__ = "challenge_daily_stats"
    __table_args__ = (UniqueConstraint("stat_date", name="uq_challenge_daily_stats_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stat_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ChallengeDailyWord(Base):
    __tablename__ = "challenge_daily_words"
    __table_args__ = (UniqueConstraint("challenge_date", "word_id", name="uq_challenge_daily_words_date_word"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    challenge_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"), nullable=False, index=True)
    word_list_id: Mapped[int | None] = mapped_column(ForeignKey("word_lists.id", ondelete="SET NULL"), index=True)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    last_result: Mapped[str] = mapped_column(String(16), default="correct", server_default="correct", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ChallengeSpellingAttempt(Base):
    __tablename__ = "challenge_spelling_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"), nullable=False, index=True)
    word_list_id: Mapped[int | None] = mapped_column(ForeignKey("word_lists.id", ondelete="SET NULL"), index=True)
    typed_spelling: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_spelling: Mapped[str] = mapped_column(String(255), nullable=False)
    expected_spellings: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class WrongWord(Base):
    __tablename__ = "wrong_words"
    __table_args__ = (UniqueConstraint("word_id", "wrong_date", name="uq_wrong_words_word_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"), nullable=False, index=True)
    wrong_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    wrong_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class LearningGrowthMetric(Base):
    __tablename__ = "learning_growth_metrics"
    __table_args__ = (UniqueConstraint("metric_key", name="uq_learning_growth_metrics_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    metric_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    metric_label: Mapped[str] = mapped_column(String(120), nullable=False)
    metric_value: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    metric_target: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    badge_label: Mapped[str] = mapped_column(String(120), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CacheEntry(Base):
    __tablename__ = "speakeasy_cache"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    payload: Mapped[str] = mapped_column(Text().with_variant(mysql.LONGTEXT, "mysql"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

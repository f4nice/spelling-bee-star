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
    audio_issue: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    alternate_spellings: Mapped[str | None] = mapped_column(Text)
    part_of_speech: Mapped[str | None] = mapped_column(String(120))
    english_definition: Mapped[str | None] = mapped_column(Text)
    english_definition_locked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    english_definition_audio_url: Mapped[str | None] = mapped_column(String(1000))
    chinese_definition: Mapped[str | None] = mapped_column(Text)
    chinese_definition_locked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    english_example: Mapped[str | None] = mapped_column(Text)
    english_example_locked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    english_example_audio_url: Mapped[str | None] = mapped_column(String(1000))
    image_url: Mapped[str | None] = mapped_column(String(1000))
    image_locked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    image_issue: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    source: Mapped[str | None] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text)
    enrichment_status: Mapped[str] = mapped_column(String(64), default="pending")
    enrichment_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class WordResourcePool(Base):
    __tablename__ = "word_resource_pool"
    __table_args__ = (UniqueConstraint("normalized_word", name="uq_word_resource_pool_normalized_word"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    normalized_word: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    display_word: Mapped[str | None] = mapped_column(String(128))
    phonetic: Mapped[str | None] = mapped_column(String(255))
    part_of_speech: Mapped[str | None] = mapped_column(String(120))
    english_definition: Mapped[str | None] = mapped_column(Text)
    english_definition_audio_url: Mapped[str | None] = mapped_column(String(1000))
    english_definition_audio_source: Mapped[str | None] = mapped_column(String(120))
    chinese_definition: Mapped[str | None] = mapped_column(Text)
    english_example: Mapped[str | None] = mapped_column(Text)
    english_example_audio_url: Mapped[str | None] = mapped_column(String(1000))
    english_example_audio_source: Mapped[str | None] = mapped_column(String(120))
    image_url: Mapped[str | None] = mapped_column(String(1000))
    image_source: Mapped[str | None] = mapped_column(String(120))
    american_audio_url: Mapped[str | None] = mapped_column(String(1000))
    american_audio_source: Mapped[str | None] = mapped_column(String(120))
    british_audio_url: Mapped[str | None] = mapped_column(String(1000))
    british_audio_source: Mapped[str | None] = mapped_column(String(120))
    source_word_id: Mapped[int | None] = mapped_column(Integer, index=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class WordListGroup(Base):
    __tablename__ = "word_list_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class WordList(Base):
    __tablename__ = "word_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("word_list_groups.id", ondelete="SET NULL"), index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
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


class EssayEntry(Base):
    __tablename__ = "essay_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text().with_variant(mysql.LONGTEXT, "mysql"), nullable=False)
    optimized_body: Mapped[str | None] = mapped_column(Text().with_variant(mysql.LONGTEXT, "mysql"))
    translation_body: Mapped[str | None] = mapped_column(Text().with_variant(mysql.LONGTEXT, "mysql"))
    optimized_translation_body: Mapped[str | None] = mapped_column(Text().with_variant(mysql.LONGTEXT, "mysql"))
    cover_url: Mapped[str | None] = mapped_column(String(1000))
    word_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    optimized_word_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    writing_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    writing_score_breakdown: Mapped[str | None] = mapped_column(Text().with_variant(mysql.LONGTEXT, "mysql"))
    writing_advice: Mapped[str | None] = mapped_column(Text().with_variant(mysql.LONGTEXT, "mysql"))
    best_writing_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    best_writing_points: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    ai_model: Mapped[str | None] = mapped_column(String(120))
    translation_model: Mapped[str | None] = mapped_column(String(120))
    cover_model: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class DebateSession(Base):
    __tablename__ = "debate_sessions"
    __table_args__ = (UniqueConstraint("phone", "debate_date", name="uq_debate_sessions_phone_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    debate_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    topic_key: Mapped[str] = mapped_column(String(80), nullable=False)
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    user_stance: Mapped[str] = mapped_column(String(20), nullable=False)
    ai_stance: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active", nullable=False)
    user_points: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    ai_points: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    turn_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    target_points: Mapped[int] = mapped_column(Integer, default=100, server_default="100", nullable=False)
    max_turns: Mapped[int] = mapped_column(Integer, default=6, server_default="6", nullable=False)
    transcript: Mapped[str | None] = mapped_column(Text().with_variant(mysql.LONGTEXT, "mysql"))
    final_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    final_feedback: Mapped[str | None] = mapped_column(Text().with_variant(mysql.LONGTEXT, "mysql"))
    energy_awarded: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    ai_model: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


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


class CatWorldState(Base):
    __tablename__ = "cat_world_states"
    __table_args__ = (UniqueConstraint("phone", name="uq_cat_world_states_phone"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    energy_spent: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    inventory: Mapped[str | None] = mapped_column(Text)
    cats: Mapped[str | None] = mapped_column(Text)
    room_styles: Mapped[str | None] = mapped_column(Text)
    room_layout: Mapped[str | None] = mapped_column(Text)
    current_scene_key: Mapped[str] = mapped_column(
        String(80), default="main-room", server_default="main-room", nullable=False
    )
    cat_bonds: Mapped[str | None] = mapped_column(Text)
    cat_care: Mapped[str | None] = mapped_column(Text)
    selected_cat: Mapped[str] = mapped_column(String(80), default="mimi", server_default="mimi", nullable=False)
    selected_cat_profile: Mapped[str | None] = mapped_column(String(80))
    last_play_item: Mapped[str | None] = mapped_column(String(80))
    last_played_at: Mapped[datetime | None] = mapped_column(DateTime)
    active_food_item: Mapped[str | None] = mapped_column(String(80))
    active_food_cat_id: Mapped[str | None] = mapped_column(String(80))
    active_food_at: Mapped[datetime | None] = mapped_column(DateTime)
    active_care_item: Mapped[str | None] = mapped_column(String(80))
    active_care_cat_id: Mapped[str | None] = mapped_column(String(80))
    active_care_at: Mapped[datetime | None] = mapped_column(DateTime)
    litter_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    litter_ready_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    litter_updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    litter_started_at: Mapped[datetime | None] = mapped_column(DateTime)
    damaged_items: Mapped[str | None] = mapped_column(Text)
    play_time_date: Mapped[date | None] = mapped_column(Date)
    play_time_used_seconds: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    play_time_last_seen_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CatWorldCatProfile(Base):
    __tablename__ = "cat_world_cat_profiles"
    __table_args__ = (UniqueConstraint("profile_id", name="uq_cat_world_cat_profiles_profile"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profile_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    breed_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    gender: Mapped[str] = mapped_column(String(16), nullable=False)
    pattern_key: Mapped[str] = mapped_column(String(40), nullable=False)
    feature_key: Mapped[str] = mapped_column(String(40), nullable=False)
    personality_key: Mapped[str | None] = mapped_column(String(40))
    personality_label: Mapped[str | None] = mapped_column(String(120))
    personality_traits: Mapped[str | None] = mapped_column(Text)
    nickname: Mapped[str | None] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(40), default="shop", server_default="shop", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", nullable=False)
    adopted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    escaped_at: Mapped[datetime | None] = mapped_column(DateTime)


class CatWorldEnergyGrant(Base):
    __tablename__ = "cat_world_energy_grants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    granted_by_phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class CatWorldPlayTimeGrant(Base):
    __tablename__ = "cat_world_play_time_grants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    reward_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    granted_by_phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class CatWorldScene(Base):
    __tablename__ = "cat_world_scenes"
    __table_args__ = (UniqueConstraint("scene_key", name="uq_cat_world_scenes_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scene_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    english_name: Mapped[str] = mapped_column(String(120), nullable=False)
    scene_type: Mapped[str] = mapped_column(String(80), default="indoor", server_default="indoor", nullable=False)
    world_width: Mapped[int] = mapped_column(Integer, default=1600, server_default="1600", nullable=False)
    world_height: Mapped[int] = mapped_column(Integer, default=560, server_default="560", nullable=False)
    viewport_width: Mapped[int] = mapped_column(Integer, default=1280, server_default="1280", nullable=False)
    viewport_height: Mapped[int] = mapped_column(Integer, default=560, server_default="560", nullable=False)
    floor_top: Mapped[int] = mapped_column(Integer, default=260, server_default="260", nullable=False)
    floor_bottom: Mapped[int] = mapped_column(Integer, default=522, server_default="522", nullable=False)
    config: Mapped[str | None] = mapped_column(Text)
    default_layout: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CatWorldUserScene(Base):
    __tablename__ = "cat_world_user_scenes"
    __table_args__ = (UniqueConstraint("phone", "scene_key", name="uq_cat_world_user_scenes_phone_scene"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    scene_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    layout: Mapped[str | None] = mapped_column(Text)
    room_styles: Mapped[str | None] = mapped_column(Text)
    is_unlocked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_visited_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CatWorldLimitedCatStock(Base):
    __tablename__ = "cat_world_limited_cat_stocks"
    __table_args__ = (UniqueConstraint("series_key", "cat_id", name="uq_cat_world_limited_cat_stocks_series_cat"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    series_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    cat_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    total_stock: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    claimed_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CatWorldLimitedItemStock(Base):
    __tablename__ = "cat_world_limited_item_stocks"
    __table_args__ = (UniqueConstraint("item_id", name="uq_cat_world_limited_item_stocks_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    total_stock: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    claimed_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CatWorldBlindBoxDraw(Base):
    __tablename__ = "cat_world_blind_box_draws"
    __table_args__ = (UniqueConstraint("phone", "series_key", name="uq_cat_world_blind_box_draws_phone_series"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    series_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    cat_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    energy_cost: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CatWorldShopSetting(Base):
    __tablename__ = "cat_world_shop_settings"
    __table_args__ = (UniqueConstraint("item_id", name="uq_cat_world_shop_settings_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    cost: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CatWorldGameSetting(Base):
    __tablename__ = "cat_world_game_settings"
    __table_args__ = (UniqueConstraint("setting_key", name="uq_cat_world_game_settings_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    setting_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    setting_value: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CatWorldDailyLog(Base):
    __tablename__ = "cat_world_daily_logs"
    __table_args__ = (UniqueConstraint("phone", "log_date", "cat_id", name="uq_cat_world_daily_logs_phone_date_cat"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    cat_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    favorite_decor_ids: Mapped[str | None] = mapped_column(String(255))
    mood_score: Mapped[int] = mapped_column(Integer, default=62, server_default="62", nullable=False)
    energy_score: Mapped[int] = mapped_column(Integer, default=58, server_default="58", nullable=False)
    hourly_mood_decay: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    hourly_energy_decay: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    food_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    toy_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    decor_bonus: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    agent_state: Mapped[str | None] = mapped_column(Text)
    damaged_item_id: Mapped[str | None] = mapped_column(String(80))
    last_food_item: Mapped[str | None] = mapped_column(String(80))
    last_play_item: Mapped[str | None] = mapped_column(String(80))
    last_decay_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CacheEntry(Base):
    __tablename__ = "speakeasy_cache"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    payload: Mapped[str] = mapped_column(Text().with_variant(mysql.LONGTEXT, "mysql"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AdminUserSetting(Base):
    __tablename__ = "admin_user_settings"
    __table_args__ = (UniqueConstraint("phone", name="uq_admin_user_settings_phone"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="viewer", server_default="viewer")
    permissions: Mapped[str | None] = mapped_column(Text)
    login_password_hash: Mapped[str | None] = mapped_column(Text)
    image_ai_provider: Mapped[str] = mapped_column(String(64), nullable=False, default="dashscope", server_default="dashscope")
    image_ai_model: Mapped[str] = mapped_column(String(120), nullable=False, default="wan2.7-image-pro", server_default="wan2.7-image-pro")
    audio_ai_provider: Mapped[str] = mapped_column(String(64), nullable=False, default="openai", server_default="openai")
    audio_voice_gender: Mapped[str] = mapped_column(String(16), nullable=False, default="female", server_default="female")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

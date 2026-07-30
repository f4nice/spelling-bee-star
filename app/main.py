import asyncio
from calendar import monthrange
from datetime import date, datetime, timedelta
import hmac
import html
import hashlib
from io import BytesIO
import json
import logging
import math
from pathlib import Path
import random
import re
import secrets
import sys
from threading import Lock, Thread
from typing import Any, Callable
import unicodedata
from urllib.parse import quote_plus, urlparse
from uuid import uuid4
import zipfile

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, func, inspect, or_, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, SessionLocal, engine, get_db
from app.models import (
    CacheEntry,
    CatWorldBlindBoxDraw,
    CatWorldCatProfile,
    CatWorldDailyLog,
    CatWorldEnergyGrant,
    CatWorldGameSetting,
    CatWorldLimitedCatStock,
    CatWorldPlayTimeGrant,
    CatWorldScene,
    CatWorldShopSetting,
    CatWorldState,
    CatWorldUserScene,
    ChallengeDailyStat,
    ChallengeDailyWord,
    ChallengeProgress,
    ChallengeSpellingAttempt,
    AdminUserSetting,
    DailyQuote,
    DebateSession,
    EssayEntry,
    LearningGrowthMetric,
    Word,
    WordList,
    WordListGroup,
    WordListItem,
    WordResourcePool,
    WrongWord,
)
from app.services.enrichment import enrich_word, naturalize_chinese_definition, should_refresh_chinese_definition
from app.services.excel_importer import parse_preview_from_excel, parse_words_from_preview
from app.services.audio_storage import audio_candidates_with_dictionary, is_local_audio_url, store_audio_candidate
from app.services.ai_image_generation import generate_dashscope_prompt_image, generate_word_image
from app.services.ai_tts import generate_word_ai_audio
from app.services.chinadaily import get_chinadaily_article, load_chinadaily_articles
from app.services.debate import (
    DEBATE_ARGUMENT_MAX_CHARS,
    DEBATE_CHALLENGE_ROUNDS,
    DEBATE_LEVELS,
    DEBATE_MAX_TURNS,
    DEBATE_PASS_SCORE,
    DEBATE_ROUNDS_PER_SIDE,
    DEBATE_SIDE_TARGET_POINTS,
    DEBATE_TARGET_POINTS,
    DEBATE_TURN_MAX_POINTS,
    debate_encouragement_score,
    debate_energy_reward,
    debate_result_status,
    debate_topic_for_day,
    debate_turn_with_ai,
)
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
    update_analysis_cover as update_good_words_analysis_cover,
)


PREVIEW_DIR = BASE_DIR.parent / "uploads" / "previews"
MEDIA_DIR = BASE_DIR.parent / "uploads"
IMAGE_DIR = MEDIA_DIR / "images"
AUDIO_DIR = MEDIA_DIR / "audio"
BOOK_COVER_DIR = MEDIA_DIR / "book-covers"
ESSAY_COVER_DIR = MEDIA_DIR / "essay-covers"
VERSION_MATRIX_PATH = MEDIA_DIR / "version_matrix.json"
DEFAULT_VERSION_MATRIX_PATH = BASE_DIR.parent / "VERSION_MATRIX.default.json"
settings = get_settings()
DEFAULT_RELEASE_VERSION = "BIZ-REL-20260730-005"
DEFAULT_PAGE_VERSION = "v20260730.5"
CHALLENGE_LOGGER = logging.getLogger("speakeasy.challenge")
LEGACY_MACHINE_CODE_FIELD = "machine" + "Code"
PUBLIC_ASSET_DIR = MEDIA_DIR / "generated-assets"
SPB_DETAIL_BACKFILL_BATCH_LIMIT = 300
SPB_WORD_AUDIO_SOURCE_RULE_VERSION = "lexicon-v1"
SPB_DETAIL_AUDIO_SOURCE_RULE_VERSION = "compound-v1"
SCIENCE_DISCOVERY_CACHE_DIR = MEDIA_DIR / "science-discoveries"
SCIENCE_IMAGE_VERSION = "20260629-no-text-1"
SCIENCE_DISCOVERY_DATA_VERSION = "20260629-source-mode-1"
SCIENCE_PUBLIC_CONTENT_VERSION = "v6"
SCIENCE_PUBLIC_CONTENT_TTL = timedelta(days=3650)
ESSAY_TITLE_MAX_CHARS = 120
ESSAY_BODY_MAX_CHARS = 30000
SCIENCE_SOURCE_MODE_DEFAULT = "science"
SCIENCE_SOURCE_MODE_PUBLIC_BOOKS = "public-books"
SCIENCE_SOURCE_MODES = [
    {
        "key": SCIENCE_SOURCE_MODE_DEFAULT,
        "label": "公共科学源",
        "note": "NASA / NOAA / USGS / CDC / EPA 等公共科学页面",
    },
    {
        "key": SCIENCE_SOURCE_MODE_PUBLIC_BOOKS,
        "label": "公版阅读",
        "note": "Project Gutenberg 公版英文阅读素材",
    },
]
SCIENCE_TOPIC_CACHE_KEYS = {
    "全部": "all",
    "动物": "animals",
    "植物": "plants",
    "人体": "human-body",
    "微生物": "microbes",
    "地球": "earth",
    "太空": "space",
    "工程": "engineering",
}
SCIENCE_PUBLIC_BOOK_SOURCES = [
    ("Gutendex", "https://gutendex.com/"),
    ("Project Gutenberg", "https://www.gutenberg.org/"),
]
SCIENCE_PUBLIC_BOOK_TOPIC_QUERIES = {
    "全部": "science natural history",
    "动物": "animals natural history biology",
    "植物": "botany plants natural history",
    "人体": "physiology health body",
    "微生物": "germs bacteria hygiene",
    "地球": "geology earth weather",
    "太空": "astronomy stars moon",
    "工程": "engineering mechanics electricity",
}
SCIENCE_PUBLIC_BOOK_KEYWORDS = {
    "动物": "animal, nature, observe",
    "植物": "plant, leaf, grow",
    "人体": "body, health, system",
    "微生物": "germ, microbe, hygiene",
    "地球": "earth, rock, weather",
    "太空": "astronomy, star, orbit",
    "工程": "machine, force, design",
}
SCIENCE_PUBLIC_BOOK_FALLBACKS = [
    {
        "title": "A Public-Domain Science Reader",
        "author": "Project Gutenberg collection",
        "topic": "地球",
        "summary": "This public-domain reading set collects older English science writing that can be used for careful reading, vocabulary, and evidence practice.",
        "subjects": ["Science", "Natural history", "Public domain books"],
        "sourceUrl": "https://www.gutenberg.org/ebooks/search/?query=science",
    },
    {
        "title": "A Public-Domain Astronomy Reader",
        "author": "Project Gutenberg collection",
        "topic": "太空",
        "summary": "This public-domain reading set introduces astronomy words and observations through older English nonfiction.",
        "subjects": ["Astronomy", "Stars", "Moon"],
        "sourceUrl": "https://www.gutenberg.org/ebooks/search/?query=astronomy",
    },
    {
        "title": "A Public-Domain Natural History Reader",
        "author": "Project Gutenberg collection",
        "topic": "动物",
        "summary": "This public-domain reading set uses natural history writing to practice describing animals, habitats, and observations.",
        "subjects": ["Natural history", "Animals", "Observation"],
        "sourceUrl": "https://www.gutenberg.org/ebooks/search/?query=natural%20history",
    },
]
IMAGE_SYNC_JOBS: dict[str, dict] = {}
LIST_AI_IMAGE_JOBS: dict[str, dict] = {}
SPB_SYNC_JOBS: dict[str, dict] = {}
IMPORT_PREVIEW_JOBS: dict[str, dict] = {}
SPB_SYNC_BATCH_SIZE = 80
LIST_AI_IMAGE_DEFAULT_MODEL = "wan2.6-t2i"
LIST_AI_IMAGE_MODEL_LABELS = {
    "wan2.7-image-pro": "阿里 · wan2.7-image-pro",
    "qwen-image-2.0-pro": "阿里 · qwen-image-2.0-pro",
    "wan2.6-t2i": "阿里 · wan2.6-t2i",
}
LIST_AI_IMAGE_DAILY_FREE_QUOTAS = {
    "qwen-image-2.0-pro": 100,
    "wan2.6-t2i": 0,
}
AI_IMAGE_QUOTA_CACHE_PREFIX = "ai-image:daily-quota"
GROWTH_TROPHY_ASSET_STEM = "learning-growth-trophy"
GROWTH_TROPHY_FALLBACK_IMAGE = "/static/icons/challenge-crown-transparent.png"

GROWTH_BADGE_CONFIG = [
    {
        "key": "spelling_words",
        "label": "拼写挑战",
        "badge_label": "拼写 1000 题",
        "target": 1000,
        "unit": "题",
        "tier": "gold",
    },
    {
        "key": "challenge_rounds",
        "label": "完整挑战",
        "badge_label": "完成 10 轮",
        "target": 10,
        "unit": "轮",
        "tier": "platinum",
    },
    {
        "key": "good_quotes",
        "label": "好句阅读",
        "badge_label": "阅读 100 条好句",
        "target": 100,
        "unit": "条",
        "tier": "silver",
    },
]

CAT_WORLD_DEFAULT_CAT_ID = "mimi"
CAT_WORLD_MOVEMENT_SPEED_SETTING_KEY = "movement_speed"
CAT_WORLD_DEFAULT_MOVEMENT_SPEED = 1.0
CAT_WORLD_MIN_MOVEMENT_SPEED = 0.4
CAT_WORLD_MAX_MOVEMENT_SPEED = 2.0
CAT_WORLD_MOVEMENT_SPEED_STEP = 0.05
CAT_WORLD_MALE_WEIGHT_SETTING_KEY = "male_cat_weight"
CAT_WORLD_FEMALE_WEIGHT_SETTING_KEY = "female_cat_weight"
CAT_WORLD_DEFAULT_GENDER_WEIGHT = 50
CAT_WORLD_MIN_GENDER_WEIGHT = 0
CAT_WORLD_MAX_GENDER_WEIGHT = 1000
CAT_WORLD_GENDER_WEIGHT_STEP = 5
CAT_WORLD_LITTER_ITEM_ID = "tofu-cat-litter"
CAT_WORLD_LITTER_SCOOP_ITEM_ID = "litter-scoop"
CAT_WORLD_CAT_GRASS_ITEM_ID = "cat-grass-pot"
CAT_WORLD_BATH_ITEM_ID = "cat-bath-kit"
CAT_WORLD_REPAIR_HAMMER_ITEM_ID = "repair-hammer"
CAT_WORLD_PET_REWARD_COOLDOWN_SECONDS = 60 * 60
CAT_WORLD_PLAY_TIME_TIERS = ((200, 20 * 60), (100, 10 * 60))
CAT_WORLD_PLAY_TIME_HEARTBEAT_GRACE_SECONDS = 30
CAT_WORLD_LITTER_MAX = 4
CAT_WORLD_LITTER_MOOD_PENALTY_PER_PILE = 2
CAT_WORLD_LITTER_MOOD_PENALTY_MAX = 8
CAT_WORLD_LITTER_BATH_GRACE_HOURS = 6
CAT_WORLD_LITTER_BATH_ACCELERATION_RATE = 2
CAT_WORLD_LITTER_BATH_ACCELERATION_MAX_HOURS = 72
CAT_WORLD_HUNGER_WARNING_SCORE = 8
CAT_WORLD_HUNGER_CRITICAL_HOURS = 24
CAT_WORLD_HUNGER_ESCAPE_HOURS = 72
CAT_WORLD_LOW_MOOD_WARNING_SCORE = 10
CAT_WORLD_LOW_MOOD_CRITICAL_HOURS = 48
CAT_WORLD_LOW_MOOD_ESCAPE_HOURS = 120
CAT_WORLD_CAT_PATTERNS = [
    {"key": "classic", "label": "经典原生纹"},
    {"key": "bold-stripes", "label": "深色条纹"},
    {"key": "soft-patches", "label": "柔和斑块"},
    {"key": "white-socks", "label": "白袜花纹"},
    {"key": "face-mask", "label": "重点面罩"},
]
CAT_WORLD_CAT_FEATURES = [
    {"key": "bright-eyes", "label": "圆亮眼睛"},
    {"key": "fluffy-tail", "label": "蓬松尾巴"},
    {"key": "dark-ear-tips", "label": "深色耳尖"},
    {"key": "white-bib", "label": "浅色围脖"},
    {"key": "pink-paws", "label": "粉色肉垫"},
]
CAT_WORLD_CAT_PERSONALITIES = [
    {
        "key": "quiet-observer",
        "label": "安静的观察家",
        "temperament": "calm",
        "activity": "calm",
        "routine": "先在安静角落观察，再慢慢靠近喜欢的东西",
        "traitLabel": "慢热安静，体力消耗较低，喜欢稳定的陪伴。",
        "multipliers": {"movement": 0.82, "energyDrain": 0.84, "moodDrain": 0.82, "playMoodGain": 0.92},
        "restOffset": -5,
        "sleepOffset": -1,
        "thoughts": ["我先在这里看一会儿，熟悉以后再靠近。"],
    },
    {
        "key": "clingy-shadow",
        "label": "黏人的小跟班",
        "temperament": "clingy",
        "activity": "balanced",
        "routine": "跟着你的学习位置移动，偶尔贴着家具停下来",
        "traitLabel": "很需要陪伴，摸摸和互动带来的心情收益更高。",
        "multipliers": {"movement": 0.94, "moodDrain": 1.08, "playMoodGain": 1.2},
        "restOffset": -2,
        "thoughts": ["你去哪里学习，我就想跟到哪里。"],
    },
    {
        "key": "curious-scout",
        "label": "好奇的探索员",
        "temperament": "guardian",
        "activity": "adventurous",
        "routine": "在房间边缘和新道具之间来回探索",
        "traitLabel": "好奇心旺盛，走动更多，也更容易发现新道具。",
        "multipliers": {"movement": 1.16, "energyDrain": 1.08, "playMoodGain": 1.12},
        "restOffset": 4,
        "thoughts": ["那个新东西是什么？我想绕过去看看。"],
    },
    {
        "key": "chatty-listener",
        "label": "话多的倾听者",
        "temperament": "chatty",
        "activity": "chatty",
        "routine": "听见朗读声就靠近，并用叫声回应",
        "traitLabel": "喜欢声音和回应，互动收益高，独处时心情下降更快。",
        "multipliers": {"movement": 1.08, "moodDrain": 1.18, "playMoodGain": 1.24},
        "restOffset": 3,
        "thoughts": ["我听见你读英文了，再读一句给我听吧。"],
    },
    {
        "key": "gentle-dreamer",
        "label": "温柔的做梦家",
        "temperament": "gentle",
        "activity": "gentle",
        "routine": "在软垫、猫窝和书架旁慢慢换地方休息",
        "traitLabel": "温柔省体力，休息充分，吃东西时恢复更明显。",
        "multipliers": {"movement": 0.76, "energyDrain": 0.78, "moodDrain": 0.82, "foodEnergyGain": 1.12},
        "restOffset": -6,
        "sleepOffset": -1,
        "wakeOffset": 1,
        "thoughts": ["今天适合慢一点，我会在旁边陪着。"],
    },
    {
        "key": "playful-spark",
        "label": "贪玩的开心果",
        "temperament": "chatty",
        "activity": "playful",
        "routine": "在玩具和家具之间寻找下一次互动",
        "traitLabel": "精力活跃，玩耍心情收益很高，也会更快消耗体力。",
        "multipliers": {"movement": 1.2, "energyDrain": 1.2, "playMoodGain": 1.3},
        "restOffset": 7,
        "thoughts": ["先玩一下，再陪你继续学习也来得及。"],
    },
    {
        "key": "steady-guardian",
        "label": "可靠的守护者",
        "temperament": "guardian",
        "activity": "adventurous",
        "routine": "沿着入口和房间边界巡逻，确认一切正常",
        "traitLabel": "行动稳定、心情坚韧，喜欢巡视宽阔场景。",
        "multipliers": {"movement": 1.06, "energyDrain": 1.08, "moodDrain": 0.82},
        "restOffset": 3,
        "thoughts": ["房间交给我巡视，你安心完成今天的目标。"],
    },
    {
        "key": "independent-reader",
        "label": "独立的阅读者",
        "temperament": "calm",
        "activity": "calm",
        "routine": "自己挑选安静位置，长时间专注地待着",
        "traitLabel": "独处也很稳定，适合长时间安静陪读。",
        "multipliers": {"movement": 0.88, "energyDrain": 0.86, "moodDrain": 0.7},
        "restOffset": -3,
        "thoughts": ["不用一直陪我，我们可以各自安静读一会儿。"],
    },
    {
        "key": "night-patroller",
        "label": "精神的夜巡员",
        "temperament": "guardian",
        "activity": "adventurous",
        "routine": "白天多休息，夜里沿着房间边界巡视",
        "traitLabel": "偏爱夜间活动，夜里更专注，白天容易打盹。",
        "multipliers": {"movement": 1.08, "energyDrain": 1.02, "moodDrain": 0.9},
        "restOffset": 2,
        "nightOwl": True,
        "sleepStart": 2,
        "sleepEnd": 9,
        "thoughts": ["夜里很安静，正适合我把房间巡一遍。"],
    },
    {
        "key": "sunny-companion",
        "label": "开朗的陪伴员",
        "temperament": "clingy",
        "activity": "balanced",
        "routine": "在你和喜欢的家具之间轻快地来回走动",
        "traitLabel": "情绪开朗、适应力强，喜欢频繁但轻松的互动。",
        "multipliers": {"movement": 1.02, "moodDrain": 0.92, "playMoodGain": 1.14},
        "thoughts": ["今天看起来很不错，我们一起做点开心的事吧。"],
    },
]
CAT_WORLD_CAT_PATTERN_BY_KEY = {item["key"]: item for item in CAT_WORLD_CAT_PATTERNS}
CAT_WORLD_CAT_FEATURE_BY_KEY = {item["key"]: item for item in CAT_WORLD_CAT_FEATURES}
CAT_WORLD_CAT_PERSONALITY_BY_KEY = {item["key"]: item for item in CAT_WORLD_CAT_PERSONALITIES}
CAT_WORLD_SHOP = [
    {
        "id": "daily-kibble",
        "category": "food",
        "foodType": "basic",
        "label": "日常猫粮",
        "englishName": "Daily Kibble",
        "cost": 30,
        "mood": 1,
        "catEnergy": 10,
        "durationMinutes": 15,
        "description": "便宜耐放的基础口粮，所有猫都能吃，恢复量较少。",
    },
    {
        "id": "chicken-broth",
        "category": "food",
        "foodType": "basic",
        "label": "鸡肉汤饭",
        "englishName": "Chicken Broth Rice",
        "cost": 45,
        "mood": 2,
        "catEnergy": 14,
        "durationMinutes": 20,
        "description": "温热清淡的基础餐，适合平时少量补充体力。",
    },
    {
        "id": "egg-yolk-bites",
        "category": "food",
        "foodType": "basic",
        "label": "蛋黄小酥粒",
        "englishName": "Egg Yolk Bites",
        "cost": 55,
        "mood": 3,
        "catEnergy": 18,
        "durationMinutes": 25,
        "description": "一小份酥粒基础餐，恢复不高，但比日常猫粮更香。",
    },
    {
        "id": "salmon-bowl",
        "category": "food",
        "foodType": "specialty",
        "favoriteEnergyMultiplier": 1.45,
        "label": "三文鱼能量碗",
        "englishName": "Salmon Bowl",
        "cost": 60,
        "mood": 6,
        "catEnergy": 28,
        "durationMinutes": 30,
        "description": "给猫咪补充一顿香香的学习奖励餐。",
    },
    {
        "id": "tuna-can",
        "category": "food",
        "foodType": "specialty",
        "favoriteEnergyMultiplier": 1.45,
        "label": "金枪鱼罐头",
        "englishName": "Tuna Can",
        "cost": 90,
        "mood": 8,
        "catEnergy": 36,
        "durationMinutes": 45,
        "description": "适合完成一轮挑战后打开的小奖励。",
    },
    {
        "id": "goat-milk",
        "category": "food",
        "foodType": "specialty",
        "favoriteEnergyMultiplier": 1.45,
        "label": "羊奶布丁",
        "englishName": "Goat Milk Pudding",
        "cost": 120,
        "mood": 10,
        "catEnergy": 45,
        "durationMinutes": 60,
        "description": "柔软、甜一点，心情会明显变好。",
    },
    {
        "id": "silver-cod-stew",
        "category": "food",
        "foodType": "specialty",
        "favoriteEnergyMultiplier": 1.45,
        "label": "银鳕鱼南瓜煲",
        "englishName": "Silver Cod Stew",
        "cost": 105,
        "mood": 7,
        "catEnergy": 34,
        "durationMinutes": 40,
        "description": "细腻安静的特色餐，英短银渐层吃后恢复得更快。",
    },
    {
        "id": "chicken-star-bites",
        "category": "food",
        "foodType": "specialty",
        "favoriteEnergyMultiplier": 1.45,
        "label": "鸡肉星星冻干",
        "englishName": "Chicken Star Bites",
        "cost": 115,
        "mood": 8,
        "catEnergy": 38,
        "durationMinutes": 45,
        "description": "脆脆的高能特色餐，爱活动的暹罗猫吃后恢复得更快。",
    },
    {
        "id": CAT_WORLD_LITTER_SCOOP_ITEM_ID,
        "category": "consumable",
        "useType": "litter-clean",
        "label": "一次性铲屎铲",
        "englishName": "Litter Scoop",
        "cost": 35,
        "mood": 0,
        "description": "点击活动室里的猫屎时自动消耗 1 把，每把清理一堆。",
    },
    {
        "id": CAT_WORLD_LITTER_ITEM_ID,
        "category": "consumable",
        "useType": "litter-prevent",
        "label": "豆腐猫砂包",
        "englishName": "Tofu Cat Litter",
        "cost": 55,
        "mood": 0,
        "description": "点击后放进活动室，猫咪下次排泄时自动使用并处理，随后从房间消失。",
    },
    {
        "id": "grooming-brush",
        "category": "consumable",
        "useType": "cat-care",
        "label": "一次性顺毛梳",
        "englishName": "Grooming Brush",
        "cost": 80,
        "mood": 14,
        "bond": 4,
        "description": "给当前猫咪认真梳一次毛，立即增加心情和亲密度。",
    },
    {
        "id": "care-wipes",
        "category": "consumable",
        "useType": "cat-care",
        "label": "眼耳护理湿巾",
        "englishName": "Care Wipes",
        "cost": 60,
        "mood": 8,
        "catEnergy": 2,
        "bond": 2,
        "description": "给当前猫咪做一次清洁护理，恢复少量体力并增加心情。",
    },
    {
        "id": CAT_WORLD_BATH_ITEM_ID,
        "category": "consumable",
        "useType": "cat-bath",
        "label": "猫咪泡泡浴套装",
        "englishName": "Cat Bath Kit",
        "cost": 150,
        "mood": 16,
        "bond": 5,
        "description": "给当前猫咪洗一次澡，消耗 1 套，炸毛会恢复，重新计算下次洗澡日期。",
    },
    {
        "id": "room-deodorizer",
        "category": "consumable",
        "useType": "room-care",
        "label": "房间除味喷雾",
        "englishName": "Room Deodorizer",
        "cost": 90,
        "mood": 5,
        "description": "一次为房间除味，让所有已拥有猫咪的心情都增加一点。",
    },
    {
        "id": CAT_WORLD_CAT_GRASS_ITEM_ID,
        "category": "consumable",
        "useType": "room-place",
        "label": "猫草小盆",
        "englishName": "Cat Grass Pot",
        "cost": 120,
        "mood": 12,
        "durationMinutes": 20,
        "bond": 3,
        "description": "放进活动室 20 分钟，当前猫咪会慢慢靠近闻一闻并增加心情。",
    },
    {
        "id": CAT_WORLD_REPAIR_HAMMER_ITEM_ID,
        "category": "consumable",
        "useType": "repair-tool",
        "label": "一次性维修锤",
        "englishName": "Repair Hammer",
        "cost": 100,
        "mood": 0,
        "description": "维修损坏道具时自动消耗 1 把；只有维修成功后才会从背包扣除。",
    },
    {
        "id": "rolling-ball",
        "category": "toy",
        "label": "滚滚球",
        "englishName": "Rolling Ball",
        "cost": 80,
        "mood": 7,
        "description": "轻轻一点，猫咪就会追着跑。",
    },
    {
        "id": "feather-wand",
        "category": "toy",
        "label": "羽毛逗猫棒",
        "englishName": "Feather Wand",
        "cost": 110,
        "mood": 10,
        "description": "用来陪猫咪玩一会儿，互动感更强。",
    },
    {
        "id": "scratch-board",
        "category": "toy",
        "label": "猫抓板",
        "englishName": "Scratch Board",
        "cost": 160,
        "mood": 14,
        "description": "学习获得能量后，可以买来逗她玩。",
    },
    {
        "id": "yarn-basket",
        "category": "toy",
        "label": "彩色毛线篮",
        "englishName": "Yarn Basket",
        "cost": 130,
        "mood": 11,
        "description": "一篮不会滚远的彩色毛线球，适合慢慢拨着玩。",
    },
    {
        "id": "cloud-rug",
        "category": "decor",
        "label": "云朵地毯",
        "englishName": "Cloud Rug",
        "cost": 180,
        "mood": 5,
        "description": "把猫窝旁边铺得更软一点。",
    },
    {
        "id": "sun-window",
        "category": "decor",
        "label": "阳光窗台",
        "englishName": "Sunny Window",
        "cost": 220,
        "mood": 8,
        "description": "猫咪最喜欢晒太阳的安静角落。",
    },
    {
        "id": "book-shelf",
        "category": "decor",
        "label": "英文书架",
        "englishName": "English Bookshelf",
        "cost": 260,
        "mood": 9,
        "description": "把读过的书和好句收进猫咪房间。",
    },
    {
        "id": "study-desk",
        "category": "decor",
        "label": "英文书桌",
        "englishName": "Study Desk",
        "cost": 320,
        "mood": 10,
        "description": "给猫咪准备一个可以陪你背单词的小书桌。",
    },
    {
        "id": "reading-lamp",
        "category": "decor",
        "label": "阅读台灯",
        "englishName": "Reading Lamp",
        "cost": 180,
        "mood": 6,
        "description": "晚上练英文时，房间会亮起一盏温柔的小灯。",
    },
    {
        "id": "word-gallery",
        "category": "decor",
        "label": "单词挂画",
        "englishName": "Word Gallery",
        "cost": 240,
        "mood": 7,
        "description": "把今天记住的词挂在墙上，房间会更像学习基地。",
    },
    {
        "id": "window-hammock",
        "category": "decor",
        "label": "窗边吊床",
        "englishName": "Window Hammock",
        "cost": 280,
        "mood": 9,
        "description": "一张悬在窗边的软吊床，适合安静休息和观察房间。",
    },
    {
        "id": "felt-cat-bed",
        "category": "decor",
        "label": "毛毡猫窝",
        "englishName": "Felt Cat Bed",
        "cost": 240,
        "mood": 8,
        "description": "柔软包围的小猫窝，体力低的猫会更愿意靠近休息。",
    },
    {
        "id": "moon-cushion",
        "category": "decor",
        "label": "月亮软垫",
        "englishName": "Moon Cushion",
        "cost": 210,
        "mood": 7,
        "description": "放在地板上的月亮形软垫，适合安静趴着陪读。",
    },
    {
        "id": "cat-climbing-tree",
        "category": "decor",
        "label": "原木猫爬架",
        "englishName": "Cat Climbing Tree",
        "cost": 360,
        "mood": 12,
        "description": "高高的抓柱、平台和小窝，活泼的猫会在附近巡逻。",
    },
    {
        "id": "mini-fountain",
        "category": "decor",
        "label": "循环饮水机",
        "englishName": "Mini Fountain",
        "cost": 300,
        "mood": 9,
        "description": "持续冒出清水的小饮水机，让房间听起来更安静。",
    },
    {
        "id": "bubble-bathtub",
        "category": "decor",
        "label": "泡泡浴缸",
        "englishName": "Bubble Bathtub",
        "cost": 340,
        "mood": 11,
        "description": "点击浴缸后，猫咪会慢慢走进去，用一套泡泡浴用品洗干净。",
    },
    {
        "id": "rug-candy",
        "category": "color",
        "label": "地毯莓粉色",
        "englishName": "Candy Rug",
        "cost": 80,
        "mood": 2,
        "description": "给云朵地毯换成甜甜的莓粉色。",
        "targetDecor": "cloud-rug",
        "tone": "candy",
    },
    {
        "id": "rug-sky",
        "category": "color",
        "label": "地毯天空蓝",
        "englishName": "Sky Rug",
        "cost": 80,
        "mood": 2,
        "description": "给云朵地毯换成清爽的天空蓝。",
        "targetDecor": "cloud-rug",
        "tone": "sky",
    },
    {
        "id": "desk-cherry",
        "category": "color",
        "label": "书桌樱桃木",
        "englishName": "Cherry Desk",
        "cost": 110,
        "mood": 2,
        "description": "给英文书桌换成暖暖的樱桃木色。",
        "targetDecor": "study-desk",
        "tone": "cherry",
    },
    {
        "id": "desk-mint",
        "category": "color",
        "label": "书桌薄荷绿",
        "englishName": "Mint Desk",
        "cost": 110,
        "mood": 2,
        "description": "给英文书桌换成清新的薄荷绿色。",
        "targetDecor": "study-desk",
        "tone": "mint",
    },
    {
        "id": "shelf-lavender",
        "category": "color",
        "label": "书架薰衣草",
        "englishName": "Lavender Shelf",
        "cost": 120,
        "mood": 2,
        "description": "给英文书架换成柔和的薰衣草色。",
        "targetDecor": "book-shelf",
        "tone": "lavender",
    },
    {
        "id": "window-sunset",
        "category": "color",
        "label": "窗台晚霞色",
        "englishName": "Sunset Window",
        "cost": 120,
        "mood": 2,
        "description": "给阳光窗台换成黄昏晚霞的颜色。",
        "targetDecor": "sun-window",
        "tone": "sunset",
    },
    {
        "id": "lamp-moon",
        "category": "color",
        "label": "台灯月光色",
        "englishName": "Moon Lamp",
        "cost": 90,
        "mood": 2,
        "description": "给阅读台灯换成淡淡的月光色。",
        "targetDecor": "reading-lamp",
        "tone": "moon",
    },
    {
        "id": "gallery-peach",
        "category": "color",
        "label": "挂画蜜桃色",
        "englishName": "Peach Gallery",
        "cost": 100,
        "mood": 2,
        "description": "给单词挂画换成柔和的蜜桃色。",
        "targetDecor": "word-gallery",
        "tone": "peach",
    },
    {
        "id": "hammock-lavender",
        "category": "color",
        "label": "吊床薰衣草",
        "englishName": "Lavender Hammock",
        "cost": 100,
        "mood": 2,
        "description": "给窗边吊床换成柔和的薰衣草色。",
        "targetDecor": "window-hammock",
        "tone": "lavender",
    },
    {
        "id": "hammock-mint",
        "category": "color",
        "label": "吊床薄荷绿",
        "englishName": "Mint Hammock",
        "cost": 100,
        "mood": 2,
        "description": "给窗边吊床换成清新的薄荷绿色。",
        "targetDecor": "window-hammock",
        "tone": "mint",
    },
    {
        "id": "limited-cat-blind-box",
        "category": "blind-box",
        "label": "限定猫咪盲盒",
        "englishName": "Limited Cat Mystery Box",
        "cost": 10000,
        "mood": 0,
        "seriesKey": "turkey-water-2026-01",
        "description": "土耳其地区第一期限定盲盒，每个账号本期只能开启一次，随机获得土耳其梵猫或土耳其安哥拉猫。",
    },
    {
        "id": "cat-collection-handbook",
        "category": "handbook",
        "handbookType": "cats",
        "label": "猫咪收集手册",
        "englishName": "Cat Collection Handbook",
        "cost": 10000,
        "mood": 0,
        "description": "永久解锁猫咪卡册，查看地区分期、R/SR/SSR 稀有度和自己的收集进度。",
    },
    {
        "id": "cat-food-handbook",
        "category": "handbook",
        "handbookType": "food",
        "label": "猫咪食物手册",
        "englishName": "Cat Food Handbook",
        "cost": 10000,
        "mood": 0,
        "description": "永久解锁食物图鉴，集中查看食物效果、偏爱猫咪和背包数量。",
    },
    {
        "id": CAT_WORLD_DEFAULT_CAT_ID,
        "category": "cat",
        "label": "咪咪",
        "englishName": "Mimi",
        "cost": 420,
        "mood": 8,
        "description": "第一只陪你学习的猫；离家后可以重新领养。",
    },
    {
        "id": "british-shorthair",
        "category": "cat",
        "label": "英短银渐层",
        "englishName": "British Shorthair",
        "cost": 520,
        "mood": 8,
        "description": "圆脸、安静，适合陪你背长单词。",
    },
    {
        "id": "siamese",
        "category": "cat",
        "label": "暹罗猫",
        "englishName": "Siamese",
        "cost": 620,
        "mood": 10,
        "description": "聪明又爱说话，听你朗读英文很认真。",
    },
    {
        "id": "ragdoll",
        "category": "cat",
        "label": "布偶猫",
        "englishName": "Ragdoll",
        "cost": 680,
        "mood": 11,
        "description": "温柔黏人，适合阅读日一起出现。",
    },
    {
        "id": "maine-coon",
        "category": "cat",
        "label": "缅因猫",
        "englishName": "Maine Coon",
        "cost": 800,
        "mood": 13,
        "description": "像猫咪世界里的守护者，适合大目标解锁。",
    },
]
CAT_WORLD_CATS = [
    {
        "id": CAT_WORLD_DEFAULT_CAT_ID,
        "label": "咪咪",
        "englishName": "Mimi",
        "rarity": "Starter",
        "description": "第一只陪你学习的猫。",
        "personality": "黏人的学习搭子",
        "traits": {
            "activity": "balanced",
            "movement": 0.9,
            "energyDrain": 0.85,
            "moodDrain": 0.75,
            "playMoodGain": 1.1,
            "foodEnergyGain": 1.0,
            "restThreshold": 30,
            "sleepStart": 23,
            "sleepEnd": 7,
            "nightOwl": False,
            "routine": "贴着书桌和地毯慢慢巡逻",
            "temperament": "clingy",
            "label": "慢热黏人，消耗低，摸摸后心情涨得快。",
        },
        "thoughts": [
            "检测到你今天练过单词，想靠近一点听。",
            "如果你读英文，我会把尾巴调成陪读模式。",
            "能量值很香，适合换一口小鱼干。",
        ],
    },
    {
        "id": "british-shorthair",
        "label": "英短银渐层",
        "englishName": "British Shorthair",
        "rarity": "Famous Cat",
        "description": "圆脸、安静，适合陪你背长单词。",
        "personality": "冷静的词库管理员",
        "traits": {
            "activity": "calm",
            "movement": 0.72,
            "energyDrain": 0.68,
            "moodDrain": 0.62,
            "playMoodGain": 0.9,
            "foodEnergyGain": 0.95,
            "restThreshold": 26,
            "sleepStart": 22,
            "sleepEnd": 8,
            "nightOwl": False,
            "routine": "检查书架和窗台有没有摆整齐",
            "temperament": "calm",
            "label": "安静省电，走得慢，适合长时间陪读。",
        },
        "thoughts": [
            "正在把新单词按难度排好队。",
            "建议先复习三个旧词，再挑战一个新词。",
            "情绪稳定，适合长时间陪读。",
        ],
    },
    {
        "id": "siamese",
        "label": "暹罗猫",
        "englishName": "Siamese",
        "rarity": "Famous Cat",
        "description": "聪明又爱说话，听你朗读英文很认真。",
        "personality": "话多的语音小助手",
        "traits": {
            "activity": "chatty",
            "movement": 1.18,
            "energyDrain": 1.22,
            "moodDrain": 1.35,
            "playMoodGain": 1.35,
            "foodEnergyGain": 1.06,
            "restThreshold": 42,
            "sleepStart": 1,
            "sleepEnd": 7,
            "nightOwl": True,
            "routine": "夜里也会去逗逗滚滚球",
            "temperament": "chatty",
            "label": "爱跑爱说话，能量掉得快，但互动心情涨得最多。",
        },
        "thoughts": [
            "我听见了一个发音，可以再读一遍吗？",
            "朗读会让能量灯亮得更快。",
            "正在准备一串很想说的英文例句。",
        ],
    },
    {
        "id": "ragdoll",
        "label": "布偶猫",
        "englishName": "Ragdoll",
        "rarity": "Famous Cat",
        "description": "温柔黏人，适合阅读日一起出现。",
        "personality": "温柔的阅读陪伴员",
        "traits": {
            "activity": "gentle",
            "movement": 0.62,
            "energyDrain": 0.58,
            "moodDrain": 0.5,
            "playMoodGain": 0.82,
            "foodEnergyGain": 1.18,
            "restThreshold": 24,
            "sleepStart": 22,
            "sleepEnd": 9,
            "nightOwl": False,
            "routine": "在云朵地毯边趴着陪读",
            "temperament": "gentle",
            "label": "最省体力，喜欢慢慢走，吃东西恢复更明显。",
        },
        "thoughts": [
            "今天适合慢慢读一段好句。",
            "你的学习节奏很好，我想在旁边趴着。",
            "如果累了，就摸摸我再继续。",
        ],
    },
    {
        "id": "maine-coon",
        "label": "缅因猫",
        "englishName": "Maine Coon",
        "rarity": "Famous Cat",
        "description": "像猫咪世界里的守护者，适合大目标解锁。",
        "personality": "冒险型房间守护者",
        "traits": {
            "activity": "adventurous",
            "movement": 1.08,
            "energyDrain": 1.32,
            "moodDrain": 1.02,
            "playMoodGain": 1.12,
            "foodEnergyGain": 1.08,
            "restThreshold": 46,
            "sleepStart": 0,
            "sleepEnd": 6,
            "nightOwl": True,
            "routine": "绕房间边界巡逻，守着入口",
            "temperament": "guardian",
            "label": "体型大、巡逻多，能量消耗最高，心情比较稳。",
        },
        "thoughts": [
            "目标已锁定：把今天的挑战完成。",
            "能量充足，可以扩建一格房间。",
            "我负责守门，你负责把单词拿下。",
        ],
    },
]
CAT_WORLD_BLIND_BOX_SERIES = [
    {
        "key": "china-heritage-2026-01",
        "label": "东方猫韵 · 中国站",
        "region": "中国",
        "issue": "第一期",
        "description": "本期只收录 3 种中国地区代表猫咪，每个账号限开一次。",
        "shopItemId": "limited-cat-blind-box",
        "cats": [
            {
                "totalStock": 120,
                "cat": {
                    "id": "china-lihua", "label": "中华狸花猫", "englishName": "Chinese Li Hua",
                    "rarity": "R", "limited": True, "region": "中国",
                    "description": "灵活、机敏的中国本土猫，擅长巡视宽阔场景。", "personality": "可靠的院落巡查员",
                    "traits": {"activity": "adventurous", "movement": 1.18, "energyDrain": 1.0, "moodDrain": 0.82, "playMoodGain": 1.18, "foodEnergyGain": 1.0, "restThreshold": 36, "sleepStart": 23, "sleepEnd": 7, "nightOwl": False, "routine": "从院子到书桌快速巡查", "temperament": "guardian", "label": "行动敏捷、状态均衡，适合探索多场景。"},
                    "thoughts": ["院子和房间都检查好了。", "再学一个词，我就继续巡逻。", "今天的目标要稳稳拿下。"],
                },
            },
            {
                "totalStock": 45,
                "cat": {
                    "id": "linqing-lion", "label": "临清狮猫", "englishName": "Linqing Lion Cat",
                    "rarity": "SR", "limited": True, "region": "中国",
                    "description": "来自山东临清的长毛猫，安静从容，喜欢陪你读长故事。", "personality": "温和的长篇陪读员",
                    "traits": {"activity": "gentle", "movement": 0.8, "energyDrain": 0.72, "moodDrain": 0.62, "playMoodGain": 0.98, "foodEnergyGain": 1.16, "restThreshold": 28, "sleepStart": 22, "sleepEnd": 8, "nightOwl": False, "routine": "在软垫和书架附近安静陪读", "temperament": "gentle", "label": "消耗较低、陪读稳定，吃东西恢复更明显。"},
                    "thoughts": ["慢慢读，我会一直在旁边。", "长句子也可以分成几小段。", "书架旁边很适合听故事。"],
                },
            },
            {
                "totalStock": 15,
                "cat": {
                    "id": "jianzhou-cat", "label": "简州猫", "englishName": "Jianzhou Cat",
                    "rarity": "SSR", "limited": True, "region": "中国",
                    "description": "来自四川简州的珍稀限定猫，聪明活跃，对朗读声格外敏感。", "personality": "敏锐的语音探索家",
                    "traits": {"activity": "chatty", "movement": 1.12, "energyDrain": 0.9, "moodDrain": 0.76, "playMoodGain": 1.35, "foodEnergyGain": 1.08, "restThreshold": 34, "sleepStart": 1, "sleepEnd": 8, "nightOwl": True, "routine": "循着朗读声探索每一层房间", "temperament": "chatty", "label": "稀有且敏锐，互动心情收益最高。"},
                    "thoughts": ["我听见了一个很漂亮的发音。", "二楼还有新的句子等着探索。", "再读一遍，我会记住这个声音。"],
                },
            },
        ],
    },
    {
        "key": "japan-bobtail-2026-01",
        "label": "和猫纪行 · 日本站",
        "region": "日本",
        "issue": "第一期",
        "description": "本期限定日本短尾猫，全站 100 只，每个账号限开一次。",
        "shopItemId": "limited-cat-blind-box",
        "cats": [
            {
                "totalStock": 100,
                "cat": {
                    "id": "japanese-bobtail",
                    "label": "日本短尾猫",
                    "englishName": "Japanese Bobtail",
                    "rarity": "SSR",
                    "limited": True,
                    "region": "日本",
                    "description": "来自日本的短尾猫，尾巴像一团小绒球，脚步轻快又爱观察房间。",
                    "personality": "轻巧的缘侧观察员",
                    "traits": {
                        "activity": "adventurous",
                        "movement": 1.1,
                        "energyDrain": 0.9,
                        "moodDrain": 0.72,
                        "playMoodGain": 1.24,
                        "foodEnergyGain": 1.04,
                        "restThreshold": 32,
                        "sleepStart": 23,
                        "sleepEnd": 7,
                        "nightOwl": False,
                        "routine": "沿着窗台和房间边缘轻快巡视",
                        "temperament": "adventurous",
                        "label": "脚步轻快、心情稳定，喜欢在窗台附近观察。",
                    },
                    "thoughts": [
                        "窗边的光落下来，正适合安静听你读一段。",
                        "短尾巴晃了一下，发现了一个新单词。",
                        "房间巡视完毕，可以陪你继续学习。",
                    ],
                },
            },
        ],
    },
    {
        "key": "turkey-water-2026-01",
        "label": "湖光白影 · 土耳其站",
        "region": "土耳其",
        "issue": "第一期",
        "description": "本期收录亲水的土耳其梵猫和优雅的土耳其安哥拉猫，全站 100 只，每个账号限开一次。",
        "shopItemId": "limited-cat-blind-box",
        "cats": [
            {
                "totalStock": 80,
                "cat": {
                    "id": "turkish-van",
                    "label": "土耳其梵猫",
                    "englishName": "Turkish Van",
                    "rarity": "SR",
                    "limited": True,
                    "region": "土耳其",
                    "description": "来自凡湖地区的亲水猫咪，白色身体配着醒目的头尾色块，喜欢浴缸和流动的水。",
                    "personality": "好奇的水边探索员",
                    "traits": {
                        "activity": "adventurous",
                        "movement": 1.12,
                        "energyDrain": 0.96,
                        "moodDrain": 0.74,
                        "playMoodGain": 1.28,
                        "foodEnergyGain": 1.04,
                        "restThreshold": 33,
                        "sleepStart": 23,
                        "sleepEnd": 7,
                        "nightOwl": False,
                        "routine": "沿着浴缸和饮水机巡视水花",
                        "temperament": "adventurous",
                        "label": "喜欢玩水、脚步轻快，靠近浴缸和饮水机时更开心。",
                    },
                    "thoughts": [
                        "听见水声了，我想过去看看。",
                        "凡湖的风和今天的新单词一样清亮。",
                        "浴缸边很适合甩甩尾巴再继续陪读。",
                    ],
                },
            },
            {
                "totalStock": 20,
                "cat": {
                    "id": "turkish-angora",
                    "label": "土耳其安哥拉猫",
                    "englishName": "Turkish Angora",
                    "rarity": "SSR",
                    "limited": True,
                    "region": "土耳其",
                    "description": "轻盈的长毛猫，尾巴蓬松，喜欢在窗边和书架旁安静观察你的学习节奏。",
                    "personality": "优雅的晨光观察员",
                    "traits": {
                        "activity": "gentle",
                        "movement": 0.92,
                        "energyDrain": 0.7,
                        "moodDrain": 0.58,
                        "playMoodGain": 1.12,
                        "foodEnergyGain": 1.14,
                        "restThreshold": 27,
                        "sleepStart": 22,
                        "sleepEnd": 8,
                        "nightOwl": False,
                        "routine": "在窗台与书架之间轻轻踱步",
                        "temperament": "gentle",
                        "label": "长毛轻盈、情绪稳定，喜欢安静的窗边和阅读角。",
                    },
                    "thoughts": [
                        "晨光正好，我想听你慢慢读一页。",
                        "蓬松的尾巴已经替新单词做了标记。",
                        "安静学习的时候，我会守在窗边。",
                    ],
                },
            },
        ],
    },
]
CAT_WORLD_CURRENT_BLIND_BOX_SERIES_KEY = "turkey-water-2026-01"
CAT_WORLD_BLIND_BOX_SERIES_BY_KEY = {series["key"]: series for series in CAT_WORLD_BLIND_BOX_SERIES}
CAT_WORLD_LIMITED_CAT_SEEDS = [
    {**cat_seed, "seriesKey": series["key"]}
    for series in CAT_WORLD_BLIND_BOX_SERIES
    for cat_seed in series["cats"]
]
CAT_WORLD_CATS.extend(seed["cat"] for seed in CAT_WORLD_LIMITED_CAT_SEEDS)
CAT_WORLD_SHOP_BY_ID = {item["id"]: item for item in CAT_WORLD_SHOP}
CAT_WORLD_CAT_BY_ID = {item["id"]: item for item in CAT_WORLD_CATS}
CAT_WORLD_DECOR_LABELS = {
    item["id"]: item["label"]
    for item in CAT_WORLD_SHOP
    if item["category"] == "decor"
}
CAT_WORLD_LAYOUT_ITEM_LABELS = {
    item["id"]: item["label"]
    for item in CAT_WORLD_SHOP
    if item["category"] in {"decor", "toy"}
}
CAT_WORLD_DECOR_FAVORITE_CAT = {
    "book-shelf": CAT_WORLD_DEFAULT_CAT_ID,
    "cloud-rug": "ragdoll",
    "sun-window": "british-shorthair",
    "study-desk": "siamese",
    "reading-lamp": "maine-coon",
    "word-gallery": CAT_WORLD_DEFAULT_CAT_ID,
    "window-hammock": "british-shorthair",
    "felt-cat-bed": "ragdoll",
    "moon-cushion": CAT_WORLD_DEFAULT_CAT_ID,
    "cat-climbing-tree": "maine-coon",
    "mini-fountain": "siamese",
    "bubble-bathtub": "ragdoll",
}
CAT_WORLD_EXTRA_DECOR_FAVORITES = {
    "turkish-van": ["mini-fountain", "bubble-bathtub"],
    "turkish-angora": ["sun-window", "book-shelf"],
}
CAT_WORLD_TOY_FAVORITE_CAT = {
    "rolling-ball": "siamese",
    "feather-wand": "maine-coon",
    "scratch-board": "british-shorthair",
    "yarn-basket": CAT_WORLD_DEFAULT_CAT_ID,
}
CAT_WORLD_FOOD_FAVORITE_CAT = {
    "salmon-bowl": CAT_WORLD_DEFAULT_CAT_ID,
    "tuna-can": "maine-coon",
    "goat-milk": "ragdoll",
    "silver-cod-stew": "british-shorthair",
    "chicken-star-bites": "siamese",
}
CAT_WORLD_ITEM_FAVORITE_CAT = {
    **CAT_WORLD_DECOR_FAVORITE_CAT,
    **CAT_WORLD_TOY_FAVORITE_CAT,
    **CAT_WORLD_FOOD_FAVORITE_CAT,
}
CAT_WORLD_DECOR_DEFAULT_LAYOUT = {
    "sun-window": {"x": 5, "y": 5},
    "book-shelf": {"x": 73, "y": 8},
    "cloud-rug": {"x": 17, "y": 77},
    "study-desk": {"x": 43, "y": 62},
    "reading-lamp": {"x": 62, "y": 47},
    "word-gallery": {"x": 31, "y": 31},
    "window-hammock": {"x": 8, "y": 49},
    "felt-cat-bed": {"x": 70, "y": 75},
    "moon-cushion": {"x": 31, "y": 80},
    "cat-climbing-tree": {"x": 86, "y": 48},
    "mini-fountain": {"x": 54, "y": 76},
    "bubble-bathtub": {"x": 77, "y": 58},
}
CAT_WORLD_TOY_DEFAULT_LAYOUT = {
    "rolling-ball": {"x": 24, "y": 70},
    "scratch-board": {"x": 7, "y": 75},
    "feather-wand": {"x": 83, "y": 45},
    "yarn-basket": {"x": 55, "y": 78},
}
CAT_WORLD_ROOM_DEFAULT_LAYOUT = {
    **CAT_WORLD_DECOR_DEFAULT_LAYOUT,
    **CAT_WORLD_TOY_DEFAULT_LAYOUT,
}
CAT_WORLD_DEFAULT_SCENE_KEY = "main-room"
CAT_WORLD_SCENE_SEEDS = [
    {
        "sceneKey": CAT_WORLD_DEFAULT_SCENE_KEY,
        "label": "一楼活动室",
        "englishName": "Main Room",
        "sceneType": "indoor",
        "isEnabled": True,
        "sortOrder": 10,
        "description": "默认的一楼活动室。",
        "purchasable": False,
        "purchaseCost": 0,
        "unlockByDefault": True,
        "world": {
            "width": 2560,
            "height": 560,
            "viewportWidth": 1280,
            "viewportHeight": 560,
            "floorTop": 260,
            "floorBottom": 522,
        },
        "camera": {"pageWidth": 1280, "initialPage": 0, "snapPaging": True},
        "palette": {
            "wallTopLeft": "#cff7ee",
            "wallTopRight": "#fff0d0",
            "wallBottomLeft": "#9be4ff",
            "wallBottomRight": "#ffd7e7",
            "floor": "#c29258",
            "trim": "#6bc579",
            "grid": "#2c2f3a",
        },
        "features": {"cats": True, "food": True, "care": True, "hygiene": True},
        "itemRules": {"allowedCategories": ["decor", "toy"], "excludedItemIds": []},
        "spawnPoints": {
            "activeFood": {"x": 1340, "y": 408, "width": 118, "height": 46},
            "activeCare": {"x": 590, "y": 426, "width": 68, "height": 70},
            "readyLitter": {"x": 1134, "y": 352, "width": 112, "height": 82},
            "attention": {"x": 754, "y": 444},
            "litter": [
                {"x": 1110, "y": 456},
                {"x": 930, "y": 468},
                {"x": 744, "y": 448},
                {"x": 426, "y": 466},
            ],
        },
        "portals": [
            {"targetSceneKey": "yard", "label": "去外院", "x": 1510, "y": 250},
            {"targetSceneKey": "second-floor", "label": "去二楼", "x": 82, "y": 250},
        ],
        "defaultLayout": CAT_WORLD_ROOM_DEFAULT_LAYOUT,
    },
    {
        "sceneKey": "yard",
        "label": "猫咪外院",
        "englishName": "Garden Yard",
        "sceneType": "outdoor",
        "isEnabled": True,
        "sortOrder": 20,
        "description": "可以晒太阳、追风和摆放户外玩具的猫咪外院。",
        "purchasable": True,
        "purchaseCost": 50000,
        "unlockByDefault": False,
        "world": {
            "width": 2560,
            "height": 560,
            "viewportWidth": 1280,
            "viewportHeight": 560,
            "floorTop": 236,
            "floorBottom": 522,
        },
        "camera": {"pageWidth": 1280, "initialPage": 0, "snapPaging": True},
        "palette": {
            "wallTopLeft": "#8ed8ff",
            "wallTopRight": "#fff1a8",
            "wallBottomLeft": "#bff0ff",
            "wallBottomRight": "#d9f6c2",
            "floor": "#78b95a",
            "trim": "#4c963f",
            "grid": "#31544d",
        },
        "features": {"cats": True, "food": True, "care": True, "hygiene": True},
        "itemRules": {"allowedCategories": ["decor", "toy"], "excludedItemIds": ["sun-window", "window-hammock"]},
        "spawnPoints": {
            "activeFood": {"x": 1920, "y": 408, "width": 118, "height": 46},
            "activeCare": {"x": 760, "y": 426, "width": 68, "height": 70},
            "readyLitter": {"x": 1560, "y": 352, "width": 112, "height": 82},
            "attention": {"x": 1054, "y": 444},
            "litter": [
                {"x": 1710, "y": 456},
                {"x": 1320, "y": 468},
                {"x": 840, "y": 448},
                {"x": 390, "y": 466},
            ],
        },
        "portals": [{"targetSceneKey": CAT_WORLD_DEFAULT_SCENE_KEY, "label": "回一楼", "x": 80, "y": 238}],
        "defaultLayout": CAT_WORLD_ROOM_DEFAULT_LAYOUT,
    },
    {
        "sceneKey": "second-floor",
        "label": "二楼阅读间",
        "englishName": "Reading Loft",
        "sceneType": "upper-floor",
        "isEnabled": True,
        "sortOrder": 30,
        "description": "适合安静陪读和布置书架的二楼阅读间。",
        "purchasable": True,
        "purchaseCost": 50000,
        "unlockByDefault": False,
        "world": {
            "width": 2560,
            "height": 560,
            "viewportWidth": 1280,
            "viewportHeight": 560,
            "floorTop": 268,
            "floorBottom": 522,
        },
        "camera": {"pageWidth": 1280, "initialPage": 0, "snapPaging": True},
        "palette": {
            "wallTopLeft": "#e9ddff",
            "wallTopRight": "#ffeab5",
            "wallBottomLeft": "#c9e8ff",
            "wallBottomRight": "#ffd4e5",
            "floor": "#a97858",
            "trim": "#8e70b8",
            "grid": "#3d354d",
        },
        "features": {"cats": True, "food": True, "care": True, "hygiene": True},
        "itemRules": {"allowedCategories": ["decor", "toy"], "excludedItemIds": []},
        "spawnPoints": {
            "activeFood": {"x": 1510, "y": 408, "width": 118, "height": 46},
            "activeCare": {"x": 650, "y": 426, "width": 68, "height": 70},
            "readyLitter": {"x": 1260, "y": 352, "width": 112, "height": 82},
            "attention": {"x": 854, "y": 444},
            "litter": [
                {"x": 1430, "y": 456},
                {"x": 1110, "y": 468},
                {"x": 760, "y": 448},
                {"x": 390, "y": 466},
            ],
        },
        "portals": [{"targetSceneKey": CAT_WORLD_DEFAULT_SCENE_KEY, "label": "回一楼", "x": 80, "y": 268}],
        "defaultLayout": CAT_WORLD_ROOM_DEFAULT_LAYOUT,
    },
    {
        "sceneKey": "kitchen",
        "label": "猫咪厨房",
        "englishName": "Cat Kitchen",
        "sceneType": "kitchen",
        "isEnabled": True,
        "sortOrder": 40,
        "description": "摆放食盆、饮水机和餐桌的明亮猫咪厨房。",
        "purchasable": True,
        "purchaseCost": 50000,
        "unlockByDefault": False,
        "world": {
            "width": 2560,
            "height": 560,
            "viewportWidth": 1280,
            "viewportHeight": 560,
            "floorTop": 252,
            "floorBottom": 522,
        },
        "camera": {"pageWidth": 1280, "initialPage": 0, "snapPaging": True},
        "palette": {
            "wallTopLeft": "#c9f5ff", "wallTopRight": "#fff1a8",
            "wallBottomLeft": "#e5fbff", "wallBottomRight": "#ffd6c9",
            "floor": "#78ad92", "trim": "#e4686f", "grid": "#2c3f46",
        },
        "features": {"cats": True, "food": True, "care": True, "hygiene": True},
        "itemRules": {"allowedCategories": ["decor", "toy"], "excludedItemIds": ["window-hammock"]},
        "spawnPoints": {
            "activeFood": {"x": 2210, "y": 408, "width": 118, "height": 46},
            "activeCare": {"x": 680, "y": 426, "width": 68, "height": 70},
            "readyLitter": {"x": 1820, "y": 352, "width": 112, "height": 82},
            "attention": {"x": 1234, "y": 444},
            "litter": [{"x": 2180, "y": 456}, {"x": 1680, "y": 468}, {"x": 920, "y": 448}, {"x": 390, "y": 466}],
        },
        "portals": [{"targetSceneKey": CAT_WORLD_DEFAULT_SCENE_KEY, "label": "回一楼", "x": 80, "y": 252}],
        "defaultLayout": CAT_WORLD_ROOM_DEFAULT_LAYOUT,
    },
    {
        "sceneKey": "master-bedroom",
        "label": "猫咪主卧",
        "englishName": "Master Bedroom",
        "sceneType": "bedroom",
        "isEnabled": True,
        "sortOrder": 50,
        "description": "适合猫窝、软垫和夜间休息的安静主卧。",
        "purchasable": True,
        "purchaseCost": 50000,
        "unlockByDefault": False,
        "world": {
            "width": 2560,
            "height": 560,
            "viewportWidth": 1280,
            "viewportHeight": 560,
            "floorTop": 270,
            "floorBottom": 522,
        },
        "camera": {"pageWidth": 1280, "initialPage": 0, "snapPaging": True},
        "palette": {
            "wallTopLeft": "#d7e6ff", "wallTopRight": "#ffd7e7",
            "wallBottomLeft": "#bdebd7", "wallBottomRight": "#ffe9ad",
            "floor": "#8b739d", "trim": "#55a891", "grid": "#34334b",
        },
        "features": {"cats": True, "food": True, "care": True, "hygiene": True},
        "itemRules": {"allowedCategories": ["decor", "toy"], "excludedItemIds": []},
        "spawnPoints": {
            "activeFood": {"x": 2190, "y": 408, "width": 118, "height": 46},
            "activeCare": {"x": 720, "y": 426, "width": 68, "height": 70},
            "readyLitter": {"x": 1840, "y": 352, "width": 112, "height": 82},
            "attention": {"x": 1234, "y": 444},
            "litter": [{"x": 2160, "y": 456}, {"x": 1650, "y": 468}, {"x": 900, "y": 448}, {"x": 380, "y": 466}],
        },
        "portals": [{"targetSceneKey": CAT_WORLD_DEFAULT_SCENE_KEY, "label": "回一楼", "x": 80, "y": 270}],
        "defaultLayout": CAT_WORLD_ROOM_DEFAULT_LAYOUT,
    },
]
CAT_WORLD_SCENE_SEED_BY_KEY = {scene["sceneKey"]: scene for scene in CAT_WORLD_SCENE_SEEDS}
CAT_WORLD_PRICING_PLANS = [
    {
        "category": "food",
        "label": "猫粮",
        "range": "30-120",
        "strategy": "基础口粮低价低恢复；特色餐对指定猫提供更高体力加成。",
    },
    {
        "category": "consumable",
        "label": "消耗品",
        "range": "35-150",
        "strategy": "可重复购买；猫砂先放进房间再自动预防，铲子负责清理，洗澡和护理用品使用一次消耗一个。",
    },
    {
        "category": "toy",
        "label": "玩具",
        "range": "80-160",
        "strategy": "中价一次性解锁，主要提高互动感和心情值。",
    },
    {
        "category": "decor",
        "label": "装修",
        "range": "180-360",
        "strategy": "中高价长期布置，书桌、猫窝、猫爬架和窗台会直接出现在房间。",
    },
    {
        "category": "color",
        "label": "配色",
        "range": "80-120",
        "strategy": "低价皮肤解锁，购买后点击已拥有家具切换颜色。",
    },
    {
        "category": "cat",
        "label": "名猫",
        "range": "420-800",
        "strategy": "高价长期目标；猫咪离家后需要重新购买，领养后恢复基础状态。",
    },
    {
        "category": "blind-box",
        "label": "限定盲盒",
        "range": "10000",
        "strategy": "全站限量库存；随机解锁一只尚未拥有的限定猫咪，库存扣减后不会补回。",
    },
    {
        "category": "handbook",
        "label": "收藏手册",
        "range": "10000",
        "strategy": "一次购买永久拥有；猫咪手册解锁分期卡册，食物手册解锁食物图鉴。",
    },
]


SCIENCE_LEVELS = [
    {"key": "L300-L500", "label": "L300-L500", "tone": "short sentences and simple science words"},
    {"key": "L500-L700", "label": "L500-L700", "tone": "clear middle-grade explanations"},
    {"key": "L700-L900", "label": "L700-L900", "tone": "richer details and cause-effect language"},
    {"key": "L900-L1100", "label": "L900-L1100", "tone": "upper middle-grade explanations with evidence and examples"},
    {"key": "L1100-L1300", "label": "L1100-L1300", "tone": "more academic wording with clear scientific reasoning"},
    {"key": "L1300-L1500", "label": "L1300-L1500", "tone": "advanced science reading with concise technical context"},
]

SCIENCE_SOURCES = [
    ("NASA Space Place", "https://spaceplace.nasa.gov/"),
    ("NASA Science Kids", "https://science.nasa.gov/kids/"),
    ("NOAA Education", "https://www.noaa.gov/education"),
    ("USGS Water Science School", "https://www.usgs.gov/water-science-school"),
    ("USGS Volcano Hazards", "https://www.usgs.gov/programs/VHP"),
    ("CDC Clean Hands", "https://www.cdc.gov/clean-hands/"),
    ("EPA Water Filtration", "https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P100A2CR.TXT"),
    ("EIA Energy Kids", "https://www.eia.gov/kids/"),
    ("Federal Highway Administration", "https://highways.dot.gov/"),
]

SCIENCE_CONCEPTS = [
    ("动物", "How Sea Otters Use Tools", "Sea otters crack shells with rocks and show that animals can solve problems in clever ways.", "otter, tool, shell"),
    ("动物", "Why Owls Fly Quietly", "Soft feather edges help owls move through the air with very little sound.", "owl, feather, silent"),
    ("动物", "The Secret Work of Coral Reefs", "Tiny coral animals build large reef homes that protect many ocean species.", "coral, reef, habitat"),
    ("动物", "How Penguins Stay Warm", "Penguins use oily feathers, packed groups, and body fat to survive cold water.", "penguin, insulation, colony"),
    ("动物", "Why Bees Dance", "Honeybees use movement to tell other bees where flowers are located.", "bee, nectar, signal"),
    ("动物", "How Bats Use Echoes", "Bats send out sounds and listen for returning echoes to find insects in the dark.", "bat, echo, sound wave"),
    ("动物", "Why Camels Have Humps", "Camels store fat in humps and use other body features to survive dry places.", "camel, hump, desert"),
    ("动物", "How Salmon Find Their Way", "Salmon use smell, current, and Earth's magnetic clues to return to home streams.", "salmon, migration, stream"),
    ("植物", "How Leaves Breathe", "Leaves use tiny openings to trade gases while making food from sunlight.", "leaf, stomata, photosynthesis"),
    ("植物", "Why Seeds Travel", "Seeds move by wind, water, animals, and sticky hooks so plants can spread.", "seed, dispersal, germinate"),
    ("植物", "The Job of Tree Rings", "Tree rings record years of growth and clues about rainfall and climate.", "tree ring, growth, climate"),
    ("植物", "How Desert Plants Save Water", "Cacti and other desert plants store water and protect it with waxy skins.", "cactus, waxy, desert"),
    ("植物", "Why Flowers Have Colors", "Flower colors and smells help guide pollinators toward nectar.", "flower, pollinator, nectar"),
    ("植物", "How Roots Find Water", "Roots grow through soil and branch toward places where water and minerals are available.", "root, water, mineral"),
    ("植物", "Why Plants Turn Toward Light", "Plant stems can bend as growth changes on each side, helping leaves reach more light.", "plant, light, growth"),
    ("植物", "How Forests Share Nutrients", "Trees, fungi, and soil organisms move nutrients through busy underground networks.", "forest, fungi, nutrient"),
    ("人体", "How Your Heart Pumps", "The heart squeezes blood through vessels to deliver oxygen around the body.", "heart, blood, oxygen"),
    ("人体", "Why Muscles Get Stronger", "Muscles adapt when they work, rest, and repair tiny fibers.", "muscle, fiber, repair"),
    ("人体", "How Eyes See Color", "Special cells in the eye detect light and send color signals to the brain.", "retina, cone, signal"),
    ("人体", "Why Sleep Helps Memory", "During sleep, the brain sorts information and strengthens useful memories.", "sleep, memory, brain"),
    ("人体", "How Skin Protects You", "Skin blocks many germs, helps control heat, and senses the world.", "skin, germ, temperature"),
    ("人体", "How Lungs Move Air", "Lungs fill and empty as muscles change the space inside the chest.", "lung, breath, diaphragm"),
    ("人体", "Why Bones Heal", "Bone cells rebuild cracked areas with new tissue that slowly becomes strong again.", "bone, cell, repair"),
    ("人体", "How Your Ear Hears Sound", "The ear changes vibrations in air into signals the brain can understand.", "ear, vibration, signal"),
    ("微生物", "The Good Side of Bacteria", "Many bacteria help digest food, recycle nutrients, and keep ecosystems balanced.", "bacteria, nutrient, ecosystem"),
    ("微生物", "How Yeast Makes Bread Rise", "Yeast eats sugar and releases gas that makes dough puff up.", "yeast, dough, carbon dioxide"),
    ("微生物", "What Makes Mold Grow", "Mold spreads by spores and grows best in warm, damp places.", "mold, spore, damp"),
    ("微生物", "How Microbes Clean Water", "Some microbes break down waste and help clean water in treatment systems.", "microbe, waste, filter"),
    ("微生物", "Why Handwashing Works", "Soap lifts oils and germs from skin so water can wash them away.", "soap, germ, rinse"),
    ("微生物", "How Probiotics Help Digestion", "Helpful microbes can live in the gut and support digestion by breaking down food.", "probiotic, gut, digestion"),
    ("微生物", "Why Food Spoils", "Food spoils when microbes grow and change its smell, texture, or safety.", "food, microbe, spoil"),
    ("微生物", "How Algae Make Oxygen", "Tiny algae use sunlight in water and release oxygen as they grow.", "algae, oxygen, sunlight"),
    ("地球", "Why Volcanoes Erupt", "Magma rises through weak places in Earth's crust and can burst out as lava.", "magma, lava, crust"),
    ("地球", "How Rivers Shape Land", "Moving water carries rock and soil, slowly carving valleys and deltas.", "river, erosion, delta"),
    ("地球", "Why Earthquakes Happen", "Earthquakes happen when rocks suddenly slip along faults underground.", "earthquake, fault, plate"),
    ("地球", "How Clouds Form", "Warm air rises, cools, and turns water vapor into tiny droplets.", "cloud, vapor, droplet"),
    ("地球", "What Makes a Fossil", "Fossils form when remains are buried and slowly replaced or preserved in rock.", "fossil, sediment, preserve"),
    ("地球", "How Glaciers Move", "Glaciers flow slowly downhill and scrape land as thick ice deforms under its own weight.", "glacier, ice, valley"),
    ("地球", "Why Ocean Tides Rise", "Tides rise and fall because gravity from the Moon and Sun pulls on ocean water.", "tide, gravity, ocean"),
    ("地球", "How Soil Forms", "Soil forms as rock breaks down and mixes with air, water, and once-living material.", "soil, rock, humus"),
    ("太空", "Why the Moon Changes Shape", "The Moon's phases come from how sunlight hits the part we can see.", "moon, phase, orbit"),
    ("太空", "How Rockets Leave Earth", "Rockets push gas downward, and the reaction pushes the rocket upward.", "rocket, thrust, gravity"),
    ("太空", "Why Mars Looks Red", "Iron-rich dust on Mars gives the planet its rusty red color.", "Mars, iron, dust"),
    ("太空", "How Telescopes Collect Light", "Telescopes gather light so distant objects look brighter and clearer.", "telescope, light, lens"),
    ("太空", "What Astronauts Need in Space", "Astronauts need air, water, food, exercise, and careful plans to stay healthy.", "astronaut, orbit, life support"),
    ("太空", "Why Stars Shine", "Stars shine because nuclear reactions in their cores release huge amounts of energy.", "star, fusion, energy"),
    ("太空", "How Satellites Stay in Orbit", "Satellites keep falling around Earth because forward motion and gravity balance.", "satellite, orbit, gravity"),
    ("太空", "What Makes a Comet Tail", "A comet grows a bright tail when sunlight warms ice and dust near the Sun.", "comet, ice, tail"),
    ("工程", "How Bridges Carry Weight", "Bridges spread forces through beams, arches, cables, or triangles.", "bridge, force, beam"),
    ("工程", "Why Robots Use Sensors", "Sensors help robots detect light, distance, touch, and movement.", "robot, sensor, program"),
    ("工程", "How Solar Panels Work", "Solar panels turn sunlight into electricity using special materials.", "solar panel, electricity, sunlight"),
    ("工程", "Why Filters Matter", "Filters trap particles and help clean air or water before people use it.", "filter, particle, clean"),
    ("工程", "How Wind Turbines Make Electricity", "Wind turbines turn moving air into spinning motion and then electrical energy.", "turbine, wind, generator"),
    ("工程", "Why Airplanes Have Wings", "Airplane wings shape moving air so lift can help hold the plane up.", "airplane, wing, lift"),
    ("工程", "How Dams Hold Back Water", "Dams use heavy walls, strong foundations, and spillways to control moving water.", "dam, water, spillway"),
    ("工程", "How 3D Printers Build Shapes", "3D printers build objects layer by layer from digital designs.", "printer, layer, design"),
]

SCIENCE_TOPIC_REFERENCE = {
    "动物": ("NOAA Education", "https://www.noaa.gov/education"),
    "植物": ("NASA Science Kids", "https://science.nasa.gov/kids/earth/"),
    "人体": ("CDC", "https://www.cdc.gov/"),
    "微生物": ("CDC Clean Hands", "https://www.cdc.gov/clean-hands/"),
    "地球": ("USGS", "https://www.usgs.gov/"),
    "太空": ("NASA Space Place", "https://spaceplace.nasa.gov/"),
    "工程": ("Federal Highway Administration", "https://highways.dot.gov/"),
}

SCIENCE_REFERENCE_BY_TITLE = {
    "The Secret Work of Coral Reefs": ("NOAA Fisheries", "https://www.fisheries.noaa.gov/national/habitat-conservation/shallow-coral-reef-habitat"),
    "How Your Heart Pumps": ("CDC", "https://www.cdc.gov/heart-defects/how-the-heart-works/index.html"),
    "Why Handwashing Works": ("CDC Clean Hands", "https://www.cdc.gov/clean-hands/data-research/facts-stats/index.html"),
    "Why Volcanoes Erupt": ("USGS Volcano Hazards Program", "https://www.usgs.gov/faqs/how-do-volcanoes-erupt"),
    "How Rivers Shape Land": ("USGS Water Science School", "https://www.usgs.gov/water-science-school/surface-water"),
    "How Clouds Form": ("NASA Science Kids", "https://science.nasa.gov/kids/earth/how-do-clouds-form/"),
    "Why the Moon Changes Shape": ("NASA Space Place", "https://spaceplace.nasa.gov/moon-phases/"),
    "How Solar Panels Work": ("EIA Energy Kids", "https://www.eia.gov/kids/energy-sources/solar/"),
    "Why Stars Shine": ("NASA Space Place", "https://spaceplace.nasa.gov/sun-corona/"),
    "How Satellites Stay in Orbit": ("NASA Space Place", "https://spaceplace.nasa.gov/"),
    "What Makes a Comet Tail": ("NASA Space Place", "https://spaceplace.nasa.gov/comets/"),
    "How Wind Turbines Make Electricity": ("EIA Energy Kids", "https://www.eia.gov/kids/energy-sources/wind/"),
    "Why Airplanes Have Wings": ("NASA Glenn Research Center", "https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/"),
    "How Dams Hold Back Water": ("USGS Water Science School", "https://www.usgs.gov/water-science-school"),
    "What Astronauts Need in Space": ("NASA Space Place", "https://spaceplace.nasa.gov/"),
    "How Bridges Carry Weight": ("Federal Highway Administration", "https://www.environment.fhwa.dot.gov/env_topics/historic_pres/post1945_engineering/this_bridge.aspx"),
    "Why Filters Matter": ("EPA Water Filtration", "https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P100A2CR.TXT"),
}

SCIENCE_CONCEPT_FACTS = {
    "How Sea Otters Use Tools": [
        "A sea otter often floats on its back and uses its chest like a workbench while it opens hard-shelled food.",
        "The tool is useful because a shell protects the soft animal inside, and repeated tapping can crack that shell without wasting too much energy.",
        "This behavior shows that an animal can match a problem, a body part, and an object from the environment.",
    ],
    "Why Owls Fly Quietly": [
        "An owl wing does not slice through air like a smooth board; the feather edges split moving air into smaller, softer currents.",
        "Soft fringes and downy surfaces reduce the rushing sound that many birds make when air breaks around their wings.",
        "Quiet flight helps an owl approach prey before the prey can use hearing as an early warning system.",
    ],
    "The Secret Work of Coral Reefs": [
        "A reef is built by many tiny coral animals that make hard skeletons and slowly create a three-dimensional home.",
        "That structure gives fish and other ocean animals places to hide, feed, reproduce, and grow.",
        "Because so much life depends on reef structure, small changes in water temperature, sunlight, or water quality can affect a whole community.",
    ],
    "How Penguins Stay Warm": [
        "A penguin keeps heat with overlapping feathers, a layer of fat, and a body shape that reduces heat loss.",
        "When penguins huddle, each bird loses less heat to cold air and wind than it would alone.",
        "Warmth is not one trick; it is a system of body parts and behaviors working together.",
    ],
    "Why Bees Dance": [
        "A honeybee dance is a moving signal that helps other bees find food without every bee searching at random.",
        "The direction and length of the dance can give clues about where nectar is located.",
        "The colony works better because one bee's discovery can become shared information.",
    ],
    "How Leaves Breathe": [
        "Leaves trade gases through tiny openings, while green cells use light energy to help make sugar.",
        "A leaf must balance two needs: taking in carbon dioxide and keeping too much water from escaping.",
        "The shape of a leaf, the number of openings, and the weather around it all affect that balance.",
    ],
    "Why Seeds Travel": [
        "A seed must leave the parent plant if it is going to find enough space, light, and water to grow.",
        "Some seeds float, some fly, some stick to fur, and some pass through animals after fruit is eaten.",
        "Seed movement is a plant's way of solving a problem even though the plant itself cannot walk.",
    ],
    "The Job of Tree Rings": [
        "A tree ring is a record of growth, and each ring shows wood made during one growing season.",
        "Wide and narrow rings can give clues about rainfall, temperature, fire, or other conditions from that year.",
        "Scientists compare ring patterns from many trees to build evidence about past environments.",
    ],
    "How Desert Plants Save Water": [
        "Many desert plants store water in thick tissues and reduce water loss with waxy surfaces or small leaves.",
        "Spines can protect stored water and can also shade the plant surface a little.",
        "The plant survives by slowing water loss, not by finding water every day.",
    ],
    "Why Flowers Have Colors": [
        "Flower colors, patterns, and smells can guide pollinators toward nectar or pollen.",
        "When an animal visits a flower, pollen may stick to its body and move to another flower.",
        "A flower is both a plant structure and a signal in a living partnership.",
    ],
    "How Your Heart Pumps": [
        "The heart is a muscle that squeezes in a rhythm, moving blood through chambers, valves, and blood vessels.",
        "Blood picks up oxygen in the lungs and then carries that oxygen to body cells that need energy.",
        "Valves matter because they keep blood moving in one direction instead of leaking backward.",
    ],
    "Why Muscles Get Stronger": [
        "A muscle becomes stronger when work, rest, food, and repeated practice give the body time to repair and adapt.",
        "Exercise challenges muscle fibers, and recovery helps the body rebuild them for the next effort.",
        "Strength is evidence of adaptation, not something that appears from one hard workout.",
    ],
    "How Eyes See Color": [
        "Color vision begins when light enters the eye and reaches cells that respond to different wavelengths.",
        "The brain compares signals from these cells and builds the color experience we notice.",
        "Objects do not simply contain color; they reflect light that the eye and brain interpret.",
    ],
    "Why Sleep Helps Memory": [
        "During sleep, the brain is still active, sorting recent experiences and strengthening useful connections.",
        "Rest can make a skill or idea easier to use later because the brain has time to organize it.",
        "Memory depends on attention while learning and recovery after learning.",
    ],
    "How Skin Protects You": [
        "Skin is a flexible barrier that helps block germs, keep water inside the body, and sense touch and temperature.",
        "When skin is cut, the body starts repair work so the barrier can close again.",
        "Protection is both physical and sensory: skin warns you about heat, pressure, and injury.",
    ],
    "The Good Side of Bacteria": [
        "Some bacteria cause disease, but many bacteria help ecosystems recycle nutrients and help bodies digest food.",
        "Helpful bacteria often work in communities where different microbes use different materials.",
        "The important science question is not whether bacteria are good or bad, but what each kind is doing in its environment.",
    ],
    "How Yeast Makes Bread Rise": [
        "Yeast is a living microbe that uses sugar and releases carbon dioxide gas.",
        "Gas bubbles get trapped in dough, so the dough expands and becomes lighter.",
        "Warmth, time, and food affect how active yeast becomes.",
    ],
    "What Makes Mold Grow": [
        "Mold spreads by tiny spores and grows well when it has moisture, food, and the right temperature.",
        "A damp surface can become a habitat for mold because spores are already common in the air.",
        "Controlling moisture is often the most important way to slow mold growth.",
    ],
    "How Microbes Clean Water": [
        "Some water treatment systems use microbes that break down waste into simpler materials.",
        "The microbes need the right oxygen, food, and flow conditions to keep working.",
        "Clean water can depend on living processes as well as filters, settling tanks, and human engineering.",
    ],
    "Why Handwashing Works": [
        "Soap helps lift oils, dirt, and many germs from skin so running water can carry them away.",
        "Rubbing matters because it reaches the backs of hands, between fingers, and under nails.",
        "Handwashing is a small action with a large effect because hands move germs between surfaces, faces, and other people.",
    ],
    "Why Volcanoes Erupt": [
        "Deep underground, hot rock can melt into magma, which is less dense than nearby solid rock.",
        "Magma rises through cracks or weak places and may collect in chambers before reaching the surface.",
        "Once magma erupts, scientists call it lava, and the eruption can also release gases, ash, and broken rock.",
    ],
    "How Rivers Shape Land": [
        "A river carries water, sand, soil, and rock, and that moving material can wear land down over time.",
        "Fast water can erode banks and valleys, while slower water may drop sediment in bars, floodplains, or deltas.",
        "River shape is evidence of energy, slope, water volume, and the material the river is moving.",
    ],
    "Why Earthquakes Happen": [
        "Earth's outer layer is broken into moving plates, and stress can build where rocks are locked together.",
        "An earthquake happens when rocks suddenly slip and release stored energy as shaking waves.",
        "Faults, aftershocks, and patterns of past quakes help scientists estimate where shaking is more likely.",
    ],
    "How Clouds Form": [
        "A cloud forms when invisible water vapor cools and changes into tiny liquid droplets or ice crystals.",
        "Those droplets need small particles, such as dust or salt, to gather on.",
        "Rising air, cooling temperature, and moisture work together to decide when a cloud appears.",
    ],
    "What Makes a Fossil": [
        "A fossil usually begins when a dead organism is buried quickly by sediment.",
        "Over long periods, minerals can fill spaces or replace hard parts such as shells, bones, or wood.",
        "Fossils are rare records because most living things decay or are broken apart before they can be preserved.",
    ],
    "Why the Moon Changes Shape": [
        "The Moon does not make its own light; we see sunlight reflecting from its surface.",
        "As the Moon orbits Earth, we see different amounts of the sunlit half.",
        "The repeating pattern of phases is evidence that the Moon is moving around Earth.",
    ],
    "How Rockets Leave Earth": [
        "A rocket pushes hot gas downward, and the gas pushes the rocket upward with an equal and opposite force.",
        "The rocket must produce enough thrust to overcome gravity and keep accelerating.",
        "Fuel, mass, shape, and guidance all matter because leaving Earth is a problem of force and motion.",
    ],
    "Why Mars Looks Red": [
        "Mars looks red because iron minerals in its dust and rocks have reacted with oxygen over time.",
        "Fine dust can cover large areas, so the rusty color is visible even from far away.",
        "The color gives scientists a clue about the planet's surface materials and history.",
    ],
    "How Telescopes Collect Light": [
        "A telescope gathers more light than an eye can gather by itself.",
        "Mirrors or lenses focus that light so faint or distant objects can be seen more clearly.",
        "A larger light-collecting area can reveal details that would otherwise be too dim.",
    ],
    "What Astronauts Need in Space": [
        "Astronauts need air, water, food, temperature control, communication, exercise, and protection from hazards.",
        "In orbit, the body and equipment behave differently because there is very little weight pulling things downward.",
        "Space travel is a life-support problem as much as it is a rocket problem.",
    ],
    "How Bridges Carry Weight": [
        "A bridge carries weight by spreading forces from the deck into supports, cables, arches, or trusses.",
        "Different shapes handle tension and compression in different ways, so design changes how much weight a bridge can hold.",
        "Testing a model bridge helps engineers compare evidence instead of guessing which design is strongest.",
    ],
    "Why Robots Use Sensors": [
        "A robot sensor changes information from the world, such as light, distance, touch, or sound, into data the robot can use.",
        "A program compares sensor data with instructions and chooses the next action.",
        "Sensors matter because a robot that cannot detect change cannot respond to its environment.",
    ],
    "How Solar Panels Work": [
        "A solar cell can convert light energy directly into electrical energy.",
        "Many cells are connected into a panel so they can produce more useful power together.",
        "Sunlight, angle, shade, and storage all affect how much electricity a solar system can provide.",
    ],
    "Why Filters Matter": [
        "A filter is a barrier with tiny spaces that let some materials pass while trapping others.",
        "In water or air, larger particles can be blocked, while smaller molecules may need different treatment methods.",
        "A good filter is matched to the problem: the material, pore size, flow speed, and contaminant all matter.",
    ],
}

SCIENCE_CONCEPT_FACTS.update(
    {
        "How Bats Use Echoes": [
            "A bat sends out high sounds that bounce off insects, branches, and walls.",
            "The returning echo changes with distance, size, and movement, so the bat can adjust its flight.",
            "Echolocation is useful because sound can carry information even when light is limited.",
        ],
        "Why Camels Have Humps": [
            "A camel's hump stores fat, not water, and that stored energy can help when food is scarce.",
            "Other adaptations, such as wide feet and a body that tolerates heat, reduce stress in dry habitats.",
            "Survival in a desert depends on managing energy, heat, and water loss together.",
        ],
        "How Salmon Find Their Way": [
            "Young salmon leave freshwater streams and later return from the ocean to reproduce.",
            "Smell can help salmon recognize home waters, while currents and magnetic clues may guide longer travel.",
            "Migration connects rivers and oceans, so a change in one place can affect the whole life cycle.",
        ],
        "How Roots Find Water": [
            "Roots grow through small spaces in soil and branch into areas with water and dissolved minerals.",
            "Root hairs increase surface area, which helps the plant absorb more from the soil around it.",
            "A plant's hidden root system can decide how well the visible stem and leaves survive.",
        ],
        "Why Plants Turn Toward Light": [
            "Many shoots bend toward light because cells on one side grow more than cells on the other side.",
            "Turning toward light can help leaves capture more energy for photosynthesis.",
            "This movement shows that plants respond to their environment even though they do not walk.",
        ],
        "How Forests Share Nutrients": [
            "Tree roots, fungi, bacteria, and decaying leaves form an underground nutrient network.",
            "Fungi can connect with roots and help move minerals, while receiving sugars from the plant.",
            "A forest is not just separate trees; it is a living system with many exchanges below the surface.",
        ],
        "How Lungs Move Air": [
            "The diaphragm and rib muscles change the size of the chest space.",
            "When the space inside the chest gets larger, air moves into the lungs; when it gets smaller, air moves out.",
            "Breathing is a pressure-and-motion process that keeps oxygen entering and carbon dioxide leaving.",
        ],
        "Why Bones Heal": [
            "After a break, blood, repair cells, and minerals gather around the damaged area.",
            "Soft repair tissue can become harder over time as new bone forms and reshapes.",
            "A healed bone is evidence that the body can rebuild structure, but the process needs protection and time.",
        ],
        "How Your Ear Hears Sound": [
            "Sound begins as vibration in air and reaches the eardrum as moving pressure waves.",
            "Tiny bones and fluid-filled parts of the inner ear help change vibration into nerve signals.",
            "The brain interprets those signals as pitch, loudness, direction, and meaning.",
        ],
        "How Probiotics Help Digestion": [
            "Probiotics are helpful microbes that can live in the gut or in fermented foods.",
            "Some microbes help break down food materials that human cells cannot digest alone.",
            "Gut health depends on a community, so balance and habitat matter as much as a single microbe.",
        ],
        "Why Food Spoils": [
            "Food can spoil when microbes use it as a source of energy and multiply.",
            "Warmth, moisture, oxygen, and time can speed up changes in smell, texture, and safety.",
            "Cooling, drying, sealing, or cooking food works because those actions change the conditions microbes need.",
        ],
        "How Algae Make Oxygen": [
            "Many algae are tiny photosynthetic organisms that live in water and use sunlight.",
            "During photosynthesis, algae take in carbon dioxide and release oxygen.",
            "Because algae can grow in huge numbers, they affect food webs and the gases dissolved in water.",
        ],
        "How Glaciers Move": [
            "A glacier is thick ice that can flow slowly downhill under its own weight.",
            "As it moves, it can scrape rock, carry sediment, and shape valleys.",
            "Glacial landforms are evidence of motion that is slow for people but powerful over long periods.",
        ],
        "Why Ocean Tides Rise": [
            "Ocean tides are linked to gravity from the Moon and, to a lesser degree, the Sun.",
            "As Earth rotates, coastlines move through areas where ocean water is pulled higher or lower.",
            "Tide patterns show how distant objects can still affect water on Earth.",
        ],
        "How Soil Forms": [
            "Soil begins as rock breaks into smaller pieces through weather, water, roots, and time.",
            "Dead leaves, microbes, and animals add organic material that helps soil hold water and nutrients.",
            "Good soil is a mixture, not just dirt: minerals, air, water, and living things work together.",
        ],
        "Why Stars Shine": [
            "A star shines because nuclear fusion in its core changes hydrogen into helium and releases energy.",
            "That energy moves outward and eventually leaves the star as light and heat.",
            "The light we see is evidence of processes happening in a place too hot and distant to visit.",
        ],
        "How Satellites Stay in Orbit": [
            "A satellite in orbit is always falling toward Earth, but it also moves forward very fast.",
            "Because Earth curves away beneath it, the satellite keeps missing the ground.",
            "Orbit is a balance between gravity, speed, and direction rather than a place with no gravity.",
        ],
        "What Makes a Comet Tail": [
            "A comet contains ice, dust, and rock left from the early solar system.",
            "When it comes closer to the Sun, warming ice releases gas and dust around the comet.",
            "Sunlight and charged particles can push that material into a tail that points away from the Sun.",
        ],
        "How Wind Turbines Make Electricity": [
            "Moving air pushes turbine blades and makes the rotor spin.",
            "The spinning motion turns a generator, which changes mechanical energy into electrical energy.",
            "A wind turbine's output depends on wind speed, blade shape, tower height, and the generator system.",
        ],
        "Why Airplanes Have Wings": [
            "A wing changes how air moves above and below it as the airplane goes forward.",
            "The shape and angle of the wing help create lift, while engines provide thrust.",
            "Flight depends on several forces at once: lift, weight, thrust, and drag.",
        ],
        "How Dams Hold Back Water": [
            "A dam must resist the push of stored water, which grows stronger with depth.",
            "Strong foundations, curved or heavy walls, and controlled spillways help manage that pressure.",
            "A dam is both a structure and a water-control system, so safety depends on design and operation.",
        ],
        "How 3D Printers Build Shapes": [
            "A 3D printer follows a digital design and builds an object in thin layers.",
            "Each layer must line up with the layer before it so the final shape is accurate.",
            "Layer-by-layer building lets engineers test shapes quickly before making a final product.",
        ],
    }
)

SCIENCE_PUBLIC_SOURCE_DOMAINS = (
    "nasa.gov",
    "spaceplace.nasa.gov",
    "noaa.gov",
    "usgs.gov",
    "cdc.gov",
    "epa.gov",
    "eia.gov",
    "dot.gov",
)


def science_source_mode_config(source_mode: str | None) -> dict[str, str]:
    normalized = (source_mode or SCIENCE_SOURCE_MODE_DEFAULT).strip().lower().replace("_", "-")
    aliases = {
        "public": SCIENCE_SOURCE_MODE_PUBLIC_BOOKS,
        "public-book": SCIENCE_SOURCE_MODE_PUBLIC_BOOKS,
        "public-books": SCIENCE_SOURCE_MODE_PUBLIC_BOOKS,
        "gutenberg": SCIENCE_SOURCE_MODE_PUBLIC_BOOKS,
        "gutendex": SCIENCE_SOURCE_MODE_PUBLIC_BOOKS,
    }
    normalized = aliases.get(normalized, normalized)
    return next((item for item in SCIENCE_SOURCE_MODES if item["key"] == normalized), SCIENCE_SOURCE_MODES[0])


def science_source_mode_key(source_mode: str | None) -> str:
    return science_source_mode_config(source_mode)["key"]


def science_sources_for_mode(source_mode: str | None) -> list[dict[str, str]]:
    if science_source_mode_key(source_mode) == SCIENCE_SOURCE_MODE_PUBLIC_BOOKS:
        return [{"name": name, "url": url} for name, url in SCIENCE_PUBLIC_BOOK_SOURCES]
    return [{"name": name, "url": url} for name, url in SCIENCE_SOURCES]


def science_reference_for_item(title: str, topic: str) -> tuple[str, str]:
    return SCIENCE_REFERENCE_BY_TITLE.get(title) or SCIENCE_TOPIC_REFERENCE.get(topic) or SCIENCE_SOURCES[0]


def is_public_science_source(source_url: str | None) -> bool:
    if not source_url:
        return False
    hostname = (urlparse(source_url).hostname or "").lower()
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in SCIENCE_PUBLIC_SOURCE_DOMAINS)


def is_public_book_text_source(source_url: str | None) -> bool:
    if not source_url:
        return False
    hostname = (urlparse(source_url).hostname or "").lower()
    return hostname == "gutenberg.org" or hostname.endswith(".gutenberg.org")


def science_level_config(level: str | None) -> dict[str, str]:
    normalized = (level or "L500-L700").strip()
    return next((item for item in SCIENCE_LEVELS if item["key"] == normalized), SCIENCE_LEVELS[1])


def science_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "science-discovery"


def science_image_url(slug: str) -> str:
    return f"/booklearner/api/science-image/{quote_plus(slug)}.svg?v={SCIENCE_IMAGE_VERSION}"


def science_illustration_url(slug: str, kind: str = "diagram") -> str:
    return f"/booklearner/api/science-illustration/{quote_plus(slug)}/{quote_plus(kind)}.svg?v={SCIENCE_IMAGE_VERSION}"


def hydrate_science_item(item: dict[str, Any]) -> dict[str, Any]:
    slug = str(item.get("slug") or science_slug(str(item.get("title") or "science-discovery")))
    item["imageUrl"] = science_image_url(slug)
    for illustration in item.get("illustrations") or []:
        if isinstance(illustration, dict):
            illustration["imageUrl"] = science_illustration_url(slug, str(illustration.get("kind") or "diagram"))
    return item


def hydrate_science_payload(payload: dict[str, Any]) -> dict[str, Any]:
    for item in payload.get("items") or []:
        if isinstance(item, dict):
            hydrate_science_item(item)
    if isinstance(payload.get("item"), dict):
        hydrate_science_item(payload["item"])
    return payload


def science_svg_lines(text: str, limit: int = 26) -> list[str]:
    words = str(text or "").split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > limit:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines[:3] or ["Science Discovery"]


def science_svg_scene(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "").lower()
    topic = str(item.get("topic") or "科学")
    if "bridge" in title:
        return """
  <g class="scene bridge-scene">
    <rect x="0" y="250" width="800" height="200" fill="#8bd3f7" opacity="0.72"/>
    <path d="M0 302 C110 270 205 328 320 296 C454 258 570 328 800 286 L800 450 L0 450 Z" fill="#4aa8c8" opacity="0.62"/>
    <rect x="78" y="210" width="644" height="28" rx="8" fill="#46586c"/>
    <rect x="66" y="190" width="668" height="24" rx="9" fill="#f5b74b"/>
    <path d="M132 210 C222 120 306 120 398 210" fill="none" stroke="#f08b35" stroke-width="20" stroke-linecap="round"/>
    <path d="M402 210 C492 120 576 120 668 210" fill="none" stroke="#f08b35" stroke-width="20" stroke-linecap="round"/>
    <path d="M148 218 L230 150 L314 218 M420 218 L502 150 L586 218" fill="none" stroke="#fff4cc" stroke-width="9" stroke-linecap="round" opacity="0.9"/>
    <rect x="145" y="235" width="34" height="138" rx="8" fill="#66788c"/>
    <rect x="384" y="235" width="34" height="146" rx="8" fill="#66788c"/>
    <rect x="625" y="235" width="34" height="132" rx="8" fill="#66788c"/>
    <g class="force-arrows">
      <path d="M246 98 L246 165" stroke="#1d7f5b" stroke-width="10" stroke-linecap="round"/>
      <path d="M246 170 L224 142 M246 170 L268 142" fill="none" stroke="#1d7f5b" stroke-width="10" stroke-linecap="round"/>
      <path d="M552 98 L552 165" stroke="#1d7f5b" stroke-width="10" stroke-linecap="round"/>
      <path d="M552 170 L530 142 M552 170 L574 142" fill="none" stroke="#1d7f5b" stroke-width="10" stroke-linecap="round"/>
    </g>
  </g>"""
    if "tree ring" in title:
        return """
  <g class="scene tree-ring-scene">
    <rect x="0" y="284" width="800" height="166" fill="#b8df8a"/>
    <ellipse cx="430" cy="234" rx="220" ry="132" fill="#c98c42"/>
    <ellipse cx="430" cy="234" rx="180" ry="103" fill="none" stroke="#f6d58c" stroke-width="15"/>
    <ellipse cx="430" cy="234" rx="132" ry="76" fill="none" stroke="#8a5527" stroke-width="10" opacity="0.65"/>
    <ellipse cx="430" cy="234" rx="82" ry="45" fill="none" stroke="#f4c970" stroke-width="9"/>
    <ellipse cx="430" cy="234" rx="28" ry="16" fill="#7a4a24" opacity="0.72"/>
    <path d="M222 332 C312 302 530 302 630 336" fill="none" stroke="#236b3b" stroke-width="12" stroke-linecap="round" opacity="0.5"/>
  </g>"""
    if "filter" in title or "water" in title:
        return """
  <g class="scene filter-scene">
    <rect x="0" y="268" width="800" height="182" fill="#bdeaf5"/>
    <path d="M300 90 L500 90 L456 214 L456 330 L344 330 L344 214 Z" fill="#ffffff" opacity="0.86" stroke="#3e8aa1" stroke-width="10"/>
    <path d="M325 164 L475 164" stroke="#f5b74b" stroke-width="18" stroke-linecap="round"/>
    <path d="M336 208 L464 208" stroke="#677a8e" stroke-width="14" stroke-linecap="round"/>
    <path d="M354 254 L446 254" stroke="#79c7a0" stroke-width="14" stroke-linecap="round"/>
    <circle cx="268" cy="114" r="18" fill="#5dbce0"/>
    <circle cx="538" cy="142" r="24" fill="#5dbce0"/>
    <circle cx="488" cy="360" r="20" fill="#5dbce0"/>
  </g>"""
    if "coral" in title:
        return """
  <g class="scene coral-scene">
    <rect x="0" y="0" width="800" height="450" fill="#8ed9d1"/>
    <path d="M0 318 C148 278 280 348 408 302 C550 252 640 318 800 280 L800 450 L0 450 Z" fill="#237b86" opacity="0.64"/>
    <path d="M266 352 L266 270 M266 306 C230 292 218 260 222 232 M266 314 C306 298 318 260 312 228" stroke="#ff8a7a" stroke-width="18" stroke-linecap="round" fill="none"/>
    <path d="M422 370 L422 282 M422 318 C382 300 372 266 378 238 M422 324 C462 302 476 266 470 236" stroke="#ffc25f" stroke-width="16" stroke-linecap="round" fill="none"/>
    <ellipse cx="572" cy="232" rx="54" ry="24" fill="#f7f2b7"/>
    <circle cx="610" cy="226" r="5" fill="#17324d"/>
    <path d="M520 232 L486 214 L486 250 Z" fill="#f7f2b7"/>
  </g>"""
    if topic == "工程":
        return """
  <g class="scene engineering-scene">
    <rect x="0" y="278" width="800" height="172" fill="#d9f2f8"/>
    <rect x="178" y="244" width="444" height="48" rx="12" fill="#485b70"/>
    <path d="M210 244 L282 156 L354 244 M364 244 L436 156 L508 244 M518 244 L590 156 L662 244" fill="none" stroke="#f5b74b" stroke-width="18" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="242" cy="332" r="38" fill="#7890a6"/>
    <circle cx="558" cy="332" r="38" fill="#7890a6"/>
    <path d="M120 366 H680" stroke="#7dc79c" stroke-width="16" stroke-linecap="round"/>
  </g>"""
    if topic == "植物":
        return """
  <g class="scene plant-scene">
    <rect x="0" y="300" width="800" height="150" fill="#b8df8a"/>
    <circle cx="654" cy="100" r="54" fill="#ffe08a" opacity="0.88"/>
    <path d="M394 352 C388 282 398 224 430 168" stroke="#236b3b" stroke-width="18" stroke-linecap="round" fill="none"/>
    <path d="M430 168 C500 128 574 144 626 204 C540 222 474 210 430 168 Z" fill="#57b77c"/>
    <path d="M392 238 C318 194 248 204 198 266 C284 292 348 280 392 238 Z" fill="#74c987"/>
  </g>"""
    if topic == "动物":
        return """
  <g class="scene animal-scene">
    <rect x="0" y="292" width="800" height="158" fill="#b8df8a"/>
    <ellipse cx="430" cy="236" rx="124" ry="72" fill="#d9a063"/>
    <circle cx="528" cy="198" r="48" fill="#d9a063"/>
    <circle cx="544" cy="188" r="7" fill="#17324d"/>
    <path d="M560 210 Q586 214 602 200" stroke="#17324d" stroke-width="7" stroke-linecap="round" fill="none"/>
    <path d="M320 222 C260 180 232 178 196 212" stroke="#d9a063" stroke-width="24" stroke-linecap="round" fill="none"/>
    <path d="M376 298 L354 366 M470 298 L494 366" stroke="#7e5130" stroke-width="18" stroke-linecap="round"/>
  </g>"""
    if topic == "人体":
        return """
  <g class="scene body-scene">
    <rect x="0" y="0" width="800" height="450" fill="#d9f0ff"/>
    <path d="M404 336 C330 276 270 228 270 164 C270 118 304 88 348 88 C374 88 394 104 404 126 C414 104 438 88 466 88 C510 88 544 118 544 164 C544 228 484 276 404 336 Z" fill="#ff6f7d"/>
    <path d="M318 212 H374 L394 176 L430 258 L456 212 H502" fill="none" stroke="#ffffff" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/>
  </g>"""
    if topic == "微生物":
        return """
  <g class="scene microbe-scene">
    <rect x="0" y="0" width="800" height="450" fill="#ede7ff"/>
    <circle cx="326" cy="214" r="86" fill="#8b72d8"/>
    <circle cx="492" cy="178" r="58" fill="#6fcaa0"/>
    <circle cx="510" cy="298" r="72" fill="#b391ee"/>
    <circle cx="298" cy="190" r="12" fill="#fff" opacity="0.72"/>
    <circle cx="468" cy="158" r="9" fill="#fff" opacity="0.72"/>
    <circle cx="536" cy="282" r="11" fill="#fff" opacity="0.72"/>
    <path d="M226 306 C300 266 360 334 438 292 C506 256 558 334 646 286" fill="none" stroke="#ffffff" stroke-width="13" stroke-linecap="round" opacity="0.52"/>
  </g>"""
    if topic == "地球":
        return """
  <g class="scene earth-scene">
    <rect x="0" y="0" width="800" height="450" fill="#d8f3ef"/>
    <path d="M0 312 C126 248 218 326 348 268 C488 206 604 296 800 232 L800 450 L0 450 Z" fill="#4aa886" opacity="0.76"/>
    <path d="M0 356 C174 310 284 386 430 338 C552 298 646 354 800 314 L800 450 L0 450 Z" fill="#8d6a47" opacity="0.78"/>
    <path d="M356 272 C390 314 456 318 492 352 C442 360 398 344 368 318 C340 292 314 292 276 300 C298 280 326 266 356 272 Z" fill="#6fd0e6"/>
  </g>"""
    if topic == "太空":
        return """
  <g class="scene space-scene">
    <rect x="0" y="0" width="800" height="450" fill="#17245a"/>
    <circle cx="640" cy="112" r="54" fill="#f5dda6"/>
    <circle cx="242" cy="92" r="4" fill="#ffffff"/><circle cx="516" cy="68" r="5" fill="#ffffff"/><circle cx="594" cy="260" r="4" fill="#ffffff"/>
    <path d="M376 318 L422 154 L468 318 Z" fill="#f4f6ff"/>
    <path d="M422 154 C450 196 456 236 468 318 L422 292 Z" fill="#c9d7ff"/>
    <circle cx="422" cy="236" r="24" fill="#66c6f2"/>
    <path d="M394 318 L362 374 M450 318 L486 374" stroke="#ffb85c" stroke-width="18" stroke-linecap="round"/>
  </g>"""
    return """
  <g class="scene science-scene">
    <rect x="0" y="286" width="800" height="164" fill="#c8ead8"/>
    <circle cx="394" cy="210" r="96" fill="#77caa0"/>
    <path d="M286 306 C360 246 446 370 522 288" fill="none" stroke="#ffffff" stroke-width="18" stroke-linecap="round" opacity="0.62"/>
    <circle cx="538" cy="166" r="48" fill="#ffe08a" opacity="0.82"/>
  </g>"""


def science_svg_card(item: dict[str, Any]) -> str:
    topic = str(item.get("topic") or "科学")
    title = str(item.get("title") or "Science Discovery")
    themes = {
        "动物": ("#7ccba2", "#1f7a59", "#f6d6a8"),
        "植物": ("#c8eb7f", "#236b3b", "#f4ffe5"),
        "人体": ("#9dd6ff", "#315f9d", "#fff2d6"),
        "微生物": ("#c8b8ff", "#6043a8", "#eef4ff"),
        "地球": ("#8ed9d1", "#1f6f79", "#f2e7c9"),
        "太空": ("#2c3a82", "#111b4d", "#dfe7ff"),
        "工程": ("#ffd16f", "#8a5a18", "#ecfbff"),
    }
    c1, c2, c3 = themes.get(topic, ("#a9e5cf", "#1d7f5b", "#f5fbf7"))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" role="img" aria-label="{html.escape(title)}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
    <radialGradient id="glow" cx="74%" cy="24%" r="58%">
      <stop offset="0%" stop-color="{c3}" stop-opacity="0.92"/>
      <stop offset="100%" stop-color="{c3}" stop-opacity="0"/>
    </radialGradient>
    <filter id="soft">
      <feDropShadow dx="0" dy="12" stdDeviation="14" flood-color="#0d2c24" flood-opacity="0.18"/>
    </filter>
  </defs>
  <rect width="800" height="450" rx="34" fill="url(#bg)"/>
  <rect width="800" height="450" rx="34" fill="url(#glow)"/>
  <circle cx="650" cy="92" r="108" fill="#fff" opacity="0.16"/>
  <circle cx="720" cy="210" r="72" fill="#fff" opacity="0.13"/>
  <path d="M-30 310 C140 210 220 360 375 272 C520 190 610 256 836 176 L836 450 L-30 450 Z" fill="#ffffff" opacity="0.18"/>
  <path d="M72 126 C118 72 174 80 218 126 C266 178 330 170 372 120 C410 76 466 82 502 132" fill="none" stroke="#ffffff" stroke-width="18" stroke-linecap="round" opacity="0.28"/>
  <g filter="url(#soft)">
    {science_svg_scene(item)}
  </g>
</svg>"""


def science_svg_diagram(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "Science Discovery")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" role="img" aria-label="{html.escape(title)} illustration">
  <defs>
    <filter id="soft">
      <feDropShadow dx="0" dy="12" stdDeviation="14" flood-color="#102334" flood-opacity="0.18"/>
    </filter>
  </defs>
  <rect width="800" height="450" rx="34" fill="#f4fbf8"/>
  <g filter="url(#soft)">
    {science_svg_scene(item)}
  </g>
</svg>"""


def science_word_items(words: str) -> list[dict[str, str]]:
    return [
        {
            "word": item.strip(),
            "meaning": "科学关键词",
        }
        for item in words.split(",")
        if item.strip()
    ]


def science_article_paragraphs(title: str, summary: str, topic: str, level_info: dict[str, str]) -> list[str]:
    facts = SCIENCE_CONCEPT_FACTS.get(title, [])
    preview = [
        f"{title} is a science reading about {topic}. {summary}",
        *(facts[:3] or [f"At the {level_info['label']} reading level, look for evidence, cause, and effect."]),
    ]
    return preview[:4]


def science_html_to_plain_text(markup: str, max_chars: int = 5000) -> str:
    text = re.sub(r"(?is)<(script|style|noscript|svg|nav|header|footer|aside|form).*?</\1>", " ", markup or "")
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</(p|div|section|article|h[1-6]|li)>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text).strip()
    return text[:max_chars]


def fetch_science_source_text(source_url: str) -> str:
    if not source_url or not source_url.startswith(("http://", "https://")):
        return ""
    if not is_public_science_source(source_url):
        return ""
    try:
        response = httpx.get(
            source_url,
            follow_redirects=True,
            timeout=4.5,
            headers={
                "User-Agent": "SpeakEasy Science Reader/1.0 (+https://speakeasy.local)",
                "Accept": "text/html, text/plain;q=0.9, */*;q=0.3",
            },
        )
    except httpx.HTTPError:
        return ""
    if response.status_code >= 400:
        return ""
    content_type = response.headers.get("content-type", "")
    if content_type and not any(kind in content_type.lower() for kind in ("text/html", "text/plain", "application/xhtml+xml")):
        return ""
    return science_html_to_plain_text(response.text)


def fetch_gutendex_books(topic: str, limit: int = 28) -> list[dict[str, Any]]:
    query = SCIENCE_PUBLIC_BOOK_TOPIC_QUERIES.get((topic or "全部").strip(), SCIENCE_PUBLIC_BOOK_TOPIC_QUERIES["全部"])
    try:
        response = httpx.get(
            "https://gutendex.com/books",
            params={"languages": "en", "copyright": "false", "search": query},
            follow_redirects=True,
            timeout=3.5,
            headers={
                "User-Agent": "SpeakEasy Science Reader/1.0 (+https://speakeasy.local)",
                "Accept": "application/json",
            },
        )
    except httpx.HTTPError:
        return []
    if response.status_code >= 400:
        return []
    try:
        payload = response.json()
    except ValueError:
        return []
    results = payload.get("results") if isinstance(payload, dict) else []
    if not isinstance(results, list):
        return []
    return [item for item in results[:limit] if isinstance(item, dict)]


def fetch_gutendex_book(book_id: str) -> dict[str, Any] | None:
    safe_id = re.sub(r"[^0-9]", "", str(book_id or ""))
    if not safe_id:
        return None
    try:
        response = httpx.get(
            f"https://gutendex.com/books/{safe_id}",
            follow_redirects=True,
            timeout=3.5,
            headers={
                "User-Agent": "SpeakEasy Science Reader/1.0 (+https://speakeasy.local)",
                "Accept": "application/json",
            },
        )
    except httpx.HTTPError:
        return None
    if response.status_code >= 400:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def public_book_text_url(book: dict[str, Any]) -> str:
    formats = book.get("formats") if isinstance(book, dict) else {}
    if not isinstance(formats, dict):
        return ""
    for media_type, url in formats.items():
        if "text/plain" in str(media_type).lower() and str(url).startswith(("http://", "https://")):
            return str(url)
    return ""


def public_book_author(book: dict[str, Any]) -> str:
    authors = book.get("authors") if isinstance(book, dict) else []
    if isinstance(authors, list) and authors:
        names = [str(author.get("name") or "").strip() for author in authors if isinstance(author, dict)]
        names = [name for name in names if name]
        if names:
            return ", ".join(names[:2])
    return str(book.get("author") or "Project Gutenberg").strip() or "Project Gutenberg"


def clean_public_book_summary(value: str, limit: int = 210) -> str:
    text = re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0].rstrip(".,;:") + "."


def infer_public_book_topic(book: dict[str, Any], fallback_topic: str = "全部") -> str:
    normalized_fallback = (fallback_topic or "全部").strip()
    if normalized_fallback in SCIENCE_TOPIC_CACHE_KEYS and normalized_fallback != "全部":
        return normalized_fallback
    fields = [
        str(book.get("title") or ""),
        " ".join(str(item) for item in (book.get("subjects") or [])[:10]),
        " ".join(str(item) for item in (book.get("bookshelves") or [])[:10]),
    ]
    marker = " ".join(fields).lower()
    checks = [
        ("太空", ("astronomy", "star", "moon", "planet", "solar", "comet")),
        ("工程", ("engineering", "mechanic", "machine", "electric", "technology", "bridge")),
        ("微生物", ("bacteria", "microbe", "germ", "hygiene", "disease")),
        ("人体", ("physiology", "body", "health", "medicine", "heart")),
        ("植物", ("botany", "plant", "flower", "tree", "leaf")),
        ("动物", ("animal", "zoology", "natural history", "bird", "insect")),
        ("地球", ("geology", "earth", "weather", "water", "climate", "volcano")),
    ]
    for topic, keywords in checks:
        if any(keyword in marker for keyword in keywords):
            return topic
    return "地球"


def public_book_summary(book: dict[str, Any], topic: str) -> str:
    summaries = book.get("summaries") if isinstance(book, dict) else []
    if isinstance(summaries, list):
        for item in summaries:
            summary = clean_public_book_summary(str(item or ""))
            if summary:
                return summary
    subjects = [str(item).strip() for item in (book.get("subjects") or []) if str(item).strip()]
    if subjects:
        return clean_public_book_summary(f"A public-domain reading connected to {topic}, with subjects such as {', '.join(subjects[:3])}.")
    author = public_book_author(book)
    title = str(book.get("title") or "Public-domain science reading")
    return clean_public_book_summary(f"{title} is a public-domain English reading by {author} that can support science vocabulary and evidence-based reading.")


def public_book_keywords(book: dict[str, Any], topic: str) -> list[dict[str, str]]:
    base_words = [word.strip() for word in SCIENCE_PUBLIC_BOOK_KEYWORDS.get(topic, "science, reading, evidence").split(",")]
    title_words = [
        word.lower()
        for word in re.findall(r"[A-Za-z]{4,}", str(book.get("title") or ""))
        if word.lower() not in {"with", "from", "that", "this", "book", "story"}
    ]
    words: list[str] = []
    for word in [*title_words, *base_words]:
        if word and word not in words:
            words.append(word)
        if len(words) >= 3:
            break
    return science_word_items(", ".join(words or base_words[:3]))


def public_book_item_from_gutendex(
    book: dict[str, Any],
    level_info: dict[str, str],
    fallback_topic: str = "全部",
) -> dict[str, Any]:
    book_id = str(book.get("id") or "").strip()
    title = str(book.get("title") or "Public-Domain Science Reading").strip()
    topic = infer_public_book_topic(book, fallback_topic)
    author = public_book_author(book)
    summary = public_book_summary(book, topic)
    slug_seed = f"gutenberg-{book_id}-{level_info['key']}" if book_id else f"public-book-{title}-{level_info['key']}"
    slug = science_slug(slug_seed)
    source_url = f"https://www.gutenberg.org/ebooks/{book_id}" if book_id else str(book.get("sourceUrl") or "https://www.gutenberg.org/")
    subjects = [str(item).strip() for item in (book.get("subjects") or []) if str(item).strip()]
    keywords = public_book_keywords(book, topic)
    return {
        "slug": slug,
        "title": title,
        "topic": topic,
        "level": level_info["key"],
        "levelLabel": level_info["label"],
        "summary": summary,
        "imageUrl": science_image_url(slug),
        "source": "Project Gutenberg",
        "sourceUrl": source_url,
        "textSourceUrl": public_book_text_url(book),
        "sourceMode": SCIENCE_SOURCE_MODE_PUBLIC_BOOKS,
        "sourceModeLabel": science_source_mode_config(SCIENCE_SOURCE_MODE_PUBLIC_BOOKS)["label"],
        "author": author,
        "subjects": subjects[:6],
        "article": [
            f"{title} is a public-domain reading connected to {topic}.",
            summary,
            f"Read it at the {level_info['label']} level by looking for evidence, examples, and useful vocabulary.",
        ],
        "words": keywords,
        "quiz": [
            {
                "question": "What is this public-domain reading mostly about?",
                "answer": summary,
            },
            {
                "question": "Which science topic does this reading connect to?",
                "answer": topic,
            },
            {
                "question": "Name one useful word from this reading.",
                "answer": keywords[0]["word"] if keywords else title,
            },
        ],
        "parentNote": f"家长提示：这一条来自 Project Gutenberg 公版书目，适合把英文阅读和 {topic} 主题词汇连起来。蓝思段为站内分级标注，可继续配合 Lexile 工具精算。",
    }


def public_book_item_from_fallback(seed: dict[str, Any], level_info: dict[str, str]) -> dict[str, Any]:
    book = {
        "title": seed["title"],
        "author": seed.get("author", "Project Gutenberg collection"),
        "subjects": seed.get("subjects", []),
        "sourceUrl": seed.get("sourceUrl", "https://www.gutenberg.org/"),
        "summaries": [seed.get("summary", "")],
    }
    item = public_book_item_from_gutendex(book, level_info, seed.get("topic", "地球"))
    item["slug"] = science_slug(f"public-book-{seed['title']}-{level_info['key']}")
    item["sourceUrl"] = seed.get("sourceUrl", item["sourceUrl"])
    return item


def public_book_fallback_seeds(topic: str) -> list[dict[str, Any]]:
    normalized_topic = (topic or "全部").strip() or "全部"
    seeds = [
        seed
        for seed in SCIENCE_PUBLIC_BOOK_FALLBACKS
        if normalized_topic == "全部" or seed.get("topic") == normalized_topic
    ]
    if normalized_topic == "全部":
        combined = list(seeds)
        seen_titles = {str(seed.get("title") or "") for seed in combined}
        for topic_key in SCIENCE_TOPIC_CACHE_KEYS:
            if topic_key == "全部":
                continue
            for seed in public_book_fallback_seeds(topic_key):
                title = str(seed.get("title") or "")
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    combined.append(seed)
        return combined
    topic_labels = {
        "动物": "Natural History",
        "植物": "Botany",
        "人体": "Physiology",
        "微生物": "Germ Life",
        "地球": "Earth Science",
        "太空": "Astronomy",
        "工程": "Engineering",
    }
    label = topic_labels.get(normalized_topic, "Science")
    base_summary = {
        "动物": "Use public-domain natural history writing to practice describing animals, habitats, and observations.",
        "植物": "Use public-domain botany writing to practice plant vocabulary, structure, and growth observations.",
        "人体": "Use public-domain physiology writing to practice body-system vocabulary and careful evidence reading.",
        "微生物": "Use public-domain germ and hygiene writing to discuss microbes, health, and observation.",
        "地球": "Use public-domain earth science writing to practice geology, weather, water, and evidence vocabulary.",
        "太空": "Use public-domain astronomy writing to practice stars, planets, motion, and observation vocabulary.",
        "工程": "Use public-domain engineering writing to practice force, design, machine, and invention vocabulary.",
    }.get(normalized_topic, "Use public-domain science writing to practice evidence-based English reading.")
    while len(seeds) < 5:
        index = len(seeds) + 1
        title = f"A Public-Domain {label} Reader {index}"
        seeds.append(
            {
                "title": title,
                "author": "Project Gutenberg collection",
                "topic": normalized_topic,
                "summary": base_summary,
                "subjects": [label, "Science", "Public domain books"],
                "sourceUrl": f"https://www.gutenberg.org/ebooks/search/?query={quote_plus(label)}",
            }
        )
    return seeds


def strip_gutenberg_boilerplate(text: str) -> str:
    cleaned = re.sub(r"\r\n?", "\n", text or "")
    start_match = re.search(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", cleaned, re.I | re.S)
    if start_match:
        cleaned = cleaned[start_match.end() :]
    end_match = re.search(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*", cleaned, re.I | re.S)
    if end_match:
        cleaned = cleaned[: end_match.start()]
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()


def fetch_public_book_text(source_url: str) -> str:
    if not source_url or not source_url.startswith(("http://", "https://")):
        return ""
    if not is_public_book_text_source(source_url):
        return ""
    try:
        response = httpx.get(
            source_url,
            follow_redirects=True,
            timeout=6,
            headers={
                "User-Agent": "SpeakEasy Science Reader/1.0 (+https://speakeasy.local)",
                "Accept": "text/plain, text/html;q=0.6, */*;q=0.2",
            },
        )
    except httpx.HTTPError:
        return ""
    if response.status_code >= 400:
        return ""
    content_type = response.headers.get("content-type", "").lower()
    raw_text = response.text
    if "text/html" in content_type:
        raw_text = science_html_to_plain_text(raw_text, max_chars=16000)
    return strip_gutenberg_boilerplate(raw_text)[:16000]


def public_book_excerpt_paragraphs(source_text: str, limit: int = 3) -> list[str]:
    if not source_text:
        return []
    paragraphs = [
        re.sub(r"\s+", " ", item).strip()
        for item in re.split(r"\n\s*\n", source_text)
        if 120 <= len(re.sub(r"\s+", " ", item).strip()) <= 650
    ]
    blocked = ("contents", "chapter", "preface", "illustration", "transcriber's note")
    selected: list[str] = []
    for paragraph in paragraphs:
        lower = paragraph.lower()
        if any(token in lower for token in blocked):
            continue
        selected.append(paragraph)
        if len(selected) >= limit:
            break
    return selected


def science_source_sentences(source_text: str, terms: list[str], max_count: int = 2) -> list[str]:
    if not source_text:
        return []
    keywords = {
        word.lower()
        for term in terms
        for word in re.findall(r"[a-zA-Z]{4,}", term or "")
        if word.lower() not in {"science", "reading", "learn", "about", "with", "from", "this", "that"}
    }
    sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", source_text).strip())
    selected: list[str] = []
    blocked = ("cookie", "privacy", "subscribe", "browser", "javascript", "menu", "search")
    for sentence in sentences:
        clean = sentence.strip()
        lower = clean.lower()
        if len(clean) < 65 or len(clean) > 280 or any(token in lower for token in blocked):
            continue
        if keywords and not any(keyword in lower for keyword in keywords):
            continue
        selected.append(clean)
        if len(selected) >= max_count:
            break
    return selected


def science_topic_frame(topic: str) -> str:
    frames = {
        "动物": "a living animal and the environment around it",
        "植物": "a plant, its structure, and the conditions where it grows",
        "人体": "the human body and the systems that keep it working",
        "微生物": "tiny living things that change food, water, soil, or health",
        "地球": "Earth systems that move matter and energy over time",
        "太空": "objects and forces beyond Earth",
        "工程": "a design problem that people solve with materials, forces, and testing",
    }
    return frames.get(topic, "a science question that can be tested with evidence")


def science_topic_investigation_prompt(topic: str) -> str:
    prompts = {
        "动物": "compare the body part or behavior with the survival problem it solves",
        "植物": "trace water, light, or nutrients from the environment into the plant structure",
        "人体": "follow the signal, force, or material as it moves through the body system",
        "微生物": "identify the condition that lets the microbe grow, slow down, or change its surroundings",
        "地球": "connect the moving material to the landform, pattern, or evidence left behind",
        "太空": "separate the force, motion, and energy so the distant object becomes easier to explain",
        "工程": "change one material, shape, setting, or constraint and predict the measurable result",
    }
    return prompts.get(topic, "name the changing condition and the evidence that would show the result")


def science_extension_paragraphs(title: str, topic: str, words: list[str]) -> list[str]:
    facts = SCIENCE_CONCEPT_FACTS.get(title, [])
    focus_words = ", ".join(words[:3]) or "evidence, pattern, result"
    first_fact = facts[0].rstrip(".") if facts else f"{title} connects an observation with a cause and a result"
    second_fact = facts[1].rstrip(".") if len(facts) > 1 else f"the important details belong to {science_topic_frame(topic)}"
    prompt = science_topic_investigation_prompt(topic)
    return [
        f"To go deeper with {title}, turn the facts into a cause-and-effect chain: {first_fact}. Then connect that chain to the next detail: {second_fact}.",
        f"One useful check is to {prompt}. Use {focus_words} to name the evidence a reader could actually observe or measure.",
    ]


def science_illustration_caption(item: dict[str, Any]) -> str:
    topic = str(item.get("topic") or "科学")
    title = str(item.get("title") or "")
    if "bridge" in title.lower():
        return "插图展示桥面、拱形结构、支撑柱和向下的力，帮助理解重量怎样被分散。"
    captions = {
        "植物": "插图展示植物结构和环境条件，帮助把观察到的细节和科学解释连起来。",
        "动物": "插图展示动物身体结构或行为，帮助理解它怎样适应环境。",
        "人体": "插图展示人体系统中的关键结构，帮助理解身体怎样完成任务。",
        "微生物": "插图展示微小生命体和它们造成的变化，帮助理解看不见的科学过程。",
        "地球": "插图展示地球表面的形状和变化，帮助理解时间、运动和环境之间的关系。",
        "太空": "插图展示太空物体或航天结构，帮助理解距离、运动和能量。",
        "工程": "插图展示材料、结构和力之间的关系，帮助理解工程设计为什么有效。",
    }
    return captions.get(topic, "插图展示这个科学问题的关键结构，帮助阅读时抓住证据和因果关系。")


def science_article_illustrations(item: dict[str, Any]) -> list[dict[str, str]]:
    slug = str(item.get("slug") or science_slug(str(item.get("title") or "science-discovery")))
    return [
        {
            "title": f"{item.get('title') or 'Science Discovery'} illustration",
            "caption": science_illustration_caption(item),
            "imageUrl": science_illustration_url(slug),
        }
    ]


def build_public_book_full_article(item: dict[str, Any], source_text: str = "") -> dict[str, Any]:
    title = str(item.get("title") or "Public-Domain Science Reading")
    topic = str(item.get("topic") or "科学")
    summary = str(item.get("summary") or "").strip()
    author = str(item.get("author") or "").strip()
    words = [
        str(word.get("word") or "").strip()
        for word in item.get("words") or []
        if isinstance(word, dict) and str(word.get("word") or "").strip()
    ]
    subjects = [str(subject).strip() for subject in (item.get("subjects") or []) if str(subject).strip()]
    excerpts = public_book_excerpt_paragraphs(source_text)
    source_note = (
        "已读取 Project Gutenberg 公版文本，并整理成站内阅读节选。"
        if excerpts
        else "已接入 Project Gutenberg 公版书目；更新全文时会尝试读取可用的公版文本。"
    )
    intro = f"{title} is a public-domain English reading"
    if author:
        intro += f" by {author}"
    intro += f". In Science Exploration, use it as a {topic} reading path: read for examples, evidence, and vocabulary."
    paragraphs = [
        intro,
        summary or f"This reading can help connect English nonfiction with the topic of {topic}.",
    ]
    if subjects:
        paragraphs.append(f"Catalog subjects include: {', '.join(subjects[:4])}.")
    if excerpts:
        paragraphs.append("Public-domain excerpt:")
        paragraphs.extend(excerpts)
    paragraphs.append(
        f"Reading task: choose one sentence from the text, underline the evidence, and explain how it connects to {', '.join(words[:3]) or topic}."
    )
    return {
        "fullArticle": paragraphs,
        "illustrations": science_article_illustrations(item),
        "fullArticleSourceStatus": "public-domain-book" if excerpts else "public-domain-metadata",
        "fullArticleSourceNote": source_note,
        "fullArticleGeneratedAt": date.today().isoformat(),
    }


def build_science_full_article(item: dict[str, Any], source_text: str = "") -> dict[str, Any]:
    if item.get("sourceMode") == SCIENCE_SOURCE_MODE_PUBLIC_BOOKS:
        return build_public_book_full_article(item, source_text)

    title = str(item.get("title") or "Science Discovery")
    topic = str(item.get("topic") or "科学")
    summary = str(item.get("summary") or "").strip()
    words = [
        str(word.get("word") or "").strip()
        for word in item.get("words") or []
        if isinstance(word, dict) and str(word.get("word") or "").strip()
    ]
    summary_sentence = summary if summary.endswith((".", "!", "?")) else f"{summary}."
    source_name = str(item.get("source") or "参考来源")
    source_url = str(item.get("sourceUrl") or "")
    public_source_text = source_text if is_public_science_source(source_url) else ""
    source_sentences = science_source_sentences(public_source_text, [title, summary, *words])
    concept_facts = SCIENCE_CONCEPT_FACTS.get(title, [])
    source_status = "public-source" if public_source_text else "generated"
    source_note = (
        f"已读取 {source_name} 的公共科普页面，并整理成站内分级阅读。"
        if public_source_text
        else "已根据公共来源选题和站内科学事实库生成分级阅读；更新全文时会尝试读取公共来源页面。"
    )

    paragraphs = [
        f"{title} begins with a real science question in {topic}: how can we explain what we observe? {summary_sentence}",
    ]
    if source_sentences:
        paragraphs.append(f"A public reference page adds this useful detail: {source_sentences[0]}")
    paragraphs.extend(concept_facts)
    if len(source_sentences) > 1:
        paragraphs.append(f"Another detail from the public reference helps connect the idea to evidence: {source_sentences[1]}")
    paragraphs.extend(science_extension_paragraphs(title, topic, words))
    return {
        "fullArticle": paragraphs,
        "illustrations": science_article_illustrations(item),
        "fullArticleSourceStatus": source_status,
        "fullArticleSourceNote": source_note,
        "fullArticleGeneratedAt": date.today().isoformat(),
    }


def science_public_content_key(item: dict[str, Any]) -> str:
    slug = str(item.get("slug") or science_slug(str(item.get("title") or "science-discovery")))
    return f"science:public-content:{SCIENCE_PUBLIC_CONTENT_VERSION}:{slug}"


def read_science_public_content(db: Session, item: dict[str, Any]) -> dict[str, Any] | None:
    entry = db.get(CacheEntry, science_public_content_key(item))
    if not entry or entry.expires_at <= datetime.utcnow():
        return None
    try:
        payload = json.loads(entry.payload)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def write_science_public_content(db: Session, item: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(payload, ensure_ascii=False)
    now = datetime.utcnow()
    key = science_public_content_key(item)
    entry = db.get(CacheEntry, key)
    if entry:
        entry.payload = encoded
        entry.expires_at = now + SCIENCE_PUBLIC_CONTENT_TTL
    else:
        entry = CacheEntry(key=key, payload=encoded, expires_at=now + SCIENCE_PUBLIC_CONTENT_TTL)
        db.add(entry)
    db.commit()
    return payload


def get_science_public_content(
    item: dict[str, Any],
    db: Session,
    *,
    refresh: bool = False,
    source_text: str = "",
) -> dict[str, Any]:
    if not refresh:
        cached = read_science_public_content(db, item)
        if cached:
            return cached
    payload = build_science_full_article(item, source_text)
    return write_science_public_content(db, item, payload)


def merge_science_public_content(item: dict[str, Any], db: Session, *, refresh: bool = False, source_text: str = "") -> dict[str, Any]:
    content = get_science_public_content(item, db, refresh=refresh, source_text=source_text)
    return hydrate_science_item({**item, **content})


def attach_science_public_content(payload: dict[str, Any], db: Session) -> dict[str, Any]:
    for index, item in enumerate(payload.get("items") or []):
        if isinstance(item, dict):
            payload["items"][index] = merge_science_public_content(item, db)
    if isinstance(payload.get("item"), dict):
        payload["item"] = merge_science_public_content(payload["item"], db)
    return hydrate_science_payload(payload)


def build_science_discovery_pool(level: str | None = None) -> list[dict[str, Any]]:
    level_items = SCIENCE_LEVELS if not level or level == "all" else [science_level_config(level)]
    pool: list[dict[str, Any]] = []
    for concept_index, (topic, title, summary, words) in enumerate(SCIENCE_CONCEPTS):
        for level_index, level_info in enumerate(level_items):
            source_name, source_url = science_reference_for_item(title, topic)
            slug = science_slug(f"{title}-{level_info['key']}")
            keywords = science_word_items(words)
            pool.append(
                {
                    "slug": slug,
                    "title": title,
                    "topic": topic,
                    "level": level_info["key"],
                    "levelLabel": level_info["label"],
                    "summary": summary,
                    "imageUrl": science_image_url(slug),
                    "source": source_name,
                    "sourceUrl": source_url,
                    "sourceMode": SCIENCE_SOURCE_MODE_DEFAULT,
                    "sourceModeLabel": science_source_mode_config(SCIENCE_SOURCE_MODE_DEFAULT)["label"],
                    "article": science_article_paragraphs(title, summary, topic, level_info),
                    "words": keywords,
                    "quiz": [
                        {
                            "question": "What is the main idea?",
                            "answer": summary,
                        },
                        {
                            "question": "Which topic does this discovery belong to?",
                            "answer": topic,
                        },
                        {
                            "question": "Name one science word from this article.",
                            "answer": keywords[0]["word"] if keywords else title,
                        },
                    ],
                    "parentNote": f"家长提示：这一条参考 {source_name} 这类儿童科学阅读方向，用适合 {level_info['label']} 的英文重写，重点看孩子是否能说出一个原因和一个结果。",
                }
            )
    return pool


def build_public_books_discovery_pool(level: str | None = None, topic: str = "全部") -> list[dict[str, Any]]:
    level_info = science_level_config(level)
    normalized_topic = (topic or "全部").strip() or "全部"
    books = fetch_gutendex_books(normalized_topic)
    pool = [
        public_book_item_from_gutendex(book, level_info, normalized_topic)
        for book in books
    ]
    pool = [item for item in pool if item.get("title") and item.get("summary")]
    if not pool:
        pool = [
            public_book_item_from_fallback(seed, level_info)
            for seed in public_book_fallback_seeds(normalized_topic)
        ]
    return pool


def science_cache_path(day: str, level: str, topic: str, batch: int, source_mode: str = SCIENCE_SOURCE_MODE_DEFAULT) -> Path:
    safe_level = science_slug(level)
    safe_topic = SCIENCE_TOPIC_CACHE_KEYS.get((topic or "").strip()) or science_slug(topic)
    safe_mode = science_slug(science_source_mode_key(source_mode))
    safe_version = science_slug(SCIENCE_DISCOVERY_DATA_VERSION)
    return SCIENCE_DISCOVERY_CACHE_DIR / f"{day}-{safe_mode}-{safe_level}-{safe_topic}-{batch}-{safe_version}.json"


def build_science_daily_payload(
    level: str,
    topic: str,
    batch: int,
    source_mode: str = SCIENCE_SOURCE_MODE_DEFAULT,
) -> dict[str, Any]:
    day = date.today().isoformat()
    level_info = science_level_config(level)
    normalized_topic = (topic or "全部").strip() or "全部"
    mode_info = science_source_mode_config(source_mode)
    mode_key = mode_info["key"]
    cache_path = science_cache_path(day, level_info["key"], normalized_topic, batch, mode_key)
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(cached, dict):
                return hydrate_science_payload(cached)
        except (OSError, json.JSONDecodeError):
            pass

    if mode_key == SCIENCE_SOURCE_MODE_PUBLIC_BOOKS:
        pool = build_public_books_discovery_pool(level_info["key"], normalized_topic)
        full_pool = pool
    else:
        full_pool = build_science_discovery_pool()
        pool = [
            item
            for item in build_science_discovery_pool(level_info["key"])
            if normalized_topic == "全部" or item["topic"] == normalized_topic
        ]
    rng = random.Random(f"{day}:{mode_key}:{level_info['key']}:{normalized_topic}:{batch}:{SCIENCE_DISCOVERY_DATA_VERSION}")
    selected = rng.sample(pool, k=min(5, len(pool))) if pool else []
    payload = {
        "date": day,
        "level": level_info["key"],
        "levelLabel": level_info["label"],
        "topic": normalized_topic,
        "sourceMode": mode_key,
        "sourceModeLabel": mode_info["label"],
        "sourceModeNote": mode_info["note"],
        "batch": batch,
        "poolSize": len(full_pool),
        "filteredPoolSize": len(pool),
        "items": selected,
        "sources": science_sources_for_mode(mode_key),
    }
    try:
        cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
    return hydrate_science_payload(payload)


def find_public_book_article(slug: str, level: str | None = None) -> dict[str, Any] | None:
    level_info = science_level_config(level)
    normalized_slug = science_slug(slug)
    id_match = re.match(r"gutenberg-([0-9]+)-", normalized_slug)
    if id_match:
        book = fetch_gutendex_book(id_match.group(1))
        if book:
            return hydrate_science_item(public_book_item_from_gutendex(book, level_info))
    fallback_seeds: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for topic in SCIENCE_TOPIC_CACHE_KEYS:
        for seed in public_book_fallback_seeds(topic):
            title = str(seed.get("title") or "")
            if title and title not in seen_titles:
                seen_titles.add(title)
                fallback_seeds.append(seed)
    fallback_candidates = [public_book_item_from_fallback(seed, level_info) for seed in fallback_seeds]
    return next((item for item in fallback_candidates if item["slug"] == normalized_slug), None)


def find_science_article(
    slug: str,
    level: str | None = None,
    source_mode: str | None = None,
) -> dict[str, Any] | None:
    normalized_slug = science_slug(slug)
    mode_key = science_source_mode_key(source_mode)
    if mode_key == SCIENCE_SOURCE_MODE_PUBLIC_BOOKS or normalized_slug.startswith(("gutenberg-", "public-book-")):
        return find_public_book_article(normalized_slug, level)
    candidates = build_science_discovery_pool(level) + build_science_discovery_pool()
    item = next((item for item in candidates if item["slug"] == normalized_slug), None)
    return hydrate_science_item(item) if item else None


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


def growth_trophy_image_url() -> str:
    if PUBLIC_ASSET_DIR.exists():
        matches = sorted(
            [
                path
                for path in PUBLIC_ASSET_DIR.glob(f"{GROWTH_TROPHY_ASSET_STEM}.*")
                if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
            ],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if matches:
            return f"/media/generated-assets/{matches[0].name}"
    return GROWTH_TROPHY_FALLBACK_IMAGE


def store_book_cover_image(title: str, content: bytes) -> str:
    if len(content) < 1000:
        raise ValueError("封面图片文件太小，请换一张清晰图片。")
    suffix = public_asset_extension(content)
    safe_stem = public_asset_slug(Path(title or "book").stem)
    target = BOOK_COVER_DIR / f"{safe_stem}-{uuid4().hex[:8]}{suffix}"
    target.write_bytes(content)
    return f"/media/book-covers/{target.name}"


def store_essay_cover_image(title: str, content: bytes) -> str:
    if len(content) < 1000:
        raise ValueError("作文封面图片太小，请重新生成。")
    ESSAY_COVER_DIR.mkdir(parents=True, exist_ok=True)
    suffix = public_asset_extension(content)
    safe_stem = public_asset_slug(Path(title or "essay").stem)
    target = ESSAY_COVER_DIR / f"{safe_stem}-{uuid4().hex[:8]}{suffix}"
    target.write_bytes(content)
    return f"/media/essay-covers/{target.name}"


IMAGE_SYNC_LOCK = Lock()
IMPORT_PREVIEW_JOB_LOCK = Lock()
CACHE_REFRESHING: set[str] = set()
CACHE_REFRESH_LOCK = Lock()

MEDIA_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
BOOK_COVER_DIR.mkdir(parents=True, exist_ok=True)
ESSAY_COVER_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_ASSET_DIR.mkdir(parents=True, exist_ok=True)
SCIENCE_DISCOVERY_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def login_cookie_max_age_seconds() -> int:
    return max(int(settings.login_cookie_days or 1), 1) * 24 * 60 * 60


def normalize_login_phone(phone: str | None) -> str:
    compact = re.sub(r"[\s\-.()]", "", str(phone or "").strip())
    if compact.startswith("+86"):
        compact = compact[3:]
    elif compact.startswith("86") and len(compact) == 13:
        compact = compact[2:]
    return compact if re.fullmatch(r"1[3-9]\d{9}", compact) else ""


def masked_login_phone(phone: str | None) -> str:
    normalized = normalize_login_phone(phone)
    return f"{normalized[:3]}****{normalized[-4:]}" if normalized else ""


def allowed_login_phones() -> set[str]:
    return {
        normalized
        for normalized in (
            normalize_login_phone(item)
            for item in str(settings.login_phone_allowlist or "").split(",")
        )
        if normalized
    }


def is_login_phone_allowed(phone: str) -> bool:
    allowlist = allowed_login_phones()
    return not allowlist or phone in allowlist


def login_signing_secret() -> str:
    configured = str(settings.login_session_secret or "").strip()
    if configured:
        return configured
    seed = f"{settings.app_name}|{settings.database_url}|{settings.list_delete_password}|phone-login"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def sign_login_payload(payload: str) -> str:
    return hmac.new(login_signing_secret().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def build_login_cookie(phone: str, issued_at: int | None = None) -> str:
    issued = int(issued_at if issued_at is not None else datetime.utcnow().timestamp())
    payload = f"v1:{phone}:{issued}"
    return f"{payload}:{sign_login_payload(payload)}"


def read_login_cookie_info(value: str | None) -> tuple[str, int] | None:
    if not settings.login_enabled or not value:
        return None
    parts = str(value).split(":")
    if len(parts) != 4:
        return None
    version, phone, issued, signature = parts
    if version != "v1":
        return None
    normalized = normalize_login_phone(phone)
    if not normalized or not issued.isdigit():
        return None
    payload = f"{version}:{normalized}:{issued}"
    if not hmac.compare_digest(signature, sign_login_payload(payload)):
        return None
    age = int(datetime.utcnow().timestamp()) - int(issued)
    if age < 0 or age > login_cookie_max_age_seconds():
        return None
    return (normalized, int(issued)) if is_login_phone_allowed(normalized) else None


def read_login_cookie(value: str | None) -> str:
    parsed = read_login_cookie_info(value)
    return parsed[0] if parsed else ""


def login_cookie_values_from_request(request: Request) -> list[str]:
    values: list[str] = []
    cookie_headers = request.headers.getlist("cookie")
    for header in cookie_headers:
        for item in str(header or "").split(";"):
            if "=" not in item:
                continue
            name, value = item.split("=", 1)
            if name.strip() != settings.login_cookie_name:
                continue
            values.append(value.strip().strip('"'))
    fallback = request.cookies.get(settings.login_cookie_name)
    if fallback and not values:
        values.append(str(fallback))
    return values


def authenticated_phone_from_request(request: Request) -> str:
    candidates: list[tuple[str, int, int]] = []
    for index, value in enumerate(login_cookie_values_from_request(request)):
        parsed = read_login_cookie_info(value)
        if parsed:
            candidates.append((parsed[0], parsed[1], index))
    if not candidates:
        return ""
    return max(candidates, key=lambda item: (item[1], item[2]))[0]


def is_login_public_path(path: str) -> bool:
    return (
        path in {"/login", "/logout", "/favicon.ico"}
        or path.startswith("/static/")
        or path.startswith("/media/")
        or path == "/booklearner/api/health"
    )


def safe_next_path(value: str | None) -> str:
    candidate = str(value or "/").strip() or "/"
    parsed = urlparse(candidate)
    if parsed.scheme or parsed.netloc or not candidate.startswith("/") or candidate.startswith("//"):
        return "/"
    if "\r" in candidate or "\n" in candidate:
        return "/"
    return candidate


def login_redirect_url(request: Request) -> str:
    target = request.url.path
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return f"/login?next={quote_plus(target)}"


def login_template_context(
    request: Request,
    next_path: str = "/",
    error: str = "",
    phone: str = "",
) -> dict[str, Any]:
    version_matrix = ensure_version_matrix_file()
    return {
        "request": request,
        "app_name": settings.app_name,
        "static_version": static_asset_version(),
        "shell_context": {
            "appName": settings.app_name,
            "currentUser": None,
            "versionMatrix": version_matrix,
        },
        "version_matrix": version_matrix,
        "next_path": safe_next_path(next_path),
        "error": error,
        "phone": phone,
    }


def login_cookie_secure(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    return request.url.scheme == "https" or "https" in forwarded_proto.lower().split(",")


def canonical_public_host_redirect_url(request: Request) -> str:
    host = request.headers.get("host", "").split(":", 1)[0].lower()
    if host != "newabby.com":
        return ""
    target = f"https://www.newabby.com{request.url.path or '/'}"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return target


def login_cookie_domain(request: Request) -> str | None:
    host = request.headers.get("host", "").split(":", 1)[0].lower()
    return ".newabby.com" if host in {"newabby.com", "www.newabby.com"} else None


def clear_login_cookies(response: Response) -> None:
    response.delete_cookie(key=settings.login_cookie_name, path="/")
    response.delete_cookie(key=settings.login_cookie_name, path="/", domain=".newabby.com")
    response.delete_cookie(key=settings.login_cookie_name, path="/", domain="newabby.com")
    response.delete_cookie(key=settings.login_cookie_name, path="/", domain="www.newabby.com")


def set_login_cookie(response: Response, request: Request, phone: str) -> None:
    clear_login_cookies(response)
    cookie_value = build_login_cookie(phone)
    cookie_args: dict[str, Any] = {
        "key": settings.login_cookie_name,
        "value": cookie_value,
        "max_age": login_cookie_max_age_seconds(),
        "httponly": True,
        "secure": login_cookie_secure(request),
        "samesite": "lax",
        "path": "/",
    }
    response.set_cookie(**cookie_args)
    domain = login_cookie_domain(request)
    if domain:
        response.set_cookie(**{**cookie_args, "domain": domain})


LOGIN_PASSWORD_ALGORITHM = "pbkdf2_sha256"
LOGIN_PASSWORD_ITERATIONS = 260000
LOGIN_PASSWORD_MIN_LENGTH = 6


def normalize_login_password(password: str | None) -> str:
    return str(password or "").strip()


def hash_login_password(password: str) -> str:
    salt = secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        LOGIN_PASSWORD_ITERATIONS,
    ).hex()
    return f"{LOGIN_PASSWORD_ALGORITHM}${LOGIN_PASSWORD_ITERATIONS}${salt}${digest}"


def verify_login_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    parts = str(password_hash).split("$")
    if len(parts) != 4:
        return False
    algorithm, iterations_text, salt, digest = parts
    if algorithm != LOGIN_PASSWORD_ALGORITHM or not iterations_text.isdigit():
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations_text),
    ).hex()
    return hmac.compare_digest(candidate, digest)


ADMIN_ROLE_OPTIONS = [
    {"key": "admin", "label": "管理员"},
    {"key": "teacher", "label": "老师"},
    {"key": "viewer", "label": "只读"},
]
ADMIN_PERMISSION_OPTIONS = [
    {"key": "admin", "label": "后台管理"},
    {"key": "word_edit", "label": "单词编辑"},
    {"key": "image_manage", "label": "图片管理"},
    {"key": "audio_manage", "label": "音频管理"},
    {"key": "import_manage", "label": "导入管理"},
    {"key": "spb_sync", "label": "SPB 同步"},
    {"key": "challenge_manage", "label": "挑战管理"},
]
ADMIN_IMAGE_AI_OPTIONS = [
    {"provider": "dashscope", "model": "wan2.7-image-pro", "label": "阿里 · wan2.7-image-pro"},
    {"provider": "dashscope", "model": "qwen-image-2.0-pro", "label": "阿里 · qwen-image-2.0-pro"},
    {"provider": "dashscope", "model": "wan2.6-t2i", "label": "阿里 · wan2.6-t2i"},
    {"provider": "openai", "model": "gpt-image-1", "label": "OpenAI · gpt-image-1"},
    {"provider": "tencent_hunyuan", "model": "TextToImageRapid", "label": "腾讯混元 · TextToImageRapid"},
]
ADMIN_AUDIO_AI_OPTIONS = [
    {"provider": "openai", "label": "OpenAI TTS"},
    {"provider": "dashscope", "label": "阿里 DashScope TTS"},
    {"provider": "aliyun", "label": "阿里云 NLS TTS"},
]


def admin_permission_defaults(role: str) -> dict[str, bool]:
    keys = [item["key"] for item in ADMIN_PERMISSION_OPTIONS]
    if role == "admin":
        return {key: True for key in keys}
    if role == "teacher":
        return {key: key in {"word_edit", "image_manage", "audio_manage", "import_manage", "challenge_manage"} for key in keys}
    return {key: key == "challenge_manage" for key in keys}


def parse_admin_permissions(raw_permissions: str | None, role: str) -> dict[str, bool]:
    defaults = admin_permission_defaults(role)
    if not raw_permissions:
        return defaults
    try:
        loaded = json.loads(raw_permissions)
    except json.JSONDecodeError:
        return defaults
    if not isinstance(loaded, dict):
        return defaults
    return {
        key: bool(loaded.get(key, defaults[key]))
        for key in defaults
    }


def encode_admin_permissions(permissions: dict[str, Any] | None, role: str) -> str:
    defaults = admin_permission_defaults(role)
    incoming = permissions if isinstance(permissions, dict) else {}
    normalized = {key: bool(incoming.get(key, defaults[key])) for key in defaults}
    if role == "admin":
        normalized["admin"] = True
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True)


def admin_user_display_name(phone: str, role: str) -> str:
    suffix = phone[-4:] if len(phone) >= 4 else phone
    return ("管理员" if role == "admin" else "用户") + suffix


def default_admin_image_ai_pair() -> tuple[str, str]:
    configured_provider = str(settings.ai_image_provider or "dashscope").strip()
    for item in ADMIN_IMAGE_AI_OPTIONS:
        if item["provider"] == configured_provider:
            return item["provider"], item["model"]
    return "dashscope", "wan2.7-image-pro"


def valid_admin_image_ai_values() -> set[str]:
    return {
        admin_image_ai_value(item["provider"], item["model"])
        for item in ADMIN_IMAGE_AI_OPTIONS
    }


def normalize_admin_user_ai_fields(user: AdminUserSetting) -> bool:
    changed = False
    if admin_image_ai_value(user.image_ai_provider, user.image_ai_model) not in valid_admin_image_ai_values():
        user.image_ai_provider, user.image_ai_model = default_admin_image_ai_pair()
        changed = True
    normalized_audio_provider = normalize_admin_audio_provider(user.audio_ai_provider)
    if user.audio_ai_provider != normalized_audio_provider:
        user.audio_ai_provider = normalized_audio_provider
        changed = True
    normalized_voice_gender = normalize_admin_voice_gender(user.audio_voice_gender)
    if user.audio_voice_gender != normalized_voice_gender:
        user.audio_voice_gender = normalized_voice_gender
        changed = True
    return changed


def active_admin_user_count(db: Session) -> int:
    return db.scalar(
        select(func.count(AdminUserSetting.id)).where(
            AdminUserSetting.role == "admin",
            AdminUserSetting.is_active.is_(True),
        )
    ) or 0


def promote_admin_user(user: AdminUserSetting) -> bool:
    changed = False
    if user.role != "admin":
        user.role = "admin"
        changed = True
    permissions = encode_admin_permissions(None, "admin")
    if user.permissions != permissions:
        user.permissions = permissions
        changed = True
    default_username = admin_user_display_name(user.phone, "viewer")
    if not user.username or user.username == default_username:
        user.username = admin_user_display_name(user.phone, "admin")
        changed = True
    return changed


def get_or_create_admin_user(db: Session, phone: str) -> AdminUserSetting | None:
    normalized = normalize_login_phone(phone)
    if not normalized:
        return None
    existing = db.scalar(select(AdminUserSetting).where(AdminUserSetting.phone == normalized))
    if existing:
        changed = normalize_admin_user_ai_fields(existing)
        if not existing.username:
            existing.username = admin_user_display_name(existing.phone, existing.role)
            changed = True
        if existing.is_active and active_admin_user_count(db) == 0:
            changed = promote_admin_user(existing) or changed
        if changed:
            db.add(existing)
            db.commit()
            db.refresh(existing)
        return existing
    role = "admin" if active_admin_user_count(db) == 0 else "viewer"
    image_provider, image_model = default_admin_image_ai_pair()
    user = AdminUserSetting(
        phone=normalized,
        username=admin_user_display_name(normalized, role),
        role=role,
        permissions=encode_admin_permissions(None, role),
        image_ai_provider=image_provider,
        image_ai_model=image_model,
        audio_ai_provider=settings.ai_tts_provider or "openai",
        audio_voice_gender="female",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def current_admin_user(request: Request, db: Session) -> AdminUserSetting:
    phone = authenticated_phone_from_request(request)
    if not phone:
        raise HTTPException(status_code=401, detail="请先用手机号登录。")
    user = get_or_create_admin_user(db, phone)
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="账号已停用。")
    return user


def admin_user_can(user: AdminUserSetting | None, permission_key: str) -> bool:
    if not user or not user.is_active:
        return False
    if user.role == "admin":
        return True
    return bool(parse_admin_permissions(user.permissions, user.role).get(permission_key))


def require_admin_panel_access(request: Request, db: Session) -> AdminUserSetting:
    user = current_admin_user(request, db)
    if not admin_user_can(user, "admin"):
        raise HTTPException(status_code=403, detail="没有后台管理权限。")
    return user


def admin_image_ai_value(provider: str | None, model: str | None) -> str:
    return f"{provider or ''}:{model or ''}"


def parse_admin_image_ai_value(value: str | None) -> tuple[str, str]:
    raw = str(value or "").strip()
    if ":" not in raw:
        return default_admin_image_ai_pair()
    provider, model = raw.split(":", 1)
    return (provider, model) if admin_image_ai_value(provider, model) in valid_admin_image_ai_values() else default_admin_image_ai_pair()


def normalize_admin_audio_provider(provider: str | None) -> str:
    normalized = str(provider or settings.ai_tts_provider or "openai").strip().lower()
    allowed = {item["provider"] for item in ADMIN_AUDIO_AI_OPTIONS}
    return normalized if normalized in allowed else (settings.ai_tts_provider or "openai")


def normalize_admin_voice_gender(value: str | None) -> str:
    return value if value in {"female", "male"} else "female"


def admin_user_summary(user: AdminUserSetting | None, phone: str | None = None) -> dict[str, Any] | None:
    masked_phone = masked_login_phone(user.phone if user else phone)
    if not masked_phone:
        return None
    username = user.username if user else ""
    if user and not username:
        username = admin_user_display_name(user.phone, user.role)
    permissions = parse_admin_permissions(user.permissions, user.role) if user else {}
    return {
        "phoneMasked": masked_phone,
        "username": username,
        "role": user.role if user else "viewer",
        "canAdmin": admin_user_can(user, "admin"),
        "permissions": permissions,
        "imageAi": {
            "provider": user.image_ai_provider,
            "model": user.image_ai_model,
        } if user else None,
        "audioAi": {
            "provider": user.audio_ai_provider,
            "voiceGender": user.audio_voice_gender,
        } if user else None,
    }


def serialize_admin_user(user: AdminUserSetting) -> dict[str, Any]:
    return {
        "id": user.id,
        "phone": user.phone,
        "phoneMasked": masked_login_phone(user.phone),
        "username": user.username,
        "role": user.role,
        "permissions": parse_admin_permissions(user.permissions, user.role),
        "hasLoginPassword": bool(user.login_password_hash),
        "imageAiValue": admin_image_ai_value(user.image_ai_provider, user.image_ai_model),
        "audioAiProvider": user.audio_ai_provider,
        "audioVoiceGender": user.audio_voice_gender,
        "isActive": bool(user.is_active),
        "createdAt": user.created_at.isoformat() if user.created_at else "",
        "updatedAt": user.updated_at.isoformat() if user.updated_at else "",
    }


def preferred_admin_user_ai(db: Session, request: Request) -> AdminUserSetting | None:
    phone = authenticated_phone_from_request(request)
    return get_or_create_admin_user(db, phone) if phone else None


app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.middleware("http")
async def require_phone_login(request: Request, call_next):
    path = request.url.path
    canonical_redirect = canonical_public_host_redirect_url(request)
    if canonical_redirect and path != "/logout":
        return RedirectResponse(url=canonical_redirect, status_code=308)
    if not settings.login_enabled or request.method == "OPTIONS" or is_login_public_path(path):
        return await call_next(request)
    if authenticated_phone_from_request(request):
        return await call_next(request)
    if path.startswith("/api/") or path.startswith("/booklearner/api/"):
        return JSONResponse({"detail": "请先用手机号登录。"}, status_code=401)
    return RedirectResponse(url=login_redirect_url(request), status_code=303)


@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/static/vue/"):
        response.headers["Cache-Control"] = "no-cache, max-age=0, must-revalidate"
    elif path.startswith("/static/") or path.startswith("/media/"):
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
    default_version = normalize_version_number(str(default_version_matrix().get("version") or "").strip())
    return release_version_sort_key(default_version) > release_version_sort_key(current_version)


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
    response = templates.TemplateResponse("vue_app.html", page_context(request, db, {"vue_path": vue_path}))
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return RedirectResponse(url="/static/speakeasy-mouth-logo.svg", status_code=302)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = Query(default="/")):
    next_path = safe_next_path(next)
    if next_path == "/login":
        next_path = "/"
    if authenticated_phone_from_request(request):
        return RedirectResponse(url=next_path, status_code=303)
    return templates.TemplateResponse("login.html", login_template_context(request, next_path))


@app.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    db: Session = Depends(get_db),
    phone: str = Form(default=""),
    password: str = Form(default=""),
    next: str = Form(default="/"),
):
    next_path = safe_next_path(next)
    if next_path == "/login":
        next_path = "/"
    normalized = normalize_login_phone(phone)
    if not normalized:
        return templates.TemplateResponse(
            "login.html",
            login_template_context(request, next_path, "请输入正确的 11 位手机号。", phone),
            status_code=400,
        )
    if not is_login_phone_allowed(normalized):
        return templates.TemplateResponse(
            "login.html",
            login_template_context(request, next_path, "这个手机号暂时没有访问权限。", phone),
            status_code=403,
        )
    normalized_password = normalize_login_password(password)
    user = db.scalar(select(AdminUserSetting).where(AdminUserSetting.phone == normalized))
    if not user:
        if active_admin_user_count(db) > 0:
            return templates.TemplateResponse(
                "login.html",
                login_template_context(request, next_path, "这个手机号还没有后台账号。", phone),
                status_code=403,
            )
        if len(normalized_password) < LOGIN_PASSWORD_MIN_LENGTH:
            return templates.TemplateResponse(
                "login.html",
                login_template_context(request, next_path, "首次登录请设置至少 6 位密码。", phone),
                status_code=400,
            )
        user = get_or_create_admin_user(db, normalized)
        user.login_password_hash = hash_login_password(normalized_password)
        db.add(user)
        db.commit()
        db.refresh(user)
    if not user.is_active:
        return templates.TemplateResponse(
            "login.html",
            login_template_context(request, next_path, "账号已停用。", phone),
            status_code=403,
        )
    if not user.login_password_hash:
        return templates.TemplateResponse(
            "login.html",
            login_template_context(request, next_path, "这个账号还没有设置登录密码，请联系管理员。", phone),
            status_code=403,
        )
    if not verify_login_password(normalized_password, user.login_password_hash):
        return templates.TemplateResponse(
            "login.html",
            login_template_context(request, next_path, "手机号或密码不正确。", phone),
            status_code=403,
        )
    response = RedirectResponse(url=next_path, status_code=303)
    set_login_cookie(response, request, normalized)
    return response


@app.api_route("/logout", methods=["GET", "POST"], include_in_schema=False)
def logout(request: Request):
    response = RedirectResponse(
        url="https://www.newabby.com/login" if canonical_public_host_redirect_url(request) else "/login",
        status_code=303,
    )
    clear_login_cookies(response)
    return response


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema_columns()
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    BOOK_COVER_DIR.mkdir(parents=True, exist_ok=True)
    ESSAY_COVER_DIR.mkdir(parents=True, exist_ok=True)
    SCIENCE_DISCOVERY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ensure_version_matrix_file()
    with SessionLocal() as db:
        backfill_essay_best_writing_results(db)
        seed_cat_world_scenes(db)
        seed_cat_world_limited_cat_stock(db)
        seed_daily_quotes(db)
        ensure_default_word_list(db)
        seed_word_resource_pool(db)


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


@app.get("/booklearner/science", response_class=HTMLResponse)
def good_words_science_home_page():
    return RedirectResponse(url="/booklearner", status_code=302)


@app.get("/booklearner/science/{slug}", response_class=HTMLResponse)
def good_words_science_page(slug: str):
    return RedirectResponse(url="/booklearner", status_code=302)


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


@app.get("/essays", response_class=HTMLResponse)
def essays_page(request: Request, db: Session = Depends(get_db)):
    return vue_shell(request, db, "essays")


@app.get("/debate", response_class=HTMLResponse)
def debate_page(request: Request, db: Session = Depends(get_db)):
    return vue_shell(request, db, "debate")


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


@app.get("/booklearner/api/science-image/{slug}.svg")
def good_words_science_image(slug: str):
    item = find_science_article(slug) or {
        "slug": slug,
        "title": slug.replace("-", " ").title(),
        "topic": "科学",
        "summary": "A small science discovery for today's reading.",
    }
    return Response(
        content=science_svg_card(item),
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/booklearner/api/science-illustration/{slug}/{kind}.svg")
def good_words_science_illustration(slug: str, kind: str):
    item = find_science_article(slug) or {
        "slug": slug,
        "title": slug.replace("-", " ").title(),
        "topic": "科学",
        "summary": "A small science discovery for today's reading.",
    }
    return Response(
        content=science_svg_diagram(item),
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/booklearner/api/science-daily")
def good_words_science_daily(
    level: str = Query(default="L500-L700"),
    topic: str = Query(default="全部"),
    source_mode: str = Query(default=SCIENCE_SOURCE_MODE_DEFAULT),
    batch: int = Query(default=0, ge=0, le=50),
    db: Session = Depends(get_db),
):
    return attach_science_public_content(
        build_science_daily_payload(level=level, topic=topic, batch=batch, source_mode=source_mode),
        db,
    )


@app.get("/booklearner/api/science-daily/{slug}/full-article")
def good_words_science_daily_full_article(
    slug: str,
    level: str | None = Query(default=None),
    source_mode: str = Query(default=SCIENCE_SOURCE_MODE_DEFAULT),
    db: Session = Depends(get_db),
):
    item = find_science_article(slug, level, source_mode=source_mode)
    if not item:
        raise HTTPException(status_code=404, detail="知识点不存在。")
    if item.get("sourceMode") == SCIENCE_SOURCE_MODE_PUBLIC_BOOKS:
        source_text = fetch_public_book_text(str(item.get("textSourceUrl") or ""))
    else:
        source_text = fetch_science_source_text(str(item.get("sourceUrl") or ""))
    item = merge_science_public_content(item, db, refresh=True, source_text=source_text)
    return {
        "item": item,
        "sources": science_sources_for_mode(item.get("sourceMode") or source_mode),
    }


@app.get("/booklearner/api/science-daily/{slug}")
def good_words_science_daily_article(
    slug: str,
    level: str | None = Query(default=None),
    source_mode: str = Query(default=SCIENCE_SOURCE_MODE_DEFAULT),
    db: Session = Depends(get_db),
):
    item = find_science_article(slug, level, source_mode=source_mode)
    if not item:
        raise HTTPException(status_code=404, detail="知识点不存在。")
    item = merge_science_public_content(item, db)
    return {
        "item": item,
        "sources": science_sources_for_mode(item.get("sourceMode") or source_mode),
    }


@app.get("/booklearner/api/history/{analysis_id}")
def good_words_history_detail(analysis_id: int):
    item = get_good_words_analysis(analysis_id)
    if not item:
        raise HTTPException(status_code=404, detail="记录不存在，或 MySQL 未启用。")
    return item


@app.post("/booklearner/api/history/{analysis_id}/cover")
async def good_words_update_cover(
    analysis_id: int,
    file: UploadFile = File(...),
):
    item = get_good_words_analysis(analysis_id)
    if not item:
        raise HTTPException(status_code=404, detail="记录不存在，或 MySQL 未启用。")

    content = await file.read()
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件。")

    book = item.get("book") if isinstance(item, dict) else {}
    title = (book or {}).get("title") or item.get("title") or f"book-{analysis_id}"
    try:
        cover_url = store_book_cover_image(str(title), content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    updated = update_good_words_analysis_cover(analysis_id, cover_url)
    if not updated:
        raise HTTPException(status_code=400, detail="封面保存失败。")
    return {"ok": True, "coverUrl": cover_url, "result": updated}


@app.post("/booklearner/api/history/{analysis_id}/ai-cover")
async def good_words_generate_ai_cover(
    analysis_id: int,
    model: str = Form(default="wan2.7-image-pro"),
    theme: str = Form(default=""),
    style: str = Form(default="书籍封面插画"),
):
    item = get_good_words_analysis(analysis_id)
    if not item:
        raise HTTPException(status_code=404, detail="记录不存在，或 MySQL 未启用。")

    book = item.get("book") if isinstance(item, dict) else {}
    title = str((book or {}).get("title") or item.get("title") or "English book").strip()
    authors = (book or {}).get("authors")
    if isinstance(authors, list):
        author_text = " / ".join(str(author) for author in authors if author)
    else:
        author_text = str((book or {}).get("author") or item.get("author") or "").strip()
    stats = item.get("stats") if isinstance(item, dict) else {}
    selected_theme = " ".join((theme or "").split())[:80]
    selected_style = " ".join((style or "书籍封面插画").split())[:80]
    selected_model = " ".join((model or "wan2.7-image-pro").split())[:80]
    prompt = " ".join(
        part
        for part in [
            "Create a polished book cover illustration for an English reading excerpt system.",
            f"Book title: {title}.",
            f"Author: {author_text}." if author_text else "",
            f"Theme: {selected_theme}." if selected_theme else "",
            f"Visual style: {selected_style}.",
            "Portrait book-cover composition, rich but clean, literary, high quality.",
            "No readable text, no letters, no Chinese characters, no logos, no watermarks, no UI elements.",
            "Leave all typography to the application.",
            f"Book has about {stats.get('words')} words." if isinstance(stats, dict) and stats.get("words") else "",
        ]
        if part
    )
    try:
        content = await generate_dashscope_prompt_image(
            api_key=settings.dashscope_api_key,
            endpoint=settings.dashscope_image_endpoint,
            task_endpoint=settings.dashscope_task_endpoint,
            poll_seconds=settings.dashscope_image_poll_seconds,
            timeout_seconds=settings.dashscope_image_timeout_seconds,
            model=selected_model,
            prompt=prompt,
        )
        cover_url = store_book_cover_image(title, content)
    except RuntimeError as exc:
        detail = str(exc)
        if "not configured" in detail:
            raise HTTPException(status_code=400, detail=detail) from exc
        if is_ai_quota_error(detail):
            raise HTTPException(status_code=402, detail="额度已经用完") from exc
        raise HTTPException(status_code=502, detail=f"AI 封面生成失败: {detail}") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:400] if exc.response is not None else str(exc)
        if is_ai_quota_error(detail):
            raise HTTPException(status_code=402, detail="额度已经用完") from exc
        raise HTTPException(status_code=502, detail=f"AI 封面生成失败: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI 封面生成失败: {exc}") from exc

    updated = update_good_words_analysis_cover(analysis_id, cover_url)
    if not updated:
        raise HTTPException(status_code=400, detail="AI 封面保存失败。")
    return {"ok": True, "coverUrl": cover_url, "result": updated, "model": selected_model}


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

    word_list = WordList(name=title, display_order=next_word_list_display_order(db))
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
        "growth": learning_growth_summary(db),
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


@app.get("/api/vue/growth")
def vue_growth_api(db: Session = Depends(get_db)):
    return {"growth": learning_growth_summary(db)}


@app.get("/api/vue/cat-world")
def vue_cat_world_api(request: Request, db: Session = Depends(get_db)):
    phone = require_cat_world_phone(request)
    state = get_or_create_cat_world_state(db, phone)
    return serialize_cat_world_payload(db, state)


@app.post("/api/vue/cat-world/play-time")
async def vue_cat_world_play_time_api(request: Request, db: Session = Depends(get_db)):
    phone = require_cat_world_phone(request)
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="计时状态不是有效 JSON。") from exc
    active = (body or {}).get("active") is not False
    state = get_or_create_cat_world_state(db, phone)
    reward_source = cat_world_play_time_reward_source(db, phone)
    play_time = cat_world_update_play_time_session(
        state,
        cat_world_today_spelling_count(db),
        active=active,
        reward_seconds=int(reward_source["seconds"]),
    )
    db.add(state)
    db.commit()
    return {"ok": True, "playTime": play_time}


@app.post("/api/vue/cat-world/purchase")
async def vue_cat_world_purchase_api(request: Request, db: Session = Depends(get_db)):
    phone = require_cat_world_phone(request)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="购买数据不是有效 JSON。") from exc
    item_id = str((payload or {}).get("itemId") or "").strip()
    shop_by_id = cat_world_effective_shop_by_id(db)
    item = shop_by_id.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="没有找到这个猫咪物品。")

    state = get_or_create_cat_world_state(db, phone)
    current = serialize_cat_world_payload(db, state)
    inventory = parse_cat_world_inventory(state.inventory)
    owned_cats = parse_cat_world_cats(state.cats)
    blind_box_result: dict[str, Any] | None = None
    adopted_profile: CatWorldCatProfile | None = None
    if item["category"] == "cat":
        if current["energy"]["available"] < int(item["cost"]):
            raise HTTPException(status_code=400, detail="能量值还不够，先去学习赚一点。")
        now = datetime.utcnow()
        cat_care = parse_cat_world_care(state.cat_care)
        care_row = {**cat_care.get(item_id, {})}
        was_escaped = bool(care_row.get("escapedAt"))
        care_row.update(
            {
                "lastBathAt": now.replace(microsecond=0).isoformat() + "Z",
                "hungerSince": "",
                "lowMoodSince": "",
                "escapedAt": "",
                "escapeReason": "",
                "escapeLabel": "",
                "adoptionCount": max(int(care_row.get("adoptionCount") or 0), 0) + 1,
            }
        )
        cat_care[item_id] = care_row
        state.cat_care = encode_cat_world_care(cat_care)
        if item_id not in owned_cats:
            owned_cats.append(item_id)
        state.cats = encode_cat_world_cats(owned_cats)
        state.selected_cat = item_id
        adopted_profile = create_cat_world_cat_profile(db, state, item_id, "shop")
        state.selected_cat_profile = adopted_profile.profile_id
        if was_escaped:
            adopted_cat = cat_world_cat_profile_payload(adopted_profile)
            log = get_or_create_cat_world_daily_log(
                db,
                state.phone,
                adopted_profile.profile_id,
                date.today(),
                now,
                adopted_cat,
            )
            log.energy_score = 68
            log.mood_score = 70
            log.hourly_energy_decay = 0
            log.hourly_mood_decay = 0
            log.last_decay_at = now
            log.agent_state = None
            log.damaged_item_id = None
            db.add(log)
    elif item["category"] == "blind-box":
        state = db.scalar(
            select(CatWorldState).where(CatWorldState.id == state.id).with_for_update()
        ) or state
        owned_cats = parse_cat_world_cats(state.cats)
        available_energy = max(int(current["energy"]["earned"]) - max(int(state.energy_spent or 0), 0), 0)
        if available_energy < int(item["cost"]):
            raise HTTPException(status_code=400, detail="能量值还不够，先去学习赚一点。")
        series_key = str(item.get("seriesKey") or CAT_WORLD_CURRENT_BLIND_BOX_SERIES_KEY)
        series = CAT_WORLD_BLIND_BOX_SERIES_BY_KEY.get(series_key)
        if not series:
            raise HTTPException(status_code=404, detail="没有找到这一期猫咪盲盒。")
        existing_draw = db.scalar(
            select(CatWorldBlindBoxDraw).where(
                CatWorldBlindBoxDraw.phone == state.phone,
                CatWorldBlindBoxDraw.series_key == series_key,
            ).with_for_update()
        )
        if existing_draw:
            raise HTTPException(status_code=409, detail="本期盲盒每个账号只能开启一次，你已经抽取过了。")
        limited_ids = {str(seed["cat"]["id"]) for seed in series["cats"]}
        stock_rows = db.scalars(
            select(CatWorldLimitedCatStock)
            .where(
                CatWorldLimitedCatStock.series_key == series_key,
                CatWorldLimitedCatStock.cat_id.in_(limited_ids),
            )
            .with_for_update()
        ).all()
        eligible_rows = [
            row
            for row in stock_rows
            if row.is_active
            and row.cat_id not in owned_cats
            and max(int(row.total_stock or 0) - int(row.claimed_count or 0), 0) > 0
        ]
        if not eligible_rows:
            raise HTTPException(status_code=409, detail="本期可抽取的限定猫咪已经售罄。")
        remaining_total = sum(max(int(row.total_stock or 0) - int(row.claimed_count or 0), 0) for row in eligible_rows)
        ticket = secrets.randbelow(remaining_total)
        selected_stock = eligible_rows[-1]
        for row in eligible_rows:
            remaining = max(int(row.total_stock or 0) - int(row.claimed_count or 0), 0)
            if ticket < remaining:
                selected_stock = row
                break
            ticket -= remaining
        selected_stock.claimed_count = max(int(selected_stock.claimed_count or 0), 0) + 1
        selected_cat = CAT_WORLD_CAT_BY_ID[selected_stock.cat_id]
        if selected_stock.cat_id not in owned_cats:
            owned_cats.append(selected_stock.cat_id)
        state.cats = encode_cat_world_cats(owned_cats)
        state.selected_cat = selected_stock.cat_id
        adopted_profile = create_cat_world_cat_profile(db, state, selected_stock.cat_id, "blind-box")
        state.selected_cat_profile = adopted_profile.profile_id
        now = datetime.utcnow()
        cat_care = parse_cat_world_care(state.cat_care)
        cat_care[selected_stock.cat_id] = {
            **cat_care.get(selected_stock.cat_id, {}),
            "lastBathAt": now.replace(microsecond=0).isoformat() + "Z",
            "hungerSince": "",
            "lowMoodSince": "",
            "escapedAt": "",
            "escapeReason": "",
            "escapeLabel": "",
            "adoptionCount": max(int(cat_care.get(selected_stock.cat_id, {}).get("adoptionCount") or 0), 0) + 1,
        }
        state.cat_care = encode_cat_world_care(cat_care)
        db.add(
            CatWorldBlindBoxDraw(
                phone=state.phone,
                series_key=series_key,
                cat_id=selected_stock.cat_id,
                energy_cost=int(item["cost"]),
            )
        )
        db.add(selected_stock)
        blind_box_result = {
            "cat": cat_world_cat_payload(selected_cat),
            "profile": cat_world_cat_profile_payload(adopted_profile),
            "seriesKey": series_key,
            "seriesLabel": series["label"],
            "remainingStock": max(int(selected_stock.total_stock or 0) - int(selected_stock.claimed_count or 0), 0),
        }
    elif item["category"] == "handbook":
        if inventory.get(item_id, 0) > 0:
            return {"ok": True, **serialize_cat_world_payload(db, state)}
        if current["energy"]["available"] < int(item["cost"]):
            raise HTTPException(status_code=400, detail="能量值还不够，先去学习赚一点。")
        inventory[item_id] = 1
        state.inventory = encode_cat_world_inventory(inventory)
    elif item["category"] == "color":
        target_decor = str(item.get("targetDecor") or "")
        if not target_decor or inventory.get(target_decor, 0) <= 0:
            target_label = item.get("targetDecorLabel") or "对应家具"
            raise HTTPException(status_code=400, detail=f"请先购买{target_label}，再解锁它的颜色。")
        _, active_user_scene, _ = cat_world_active_scene_context(db, state)
        room_styles = parse_cat_world_room_styles(active_user_scene.room_styles, inventory)
        if inventory.get(item_id, 0) > 0:
            room_styles[target_decor] = str(item.get("tone") or "default")
            save_cat_world_active_scene_styles(state, active_user_scene, room_styles)
            db.add(active_user_scene)
            db.add(state)
            db.commit()
            db.refresh(state)
            return {"ok": True, **serialize_cat_world_payload(db, state)}
        if current["energy"]["available"] < int(item["cost"]):
            raise HTTPException(status_code=400, detail="能量值还不够，先去学习赚一点。")
        inventory[item_id] = 1
        room_styles[target_decor] = str(item.get("tone") or "default")
        state.inventory = encode_cat_world_inventory(inventory)
        save_cat_world_active_scene_styles(state, active_user_scene, room_styles)
        db.add(active_user_scene)
    elif item["category"] in {"toy", "decor"}:
        if inventory.get(item_id, 0) > 0:
            return {"ok": True, **serialize_cat_world_payload(db, state)}
        if current["energy"]["available"] < int(item["cost"]):
            raise HTTPException(status_code=400, detail="能量值还不够，先去学习赚一点。")
        inventory[item_id] = 1
        state.inventory = encode_cat_world_inventory(inventory)
    else:
        if current["energy"]["available"] < int(item["cost"]):
            raise HTTPException(status_code=400, detail="能量值还不够，先去学习赚一点。")
        inventory[item_id] = inventory.get(item_id, 0) + 1
        state.inventory = encode_cat_world_inventory(inventory)
    state.energy_spent = max(int(state.energy_spent or 0), 0) + int(item["cost"])
    db.add(state)
    db.commit()
    db.refresh(state)
    response = {"ok": True, **serialize_cat_world_payload(db, state)}
    if adopted_profile:
        response["adoptedCatProfile"] = cat_world_cat_profile_payload(adopted_profile)
    if blind_box_result:
        response["blindBoxResult"] = blind_box_result
    return response


@app.post("/api/vue/cat-world/play")
async def vue_cat_world_play_api(request: Request, db: Session = Depends(get_db)):
    phone = require_cat_world_phone(request)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="互动数据不是有效 JSON。") from exc
    item_id = str((payload or {}).get("itemId") or "").strip()
    item = CAT_WORLD_SHOP_BY_ID.get(item_id)
    if not item or item["category"] not in {"toy", "food"}:
        raise HTTPException(status_code=400, detail="请选择已经拥有的食物或玩具。")
    state = get_or_create_cat_world_state(db, phone)
    if not parse_cat_world_cats(state.cats):
        raise HTTPException(status_code=400, detail="活动室里没有猫咪，请先去商店重新领养。")
    inventory = parse_cat_world_inventory(state.inventory)
    damaged_items = parse_cat_world_damaged_items(state.damaged_items)
    if item_id in damaged_items:
        repair_cost = damaged_items[item_id].get("repairCost") or 0
        raise HTTPException(status_code=400, detail=f"这个道具被弄坏了，先花 {repair_cost} 能量维修。")
    if inventory.get(item_id, 0) <= 0:
        raise HTTPException(status_code=400, detail="还没有这个道具，先用能量值买一个。")
    if item["category"] == "food":
        inventory[item_id] = max(inventory.get(item_id, 0) - 1, 0)
        if inventory[item_id] <= 0:
            inventory.pop(item_id, None)
        state.inventory = encode_cat_world_inventory(inventory)
        state.active_food_item = item_id
        state.active_food_at = datetime.utcnow()
    else:
        state.last_play_item = item_id
        state.last_played_at = datetime.utcnow()
    usable_inventory = cat_world_usable_inventory(inventory, damaged_items)
    room_layout = cat_world_active_scene_layout(db, state, usable_inventory)
    effect = cat_world_apply_daily_effect(
        db,
        state,
        item,
        usable_inventory,
        room_layout,
        "food" if item["category"] == "food" else "toy",
    )
    db.add(state)
    db.commit()
    db.refresh(state)
    return {"ok": True, "effect": effect, **serialize_cat_world_payload(db, state)}


@app.post("/api/vue/cat-world/food-nibble")
async def vue_cat_world_food_nibble_api(request: Request, db: Session = Depends(get_db)):
    phone = require_cat_world_phone(request)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="猫咪进食数据不是有效 JSON。") from exc
    payload = payload if isinstance(payload, dict) else {}
    cat_id = str(payload.get("catId") or "").strip()
    state = get_or_create_cat_world_state(db, phone)
    profile = cat_world_profile_for_reference(db, state, cat_id)
    if not profile:
        raise HTTPException(status_code=400, detail="还没有解锁这只猫。")
    cat_id = profile.profile_id
    cat = cat_world_cat_profile_payload(profile)
    breed_id = profile.breed_id
    inventory = parse_cat_world_inventory(state.inventory)
    damaged_items = parse_cat_world_damaged_items(state.damaged_items)
    usable_inventory = cat_world_usable_inventory(inventory, damaged_items)
    room_layout = cat_world_active_scene_layout(db, state, usable_inventory)
    effect = cat_world_apply_active_food_nibble(db, state, cat_id, usable_inventory, room_layout)
    return {"ok": True, "effect": effect, **serialize_cat_world_payload(db, state)}


@app.post("/api/vue/cat-world/litter/clean")
async def vue_cat_world_clean_litter_api(request: Request, db: Session = Depends(get_db)):
    phone = require_cat_world_phone(request)
    state = get_or_create_cat_world_state(db, phone)
    inventory = parse_cat_world_inventory(state.inventory)
    owned_cats = parse_cat_world_cats(state.cats)
    hygiene = cat_world_refresh_litter(state, inventory, owned_cats)
    if hygiene.get("changed"):
        db.add(state)
        db.commit()
        db.refresh(state)
        inventory = parse_cat_world_inventory(state.inventory)
    if int(state.litter_count or 0) <= 0:
        raise HTTPException(status_code=400, detail="活动室里现在没有需要清理的猫屎。")
    scoop_count = max(int(inventory.get(CAT_WORLD_LITTER_SCOOP_ITEM_ID, 0) or 0), 0)
    if scoop_count <= 0:
        raise HTTPException(status_code=400, detail="需要先在消耗品商店购买一次性铲屎铲。")
    if scoop_count == 1:
        inventory.pop(CAT_WORLD_LITTER_SCOOP_ITEM_ID, None)
    else:
        inventory[CAT_WORLD_LITTER_SCOOP_ITEM_ID] = scoop_count - 1
    state.inventory = encode_cat_world_inventory(inventory)
    state.litter_count = max(int(state.litter_count or 0) - 1, 0)
    if state.litter_count <= 0:
        state.litter_updated_at = datetime.utcnow()
        state.litter_started_at = None
    db.add(state)
    db.commit()
    db.refresh(state)
    return {
        "ok": True,
        "effect": {
            "cleaned": True,
            "remainingLitter": int(state.litter_count or 0),
            "scoopRemaining": max(int(inventory.get(CAT_WORLD_LITTER_SCOOP_ITEM_ID, 0) or 0), 0),
            "message": "猫屎清理好了，房间空气清爽了一点。",
        },
        **serialize_cat_world_payload(db, state),
    }


@app.post("/api/vue/cat-world/consumable/use")
async def vue_cat_world_use_consumable_api(request: Request, db: Session = Depends(get_db)):
    phone = require_cat_world_phone(request)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="消耗品数据不是有效 JSON。") from exc
    payload = payload if isinstance(payload, dict) else {}
    item_id = str(payload.get("itemId") or "").strip()
    item = CAT_WORLD_SHOP_BY_ID.get(item_id)
    if not item or item.get("category") != "consumable":
        raise HTTPException(status_code=400, detail="请选择已经拥有的消耗品。")
    use_type = str(item.get("useType") or "")
    if use_type == "litter-clean":
        raise HTTPException(status_code=400, detail="请直接点击活动室里的猫屎来使用铲子。")
    if use_type == "repair-tool":
        raise HTTPException(status_code=400, detail="维修锤会在维修损坏道具时自动消耗，请直接点击损坏的道具。")
    state = get_or_create_cat_world_state(db, phone)
    inventory = parse_cat_world_inventory(state.inventory)
    if inventory.get(item_id, 0) <= 0:
        raise HTTPException(status_code=400, detail="这个消耗品已经用完了，请先购买。")
    if use_type == "litter-prevent" and int(state.litter_ready_count or 0) > 0:
        raise HTTPException(status_code=400, detail="活动室里已经放好一份豆腐猫砂，等猫咪使用后再放新的。")
    inventory[item_id] = max(inventory.get(item_id, 0) - 1, 0)
    if inventory[item_id] <= 0:
        inventory.pop(item_id, None)
    state.inventory = encode_cat_world_inventory(inventory)
    usable_inventory = cat_world_usable_inventory(inventory, parse_cat_world_damaged_items(state.damaged_items))
    room_layout = cat_world_active_scene_layout(db, state, usable_inventory)
    owned_cats = parse_cat_world_cats(state.cats)
    if not owned_cats:
        raise HTTPException(status_code=400, detail="活动室里没有猫咪，请先去商店重新领养。")
    now = datetime.utcnow()
    active_profiles = cat_world_active_cat_profiles(db, state.phone)
    target_profile = cat_world_profile_for_reference(
        db,
        state,
        str(payload.get("catId") or state.selected_cat_profile or state.selected_cat),
        active_profiles,
    )
    if not target_profile:
        raise HTTPException(status_code=400, detail="没有找到要照顾的猫咪个体。")
    target_cat_id = target_profile.profile_id
    if use_type == "litter-prevent":
        state.litter_ready_count = 1
        if not state.litter_updated_at:
            state.litter_updated_at = now
        db.add(state)
        db.commit()
        db.refresh(state)
        return {
            "ok": True,
            "effect": {
                "itemId": item_id,
                "itemLabel": item.get("label") or item_id,
                "useType": use_type,
                "remaining": max(int(inventory.get(item_id, 0) or 0), 0),
                "catId": target_cat_id,
                "effects": [],
                "message": "豆腐猫砂已经放进活动室，猫咪下次排泄时会自动使用，然后从房间消失。",
            },
            **serialize_cat_world_payload(db, state),
        }
    target_ids = (
        [profile.profile_id for profile in active_profiles]
        if use_type == "room-care"
        else [target_cat_id]
    )
    effects = []
    for cat_id in target_ids:
        cat = cat_world_cat_for_reference(db, state, cat_id, active_profiles)
        if not cat:
            continue
        breed_id = str(cat.get("breedId") or cat.get("id"))
        traits = cat_world_cat_traits(cat)
        favorite_ids = cat_world_active_favorite_decor_ids(breed_id, usable_inventory, room_layout)
        log = get_or_create_cat_world_daily_log(db, state.phone, cat_id, date.today(), now, cat)
        apply_cat_world_hourly_decay(
            log,
            traits,
            usable_inventory,
            len(favorite_ids),
            now,
            int(state.litter_count or 0),
            cat_world_cat_bath_mood_penalty(state, cat_id, now, cat),
            cat,
        )
        mood_gain = max(int(item.get("mood") or 0), 0)
        energy_gain = max(int(item.get("catEnergy") or 0), 0)
        log.mood_score = clamp_cat_world_score(int(log.mood_score or 0) + mood_gain)
        if energy_gain:
            log.energy_score = clamp_cat_world_score(int(log.energy_score or 0) + energy_gain)
        message = (
            f"{cat['label']}洗完澡，炸开的毛重新顺下来了，心情 +{mood_gain}"
            if use_type == "cat-bath"
            else f"{cat['label']}使用了{item.get('label') or item_id}，心情 +{mood_gain}"
        )
        if energy_gain:
            message += f"，体力 +{energy_gain}"
        message += "。"
        append_cat_world_agent_event(
            log,
            cat,
            traits,
            "cat-bath" if use_type == "cat-bath" else "care-item",
            "洗澡护理" if use_type == "cat-bath" else "护理用品",
            message,
            now,
        )
        bond_gain = max(int(item.get("bond") or 0), 0)
        bond = cat_world_apply_cat_bond(state, cat_id, bond_gain, "care-item", item.get("label") or item_id, now) if bond_gain else {}
        db.add(log)
        effects.append({
            "catId": cat_id,
            "catLabel": cat["label"],
            "moodGain": mood_gain,
            "energyGain": energy_gain,
            "bond": bond,
            "message": message,
        })
    if use_type == "room-place":
        state.active_care_item = item_id
        state.active_care_cat_id = target_cat_id
        state.active_care_at = now
    if use_type == "cat-bath":
        cat_care, _ = cat_world_ensure_profile_care_records(state, active_profiles, now)
        care_row = {**cat_care.get(target_cat_id, {})}
        care_row["lastBathAt"] = now.replace(microsecond=0).isoformat() + "Z"
        care_row["bathCount"] = max(int(care_row.get("bathCount") or 0), 0) + 1
        cat_care[target_cat_id] = care_row
        state.cat_care = encode_cat_world_care(cat_care)
    db.add(state)
    db.commit()
    db.refresh(state)
    return {
        "ok": True,
        "effect": {
            "itemId": item_id,
            "itemLabel": item.get("label") or item_id,
            "useType": use_type,
            "remaining": max(int(inventory.get(item_id, 0) or 0), 0),
            "catId": target_cat_id,
            "effects": effects,
            "message": (
                f"{item.get('label') or item_id}已放进活动室，猫咪会慢慢靠近，{int(item.get('durationMinutes') or 20)} 分钟后消失。"
                if use_type == "room-place"
                else "；".join(effect["message"] for effect in effects)
            ),
        },
        **serialize_cat_world_payload(db, state),
    }


@app.post("/api/vue/cat-world/agent-event")
async def vue_cat_world_agent_event_api(request: Request, db: Session = Depends(get_db)):
    phone = require_cat_world_phone(request)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="猫咪事件数据不是有效 JSON。") from exc
    payload = payload if isinstance(payload, dict) else {}
    cat_id = str(payload.get("catId") or "").strip()
    item_id = str(payload.get("itemId") or "").strip()
    event_kind = str(payload.get("kind") or "").strip()
    if event_kind not in {"favorite-toy", "favorite-decor", "rest-spot"}:
        raise HTTPException(status_code=400, detail="不支持这个猫咪事件。")
    state = get_or_create_cat_world_state(db, phone)
    profile = cat_world_profile_for_reference(db, state, cat_id)
    if not profile:
        raise HTTPException(status_code=400, detail="还没有解锁这只猫。")
    cat_id = profile.profile_id
    inventory = parse_cat_world_inventory(state.inventory)
    damaged_items = parse_cat_world_damaged_items(state.damaged_items)
    usable_inventory = cat_world_usable_inventory(inventory, damaged_items)
    room_layout = cat_world_active_scene_layout(db, state, usable_inventory)
    item = CAT_WORLD_SHOP_BY_ID.get(item_id)
    label_hint = str(payload.get("label") or "").strip()
    if event_kind in {"favorite-toy", "favorite-decor"}:
        expected_category = "toy" if event_kind == "favorite-toy" else "decor"
        if not item or item.get("category") != expected_category:
            raise HTTPException(status_code=400, detail="这个道具不能记录为猫咪偏好事件。")
        if inventory.get(item_id, 0) <= 0 or item_id in damaged_items:
            return {"ok": True, "recorded": False}
        if event_kind == "favorite-toy":
            favorite_match = cat_world_item_favorite_cat_id(item_id) == breed_id
        else:
            favorite_match = item_id in cat_world_cat_favorite_decor_ids(breed_id) and item_id in room_layout
        if not favorite_match:
            return {"ok": True, "recorded": False}
    else:
        if item_id and item_id != "room-rest":
            if not item or item.get("category") not in {"decor", "toy", "food"}:
                raise HTTPException(status_code=400, detail="这个位置不能记录为猫咪休息事件。")
            if item_id in damaged_items:
                return {"ok": True, "recorded": False}
            if item.get("category") != "food" and inventory.get(item_id, 0) <= 0:
                return {"ok": True, "recorded": False}
            if item.get("category") == "decor" and item_id not in room_layout:
                return {"ok": True, "recorded": False}
        favorite_match = bool(
            item_id
            and (
                cat_world_item_favorite_cat_id(item_id) == breed_id
                or item_id in cat_world_cat_favorite_decor_ids(breed_id)
            )
        )
    traits = cat_world_cat_traits(cat)
    now = datetime.utcnow()
    log = get_or_create_cat_world_daily_log(db, state.phone, cat_id, date.today(), now, cat)
    favorite_active_ids = cat_world_active_favorite_decor_ids(breed_id, usable_inventory, room_layout)
    apply_cat_world_hourly_decay(
        log,
        traits,
        usable_inventory,
        len(favorite_active_ids),
        now,
        int(state.litter_count or 0),
        cat_world_cat_bath_mood_penalty(state, cat_id, now, cat),
        cat,
    )
    agent_state, _ = ensure_cat_world_agent_state(log, cat, traits)
    ambient_event_at = agent_state.get("ambientEventAt") if isinstance(agent_state.get("ambientEventAt"), dict) else {}
    token = f"{event_kind}:{item_id}"
    last_seen_raw = str(ambient_event_at.get(token) or "")
    try:
        last_seen = datetime.fromisoformat(last_seen_raw.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        last_seen = None
    if last_seen and now - last_seen < timedelta(minutes=30):
        return {"ok": True, "recorded": False}
    try:
        ambient_effect_count = max(int(agent_state.get("ambientEffectCount") or 0), 0)
    except (TypeError, ValueError):
        ambient_effect_count = 0
    if ambient_effect_count >= 8:
        return {"ok": True, "recorded": False}
    label = (item or {}).get("label") or label_hint or "休息点"
    mood_key = str(agent_state.get("dailyMoodKey") or "")
    adjusted_mood_score = clamp_cat_world_score(int(log.mood_score or 0) + int(agent_state.get("moodOffset") or 0))
    adjusted_energy_score = clamp_cat_world_score(int(log.energy_score or 0) + int(agent_state.get("energyOffset") or 0))
    behavior = cat_world_current_behavior(agent_state, traits, adjusted_mood_score, adjusted_energy_score, now)
    if event_kind == "favorite-toy":
        can_play = adjusted_energy_score >= int(traits.get("restThreshold") or 34) and not behavior.get("sleeping")
        if can_play:
            mood_gain = round(3 * float(traits["playMoodGain"]))
            if adjusted_mood_score < 52:
                mood_gain += 1
            if mood_key in {"bright", "curious"}:
                mood_gain += 1
            mood_gain = max(2, min(mood_gain, 7))
            energy_gain = -max(1, round(2 * float(traits["energyDrain"])))
            event_label = "自主玩耍"
            message = f"{cat['label']}自己跑去玩最喜欢的{label}，心情 +{mood_gain}，体力 {energy_gain}。"
        else:
            mood_gain = 1
            energy_gain = 0
            event_label = "轻轻看玩具"
            message = f"{cat['label']}体力不太够，只是在最喜欢的{label}旁边看了一会儿，心情 +{mood_gain}。"
    elif event_kind == "favorite-decor":
        mood_gain = 2
        if adjusted_mood_score < 52:
            mood_gain += 1
        if mood_key in {"quiet", "lazy"}:
            mood_gain += 1
        mood_gain = min(mood_gain, 5)
        energy_gain = 0
        event_label = "偏好停留"
        message = f"{cat['label']}自己跑到喜欢的{label}旁边待了一会儿，心情 +{mood_gain}。"
    else:
        rest_threshold = int(traits.get("restThreshold") or 34)
        needs_rest = adjusted_energy_score < rest_threshold + 20 or adjusted_mood_score < 45
        if behavior.get("sleeping") or not needs_rest:
            return {"ok": True, "recorded": False}
        urgency = max(rest_threshold + 20 - adjusted_energy_score, 0)
        temperament = str(traits.get("temperament") or agent_state.get("temperament") or "balanced")
        energy_gain = max(2, min(6, 2 + round(urgency / 8)))
        if temperament in {"calm", "gentle"}:
            energy_gain += 1
        energy_gain = min(energy_gain, 7)
        mood_gain = 1 if adjusted_mood_score < 52 or favorite_match else 0
        if mood_key in {"quiet", "lazy"}:
            mood_gain += 1
        mood_gain = min(mood_gain, 4)
        event_label = "自主休息"
        favorite_text = "喜欢的" if favorite_match else ""
        message = f"{cat['label']}自己跑到{favorite_text}{label}附近休息，体力 +{energy_gain}"
        if mood_gain:
            message += f"，心情 +{mood_gain}"
        message += "。"
    log.mood_score = clamp_cat_world_score(int(log.mood_score or 0) + mood_gain)
    if energy_gain:
        log.energy_score = clamp_cat_world_score(int(log.energy_score or 0) + energy_gain)
    bond_gain = 1 + (1 if favorite_match and event_kind in {"favorite-toy", "favorite-decor", "rest-spot"} else 0)
    bond = cat_world_apply_cat_bond(state, cat_id, bond_gain, event_kind, label, now)
    agent_state = append_cat_world_agent_event(
        log,
        cat,
        traits,
        event_kind,
        event_label,
        message,
        now,
    )
    ambient_event_at[token] = now.replace(microsecond=0).isoformat() + "Z"
    agent_state["ambientEventAt"] = ambient_event_at
    agent_state["ambientEffectCount"] = ambient_effect_count + 1
    log.agent_state = encode_cat_world_agent_state(agent_state)
    db.add(log)
    db.add(state)
    db.commit()
    db.refresh(state)
    effect = {
        "catId": cat["id"],
        "catLabel": cat["label"],
        "itemId": item_id,
        "itemLabel": label,
        "kind": event_kind,
        "moodGain": mood_gain,
        "energyGain": energy_gain,
        "bond": bond,
        "ambientEffectCount": ambient_effect_count + 1,
    }
    return {
        "ok": True,
        "recorded": True,
        "effect": effect,
        "event": {"kind": event_kind, "label": event_label, "message": message},
        **serialize_cat_world_payload(db, state),
    }


@app.post("/api/vue/cat-world/repair")
async def vue_cat_world_repair_api(request: Request, db: Session = Depends(get_db)):
    phone = require_cat_world_phone(request)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="维修数据不是有效 JSON。") from exc
    item_id = str((payload or {}).get("itemId") or "").strip()
    state = get_or_create_cat_world_state(db, phone)
    inventory = parse_cat_world_inventory(state.inventory)
    damaged_items = parse_cat_world_damaged_items(state.damaged_items)
    damaged = damaged_items.get(item_id)
    if not damaged:
        raise HTTPException(status_code=400, detail="这个道具不需要维修。")
    if inventory.get(item_id, 0) <= 0:
        damaged_items.pop(item_id, None)
        state.damaged_items = encode_cat_world_damaged_items(damaged_items)
        db.add(state)
        db.commit()
        return {"ok": True, **serialize_cat_world_payload(db, state)}
    hammer_count = max(int(inventory.get(CAT_WORLD_REPAIR_HAMMER_ITEM_ID, 0) or 0), 0)
    if hammer_count <= 0:
        raise HTTPException(status_code=400, detail="维修需要 1 把一次性维修锤，请先去消耗品商店购买。")
    growth = learning_growth_summary(db)
    available_energy = max(
        cat_world_earned_energy(db, state.phone, growth) - max(int(state.energy_spent or 0), 0),
        0,
    )
    repair_cost = max(int(damaged.get("repairCost") or 0), 1)
    if available_energy < repair_cost:
        raise HTTPException(status_code=400, detail="能量值还不够，先去学习赚一点再维修。")
    inventory[CAT_WORLD_REPAIR_HAMMER_ITEM_ID] = hammer_count - 1
    if inventory[CAT_WORLD_REPAIR_HAMMER_ITEM_ID] <= 0:
        inventory.pop(CAT_WORLD_REPAIR_HAMMER_ITEM_ID, None)
    state.inventory = encode_cat_world_inventory(inventory)
    damaged_items.pop(item_id, None)
    state.damaged_items = encode_cat_world_damaged_items(damaged_items)
    state.energy_spent = max(int(state.energy_spent or 0), 0) + repair_cost
    repair_cat_id = str(damaged.get("catId") or state.selected_cat or CAT_WORLD_DEFAULT_CAT_ID)
    repair_label = str(damaged.get("label") or CAT_WORLD_SHOP_BY_ID.get(item_id, {}).get("label") or item_id)
    repair_cat = cat_world_cat_for_reference(db, state, repair_cat_id) or cat_world_cat_payload(
        CAT_WORLD_CAT_BY_ID[CAT_WORLD_DEFAULT_CAT_ID]
    )
    repair_cat_id = str(repair_cat.get("profileId") or repair_cat.get("id"))
    repair_traits = cat_world_cat_traits(repair_cat)
    now = datetime.utcnow()
    repair_log = get_or_create_cat_world_daily_log(db, state.phone, repair_cat_id, date.today(), now, repair_cat)
    repair_agent_state = append_cat_world_agent_event(
        repair_log,
        repair_cat,
        repair_traits,
        "repair",
        "维修完成",
        f"{repair_label}已经维修好，消耗 1 把维修锤和 {repair_cost} 能量。",
        now,
    )
    repair_agent_state["mischiefRepairedItemId"] = item_id
    repair_agent_state["mischiefRepairedLabel"] = repair_label
    repair_agent_state["mischiefRepairCost"] = repair_cost
    repair_agent_state["mischiefRepairedAt"] = now.replace(microsecond=0).isoformat() + "Z"
    if repair_agent_state.get("mischiefItemId") == item_id or repair_log.damaged_item_id == item_id:
        repair_agent_state.pop("mischiefItemId", None)
        repair_agent_state.pop("mischiefLabel", None)
    repair_log.agent_state = encode_cat_world_agent_state(repair_agent_state)
    if repair_log.damaged_item_id == item_id:
        repair_log.damaged_item_id = None
    bond = cat_world_apply_cat_bond(state, repair_cat_id, 4, "repair", repair_label, now)
    db.add(repair_log)
    db.add(state)
    db.commit()
    db.refresh(state)
    return {
        "ok": True,
        "repair": {
            "itemId": item_id,
            "label": repair_label,
            "cost": repair_cost,
            "hammerItemId": CAT_WORLD_REPAIR_HAMMER_ITEM_ID,
            "hammerRemaining": max(int(inventory.get(CAT_WORLD_REPAIR_HAMMER_ITEM_ID, 0) or 0), 0),
            "catId": repair_cat["id"],
            "catLabel": repair_cat["label"],
            "bond": bond,
        },
        **serialize_cat_world_payload(db, state),
    }


@app.post("/api/vue/cat-world/decor-style")
async def vue_cat_world_decor_style_api(request: Request, db: Session = Depends(get_db)):
    phone = require_cat_world_phone(request)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="装修数据不是有效 JSON。") from exc
    decor_id = str((payload or {}).get("decorId") or "").strip()
    if decor_id not in CAT_WORLD_DECOR_LABELS:
        raise HTTPException(status_code=404, detail="没有找到这个装修。")
    state = get_or_create_cat_world_state(db, phone)
    requested_scene_key = str((payload or {}).get("sceneId") or state.current_scene_key).strip()
    if requested_scene_key != state.current_scene_key:
        raise HTTPException(status_code=409, detail="场景已经切换，请重新选择装修。")
    inventory = parse_cat_world_inventory(state.inventory)
    if inventory.get(decor_id, 0) <= 0:
        raise HTTPException(status_code=400, detail="请先购买这个装修。")
    requested_tone = str((payload or {}).get("tone") or "").strip()
    options = cat_world_owned_style_options(inventory, decor_id)
    if len(options) <= 1:
        raise HTTPException(status_code=400, detail="还没有解锁这个装修的颜色，先去配色商店购买。")
    _, active_user_scene, _ = cat_world_active_scene_context(db, state)
    room_styles = parse_cat_world_room_styles(active_user_scene.room_styles, inventory)
    current_tone = room_styles.get(decor_id, "default")
    if requested_tone:
        next_option = next((option for option in options if option["tone"] == requested_tone), None)
        if not next_option:
            raise HTTPException(status_code=400, detail="还没有解锁这个颜色。")
    else:
        current_index = next((index for index, option in enumerate(options) if option["tone"] == current_tone), 0)
        next_option = options[(current_index + 1) % len(options)]
    room_styles[decor_id] = next_option["tone"]
    save_cat_world_active_scene_styles(state, active_user_scene, room_styles)
    db.add(active_user_scene)
    db.add(state)
    db.commit()
    db.refresh(state)
    return {"ok": True, "style": next_option, **serialize_cat_world_payload(db, state)}


@app.post("/api/vue/cat-world/room-layout")
async def vue_cat_world_room_layout_api(request: Request, db: Session = Depends(get_db)):
    phone = require_cat_world_phone(request)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="房间布局数据不是有效 JSON。") from exc
    incoming = payload.get("layout") if isinstance(payload, dict) else None
    if not isinstance(incoming, dict):
        incoming = payload.get("positions") if isinstance(payload, dict) else None
    if not isinstance(incoming, dict):
        raise HTTPException(status_code=400, detail="请提交可保存的房间布局。")
    state = get_or_create_cat_world_state(db, phone)
    requested_scene_key = str((payload or {}).get("sceneId") or state.current_scene_key).strip()
    if requested_scene_key != state.current_scene_key:
        raise HTTPException(status_code=409, detail="场景已经切换，请重新打开编辑模式后保存。")
    inventory = parse_cat_world_inventory(state.inventory)
    _, active_user_scene, active_scene_config = cat_world_active_scene_context(db, state)
    current_layout = parse_cat_world_room_layout(
        active_user_scene.layout,
        inventory,
        active_scene_config.get("defaultLayout"),
        active_scene_config.get("itemRules"),
    )
    owned_layout_item_ids = {
        item_id
        for item_id, count in inventory.items()
        if count > 0 and CAT_WORLD_SHOP_BY_ID.get(item_id, {}).get("category") in {"decor", "toy"}
        and cat_world_layout_item_allowed(item_id, active_scene_config.get("itemRules"))
    }
    saved_layout = {**current_layout}
    for item_id, position in incoming.items():
        item_key = str(item_id)
        if item_key not in owned_layout_item_ids:
            continue
        normalized = normalize_cat_world_room_position(position)
        if normalized:
            saved_layout[item_key] = normalized
    save_cat_world_active_scene_layout(state, active_user_scene, saved_layout)
    damaged_items = parse_cat_world_damaged_items(state.damaged_items)
    usable_inventory = cat_world_usable_inventory(inventory, damaged_items)
    usable_layout = parse_cat_world_room_layout(
        active_user_scene.layout,
        usable_inventory,
        active_scene_config.get("defaultLayout"),
        active_scene_config.get("itemRules"),
    )
    rewards = cat_world_apply_favorite_decor_rewards(
        db,
        state,
        usable_inventory,
        usable_layout,
        parse_cat_world_cats(state.cats),
    )
    db.add(active_user_scene)
    db.add(state)
    db.commit()
    db.refresh(state)
    return {"ok": True, "layoutRewards": rewards, **serialize_cat_world_payload(db, state)}


@app.post("/api/vue/cat-world/scene/select")
async def vue_cat_world_select_scene_api(request: Request, db: Session = Depends(get_db)):
    phone = require_cat_world_phone(request)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="场景数据不是有效 JSON。") from exc
    scene_key = str((payload or {}).get("sceneId") or "").strip()
    scene = cat_world_scene_row(db, scene_key)
    if not scene or scene.scene_key != scene_key:
        raise HTTPException(status_code=404, detail="没有找到这个场景。")
    if not scene.is_enabled:
        raise HTTPException(status_code=403, detail="这个场景还在准备中。")
    state = get_or_create_cat_world_state(db, phone)
    user_scene, _ = get_or_create_cat_world_user_scene(db, state, scene)
    if not user_scene.is_unlocked:
        raise HTTPException(status_code=403, detail="这个场景还没有解锁。")
    state.current_scene_key = scene.scene_key
    user_scene.last_visited_at = datetime.utcnow()
    db.add(user_scene)
    db.add(state)
    db.commit()
    db.refresh(state)
    return {"ok": True, **serialize_cat_world_payload(db, state)}


@app.post("/api/vue/cat-world/select-cat")
async def vue_cat_world_select_cat_api(request: Request, db: Session = Depends(get_db)):
    phone = require_cat_world_phone(request)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="猫咪数据不是有效 JSON。") from exc
    requested_cat_id = str((payload or {}).get("catId") or "").strip()
    profile_id = str((payload or {}).get("profileId") or "").strip()
    state = get_or_create_cat_world_state(db, phone)
    if profile_id:
        profile = db.scalar(
            select(CatWorldCatProfile).where(
                CatWorldCatProfile.phone == state.phone,
                CatWorldCatProfile.profile_id == profile_id,
                CatWorldCatProfile.is_active.is_(True),
            )
        )
        if not profile:
            raise HTTPException(status_code=400, detail="没有找到这只猫咪个体。")
        if requested_cat_id and requested_cat_id not in {profile.profile_id, profile.breed_id}:
            raise HTTPException(status_code=400, detail="猫咪个体与品种不匹配。")
    else:
        profile = cat_world_profile_for_reference(db, state, requested_cat_id)
        if not profile:
            raise HTTPException(status_code=400, detail="还没有解锁这只猫。")
    state.selected_cat_profile = profile.profile_id
    state.selected_cat = profile.breed_id
    db.add(state)
    db.commit()
    db.refresh(state)
    return {"ok": True, **serialize_cat_world_payload(db, state)}


@app.post("/api/vue/cat-world/scene/purchase")
async def vue_cat_world_purchase_scene_api(request: Request, db: Session = Depends(get_db)):
    phone = require_cat_world_phone(request)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="场景购买数据不是有效 JSON。") from exc
    scene_key = str((payload or {}).get("sceneId") or "").strip()
    scene = cat_world_scene_row(db, scene_key)
    if not scene or scene.scene_key != scene_key:
        raise HTTPException(status_code=404, detail="没有找到这个场景。")
    config = cat_world_scene_config(scene)
    if not scene.is_enabled or not config.get("purchasable"):
        raise HTTPException(status_code=403, detail="这个场景暂时不能购买。")
    state = get_or_create_cat_world_state(db, phone)
    current = serialize_cat_world_payload(db, state)
    state = db.scalar(
        select(CatWorldState).where(CatWorldState.id == state.id).with_for_update()
    ) or state
    user_scene, _ = get_or_create_cat_world_user_scene(db, state, scene)
    if user_scene.is_unlocked:
        state.current_scene_key = scene.scene_key
        user_scene.last_visited_at = datetime.utcnow()
        db.add(user_scene)
        db.add(state)
        db.commit()
        db.refresh(state)
        return {"ok": True, "alreadyOwned": True, **serialize_cat_world_payload(db, state)}
    cost = max(int(config.get("purchaseCost") or 0), 0)
    available_energy = max(int(current["energy"]["earned"]) - max(int(state.energy_spent or 0), 0), 0)
    if available_energy < cost:
        raise HTTPException(status_code=400, detail=f"购买{scene.label}需要 {cost} 能量，当前能量还不够。")
    state.energy_spent = max(int(state.energy_spent or 0), 0) + cost
    state.current_scene_key = scene.scene_key
    user_scene.is_unlocked = True
    user_scene.unlocked_at = datetime.utcnow()
    user_scene.last_visited_at = datetime.utcnow()
    db.add(user_scene)
    db.add(state)
    db.commit()
    db.refresh(state)
    return {
        "ok": True,
        "scenePurchase": {"sceneId": scene.scene_key, "label": scene.label, "cost": cost},
        **serialize_cat_world_payload(db, state),
    }


@app.post("/api/vue/cat-world/pet")
async def vue_cat_world_pet_api(request: Request, db: Session = Depends(get_db)):
    phone = require_cat_world_phone(request)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="猫咪互动数据不是有效 JSON。") from exc
    cat_id = str((payload or {}).get("catId") or "").strip()
    state = get_or_create_cat_world_state(db, phone)
    db.refresh(state, with_for_update=True)
    profile = cat_world_profile_for_reference(db, state, cat_id)
    if not profile:
        raise HTTPException(status_code=400, detail="还没有解锁这只猫。")
    cat_id = profile.profile_id
    inventory = parse_cat_world_inventory(state.inventory)
    damaged_items = parse_cat_world_damaged_items(state.damaged_items)
    usable_inventory = cat_world_usable_inventory(inventory, damaged_items)
    room_layout = cat_world_active_scene_layout(db, state, usable_inventory)
    effect = cat_world_apply_pet_effect(db, state, cat_id, usable_inventory, room_layout)
    db.add(state)
    db.commit()
    db.refresh(state)
    return {"ok": True, "effect": effect, **serialize_cat_world_payload(db, state)}


@app.get("/api/vue/admin")
def vue_admin_api(request: Request, db: Session = Depends(get_db)):
    current = require_admin_panel_access(request, db)
    users = db.scalars(select(AdminUserSetting).order_by(AdminUserSetting.role.asc(), AdminUserSetting.updated_at.desc())).all()
    return {
        "currentUser": serialize_admin_user(current),
        "users": [serialize_admin_user(user) for user in users],
        "roleOptions": ADMIN_ROLE_OPTIONS,
        "permissionOptions": ADMIN_PERMISSION_OPTIONS,
        "imageAiOptions": [
            {
                **item,
                "value": admin_image_ai_value(item["provider"], item["model"]),
            }
            for item in ADMIN_IMAGE_AI_OPTIONS
        ],
        "audioAiOptions": ADMIN_AUDIO_AI_OPTIONS,
        "voiceOptions": [
            {"key": "female", "label": "女声"},
            {"key": "male", "label": "男声"},
        ],
        "catWorldPricing": admin_cat_world_pricing_payload(db),
        "catWorldPlayTimeRewards": cat_world_play_time_reward_source(db, current.phone),
    }


@app.post("/api/vue/admin/users")
async def vue_admin_save_user_api(request: Request, db: Session = Depends(get_db)):
    require_admin_panel_access(request, db)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="用户数据不是有效 JSON。") from exc

    phone = normalize_login_phone(payload.get("phone"))
    if not phone:
        raise HTTPException(status_code=400, detail="请输入正确的 11 位手机号。")
    role = str(payload.get("role") or "viewer").strip()
    if role not in {item["key"] for item in ADMIN_ROLE_OPTIONS}:
        role = "viewer"
    username = str(payload.get("username") or "").strip() or admin_user_display_name(phone, role)
    image_provider, image_model = parse_admin_image_ai_value(payload.get("imageAiValue"))
    audio_provider = normalize_admin_audio_provider(payload.get("audioAiProvider"))
    voice_gender = normalize_admin_voice_gender(payload.get("audioVoiceGender"))

    user = db.scalar(select(AdminUserSetting).where(AdminUserSetting.phone == phone))
    login_password = normalize_login_password(payload.get("loginPassword"))
    if not user:
        if len(login_password) < LOGIN_PASSWORD_MIN_LENGTH:
            raise HTTPException(status_code=400, detail="新增用户需要设置至少 6 位登录密码。")
        user = AdminUserSetting(phone=phone)
        db.add(user)
    elif not user.login_password_hash and len(login_password) < LOGIN_PASSWORD_MIN_LENGTH:
        raise HTTPException(status_code=400, detail="这个用户还没有登录密码，请先设置至少 6 位密码。")
    if login_password:
        if len(login_password) < LOGIN_PASSWORD_MIN_LENGTH:
            raise HTTPException(status_code=400, detail="登录密码至少 6 位。")
        user.login_password_hash = hash_login_password(login_password)
    user.username = username[:120]
    user.role = role
    user.permissions = encode_admin_permissions(payload.get("permissions"), role)
    user.image_ai_provider = image_provider
    user.image_ai_model = image_model
    user.audio_ai_provider = audio_provider
    user.audio_voice_gender = voice_gender
    user.is_active = bool(payload.get("isActive", True))
    db.commit()
    db.refresh(user)
    return {
        "ok": True,
        "user": serialize_admin_user(user),
        "users": [serialize_admin_user(item) for item in db.scalars(select(AdminUserSetting).order_by(AdminUserSetting.role.asc(), AdminUserSetting.updated_at.desc())).all()],
    }


@app.post("/api/vue/admin/cat-world/pricing")
async def vue_admin_cat_world_pricing_api(request: Request, db: Session = Depends(get_db)):
    require_admin_panel_access(request, db)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="商品价格数据不是有效 JSON。") from exc
    item_id = str((payload or {}).get("itemId") or "").strip()
    if item_id not in CAT_WORLD_SHOP_BY_ID:
        raise HTTPException(status_code=404, detail="没有找到这个猫咪商品。")
    try:
        cost = int((payload or {}).get("cost"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="请输入有效积分价格。") from exc
    if cost < 0 or cost > 99999:
        raise HTTPException(status_code=400, detail="商品价格需要在 0 到 99999 积分之间。")
    setting = db.scalar(select(CatWorldShopSetting).where(CatWorldShopSetting.item_id == item_id))
    if not setting:
        setting = CatWorldShopSetting(item_id=item_id)
        db.add(setting)
    setting.cost = cost
    db.commit()
    return {"ok": True, "catWorldPricing": admin_cat_world_pricing_payload(db)}


@app.post("/api/vue/admin/cat-world/scene-pricing")
async def vue_admin_cat_world_scene_pricing_api(request: Request, db: Session = Depends(get_db)):
    require_admin_panel_access(request, db)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="场景价格数据不是有效 JSON。") from exc
    scene_key = str((payload or {}).get("sceneId") or "").strip()
    scene = db.scalar(select(CatWorldScene).where(CatWorldScene.scene_key == scene_key))
    if not scene:
        raise HTTPException(status_code=404, detail="没有找到这个猫咪场景。")
    config = parse_cat_world_scene_json(scene.config, {})
    if not bool(config.get("purchasable")):
        raise HTTPException(status_code=400, detail="默认场景不需要设置解锁价格。")
    try:
        cost = int((payload or {}).get("cost"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="请输入有效的场景能量价格。") from exc
    if cost < 0 or cost > 10000000:
        raise HTTPException(status_code=400, detail="场景价格需要在 0 到 10000000 能量之间。")
    config["purchaseCost"] = cost
    scene.config = json.dumps(config, ensure_ascii=False, sort_keys=True)
    db.add(scene)
    db.commit()
    return {"ok": True, "catWorldPricing": admin_cat_world_pricing_payload(db)}


@app.post("/api/vue/admin/cat-world/settings")
async def vue_admin_cat_world_settings_api(request: Request, db: Session = Depends(get_db)):
    require_admin_panel_access(request, db)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="猫咪世界设置不是有效 JSON。") from exc
    save_cat_world_movement_speed(db, (payload or {}).get("movementSpeed"))
    gender_weights = (payload or {}).get("genderDrawWeights")
    if isinstance(gender_weights, dict):
        save_cat_world_gender_draw_weights(
            db,
            gender_weights.get("male"),
            gender_weights.get("female"),
        )
    db.commit()
    return {"ok": True, "catWorldPricing": admin_cat_world_pricing_payload(db)}


@app.post("/api/vue/admin/cat-world/energy-grant")
async def vue_admin_cat_world_energy_grant_api(request: Request, db: Session = Depends(get_db)):
    current = require_admin_panel_access(request, db)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="运营能量数据不是有效 JSON。") from exc
    reason = re.sub(r"\s+", " ", str((payload or {}).get("reason") or "").strip())[:120]
    if len(reason) < 2:
        raise HTTPException(status_code=400, detail="请填写至少 2 个字的发放理由。")
    try:
        amount = int((payload or {}).get("amount"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="请输入有效的能量值。") from exc
    if amount < 1 or amount > 1000000:
        raise HTTPException(status_code=400, detail="单次运营能量需要在 1 到 1000000 之间。")
    password = normalize_login_password((payload or {}).get("password"))
    if not current.login_password_hash:
        raise HTTPException(status_code=400, detail="请先在用户中心给当前后台账号设置登录密码。")
    if not verify_login_password(password, current.login_password_hash):
        raise HTTPException(status_code=403, detail="后台登录密码不正确。")
    grant = CatWorldEnergyGrant(
        phone=current.phone,
        amount=amount,
        reason=reason,
        granted_by_phone=current.phone,
        created_at=datetime.utcnow(),
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)
    return {
        "ok": True,
        "grant": {
            "id": grant.id,
            "amount": grant.amount,
            "reason": grant.reason,
            "createdAt": grant.created_at.replace(microsecond=0).isoformat() + "Z",
        },
        "energySource": cat_world_operating_energy_source(db, current.phone),
        "catWorldPricing": admin_cat_world_pricing_payload(db),
    }


@app.post("/api/vue/admin/cat-world/play-time-grant")
async def vue_admin_cat_world_play_time_grant_api(request: Request, db: Session = Depends(get_db)):
    current = require_admin_panel_access(request, db)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="陪伴时间奖励不是有效 JSON。") from exc
    reason = re.sub(r"\s+", " ", str((payload or {}).get("reason") or "").strip())[:120]
    if len(reason) < 2:
        raise HTTPException(status_code=400, detail="请填写至少 2 个字的奖励理由。")
    try:
        minutes = int((payload or {}).get("minutes"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="请输入有效的奖励分钟数。") from exc
    if minutes < 1 or minutes > 1440:
        raise HTTPException(status_code=400, detail="单次陪伴时间奖励需要在 1 到 1440 分钟之间。")
    password = normalize_login_password((payload or {}).get("password"))
    if not current.login_password_hash:
        raise HTTPException(status_code=400, detail="请先在用户中心给当前后台账号设置登录密码。")
    if not verify_login_password(password, current.login_password_hash):
        raise HTTPException(status_code=403, detail="后台登录密码不正确。")
    grant = CatWorldPlayTimeGrant(
        phone=current.phone,
        reward_date=date.today(),
        minutes=minutes,
        reason=reason,
        granted_by_phone=current.phone,
        created_at=datetime.utcnow(),
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)
    reward_source = cat_world_play_time_reward_source(db, current.phone)
    state = get_or_create_cat_world_state(db, current.phone)
    return {
        "ok": True,
        "grant": {
            "id": grant.id,
            "minutes": grant.minutes,
            "reason": grant.reason,
            "rewardDate": grant.reward_date.isoformat(),
            "createdAt": grant.created_at.replace(microsecond=0).isoformat() + "Z",
        },
        "playTimeRewards": reward_source,
        "playTime": cat_world_play_time_payload(
            state,
            cat_world_today_spelling_count(db),
            reward_seconds=int(reward_source["seconds"]),
        ),
    }


@app.post("/api/vue/admin/cat-world/reset")
async def vue_admin_cat_world_reset_api(request: Request, db: Session = Depends(get_db)):
    current = require_admin_panel_access(request, db)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="清零数据不是有效 JSON。") from exc
    password = normalize_login_password((payload or {}).get("password"))
    if not current.login_password_hash:
        raise HTTPException(status_code=400, detail="请先在用户中心给当前后台账号设置登录密码。")
    if not verify_login_password(password, current.login_password_hash):
        raise HTTPException(status_code=403, detail="后台登录密码不正确。")
    deleted_scenes = db.execute(delete(CatWorldUserScene).where(CatWorldUserScene.phone == current.phone)).rowcount or 0
    deleted_profiles = db.execute(delete(CatWorldCatProfile).where(CatWorldCatProfile.phone == current.phone)).rowcount or 0
    deleted_grants = db.execute(delete(CatWorldEnergyGrant).where(CatWorldEnergyGrant.phone == current.phone)).rowcount or 0
    deleted_play_time_grants = (
        db.execute(delete(CatWorldPlayTimeGrant).where(CatWorldPlayTimeGrant.phone == current.phone)).rowcount or 0
    )
    deleted_state = db.execute(delete(CatWorldState).where(CatWorldState.phone == current.phone)).rowcount or 0
    deleted_logs = db.execute(delete(CatWorldDailyLog).where(CatWorldDailyLog.phone == current.phone)).rowcount or 0
    db.commit()
    return {
        "ok": True,
        "deleted": {
            "state": deleted_state,
            "scenes": deleted_scenes,
            "dailyLogs": deleted_logs,
            "profiles": deleted_profiles,
            "energyGrants": deleted_grants,
            "playTimeGrants": deleted_play_time_grants,
        },
        "catWorldPricing": admin_cat_world_pricing_payload(db),
    }


@app.get("/api/vue/shell")
def vue_shell_api(request: Request, db: Session = Depends(get_db)):
    current_phone = authenticated_phone_from_request(request)
    admin_user = get_or_create_admin_user(db, current_phone) if current_phone else None
    return serialize_shell_context({
        "app_name": settings.app_name,
        "current_user_phone": authenticated_phone_from_request(request),
        "current_admin_user": admin_user,
        "daily_quote": get_daily_quote(db),
        "sidebar_challenges": sidebar_challenge_progress(db),
        "wrong_word_count": pending_wrong_word_count(db),
        "learning_growth": learning_growth_summary(db),
    })


def essay_word_count(text_value: str | None) -> int:
    text_value = str(text_value or "")
    tokens = re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*|\d+(?:\.\d+)?|[\u4e00-\u9fff]", text_value)
    return len(tokens)


def clean_essay_title(value: str | None) -> str:
    return " ".join(str(value or "").split())[:ESSAY_TITLE_MAX_CHARS]


def clean_essay_body(value: str | None) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()[:ESSAY_BODY_MAX_CHARS]


ESSAY_SCORE_KEYS = ("content", "length", "vocabulary", "grammar", "structure")


def clean_essay_feedback_text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def normalize_essay_score_breakdown(value: Any) -> dict[str, int]:
    source = value if isinstance(value, dict) else {}
    parsed: dict[str, int] = {}
    for key in ESSAY_SCORE_KEYS:
        try:
            parsed[key] = int(round(float(source[key])))
        except (KeyError, TypeError, ValueError):
            continue
    if not parsed:
        return {}
    declared_scale = source.get("_scale") or source.get("scale")
    hundred_point_scale = str(declared_scale or "").strip() == "100"
    legacy_twenty_point_scale = not hundred_point_scale and all(score <= 20 for score in parsed.values())
    return {
        key: min(max(score * 5 if legacy_twenty_point_scale else score, 0), 100)
        for key, score in parsed.items()
    }


def essay_writing_points_from_values(writing_score: Any, raw_breakdown: Any) -> int:
    if isinstance(raw_breakdown, str):
        try:
            raw_breakdown = json.loads(raw_breakdown or "{}")
        except (json.JSONDecodeError, TypeError):
            raw_breakdown = {}
    breakdown = normalize_essay_score_breakdown(raw_breakdown)
    if len(breakdown) == len(ESSAY_SCORE_KEYS):
        return min(max(sum(breakdown.values()), 0), 500)
    return min(max(int(writing_score or 0), 0), 100)


def current_essay_writing_points(essay: EssayEntry) -> int:
    return essay_writing_points_from_values(essay.writing_score, essay.writing_score_breakdown)


def effective_essay_best_writing_metrics(essay: EssayEntry) -> tuple[int, int]:
    stored_points = min(max(int(essay.best_writing_points or 0), 0), 500)
    stored_score = min(max(int(essay.best_writing_score or 0), 0), 100)
    if stored_points > 0:
        return stored_score or round(stored_points / 5), stored_points
    return min(max(int(essay.writing_score or 0), 0), 100), current_essay_writing_points(essay)


def preserve_essay_best_writing_result(essay: EssayEntry) -> None:
    current_points = current_essay_writing_points(essay)
    stored_points = min(max(int(essay.best_writing_points or 0), 0), 500)
    if stored_points <= 0 and current_points > 0:
        essay.best_writing_points = current_points
        essay.best_writing_score = min(max(int(essay.writing_score or 0), 0), 100)


def backfill_essay_best_writing_results(db: Session) -> int:
    essays = db.scalars(
        select(EssayEntry).where(
            EssayEntry.best_writing_points <= 0,
            EssayEntry.writing_score > 0,
        )
    ).all()
    changed = 0
    for essay in essays:
        previous_points = int(essay.best_writing_points or 0)
        preserve_essay_best_writing_result(essay)
        if int(essay.best_writing_points or 0) > previous_points:
            db.add(essay)
            changed += 1
    if changed:
        db.commit()
    return changed


def award_essay_writing_improvement(
    essay: EssayEntry,
    *,
    writing_score: int,
    writing_points: int,
    eligible: bool,
) -> int:
    best_points = min(max(int(essay.best_writing_points or 0), 0), 500)
    writing_points = min(max(int(writing_points or 0), 0), 500)
    if not eligible or writing_points <= best_points:
        return 0
    essay.best_writing_points = writing_points
    essay.best_writing_score = min(max(int(writing_score or 0), 0), 100)
    return writing_points - best_points


def normalize_essay_advice_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    for raw_item in value:
        if isinstance(raw_item, dict):
            raw_word_choices = raw_item.get("wordChoices") or raw_item.get("word_choices") or raw_item.get("vocabulary")
            word_choices: list[dict[str, str]] = []
            if isinstance(raw_word_choices, list):
                for raw_choice in raw_word_choices:
                    if not isinstance(raw_choice, dict):
                        continue
                    original = clean_essay_feedback_text(
                        raw_choice.get("original") or raw_choice.get("from") or raw_choice.get("source"),
                        100,
                    )
                    better = clean_essay_feedback_text(
                        raw_choice.get("better") or raw_choice.get("to") or raw_choice.get("replacement"),
                        160,
                    )
                    reason = clean_essay_feedback_text(
                        raw_choice.get("reason") or raw_choice.get("explanation"),
                        300,
                    )
                    if original and better:
                        word_choices.append({
                            "original": original,
                            "better": better,
                            "reason": reason,
                        })
                    if len(word_choices) >= 3:
                        break
            item = {
                "kind": clean_essay_feedback_text(raw_item.get("kind") or raw_item.get("category"), 30) or "老师建议",
                "title": clean_essay_feedback_text(raw_item.get("title"), 100),
                "observation": clean_essay_feedback_text(
                    raw_item.get("observation") or raw_item.get("issue"),
                    500,
                ),
                "guidance": clean_essay_feedback_text(
                    raw_item.get("guidance") or raw_item.get("suggestion") or raw_item.get("advice"),
                    700,
                ),
                "original": clean_essay_feedback_text(
                    raw_item.get("original") or raw_item.get("originalSentence"),
                    500,
                ),
                "example": clean_essay_feedback_text(
                    raw_item.get("example") or raw_item.get("improved") or raw_item.get("improvedSentence"),
                    700,
                ),
                "wordChoices": word_choices,
            }
            if not item["title"]:
                item["title"] = item["guidance"][:60] or f"老师建议 {len(normalized) + 1}"
            if any((item["observation"], item["guidance"], item["original"], item["example"], item["wordChoices"])):
                normalized.append(item)
        else:
            guidance = clean_essay_feedback_text(raw_item, 700)
            if guidance:
                normalized.append({
                    "kind": "",
                    "title": f"AI老师建议{len(normalized) + 1}",
                    "observation": "",
                    "guidance": guidance,
                    "original": "",
                    "example": "",
                    "wordChoices": [],
                })
        if len(normalized) >= 5:
            break
    return normalized


def serialize_essay(essay: EssayEntry) -> dict[str, Any]:
    try:
        score_breakdown = json.loads(essay.writing_score_breakdown or "{}")
    except (json.JSONDecodeError, TypeError):
        score_breakdown = {}
    if not isinstance(score_breakdown, dict):
        score_breakdown = {}
    score_breakdown = normalize_essay_score_breakdown(score_breakdown)
    try:
        writing_advice = json.loads(essay.writing_advice or "[]")
    except (json.JSONDecodeError, TypeError):
        writing_advice = []
    if not isinstance(writing_advice, list):
        writing_advice = []
    writing_points = essay_writing_points_from_values(essay.writing_score, score_breakdown)
    best_writing_score, best_writing_points = effective_essay_best_writing_metrics(essay)
    return {
        "id": essay.id,
        "title": essay.title,
        "body": essay.body,
        "optimizedBody": essay.optimized_body or "",
        "translationBody": essay.translation_body or "",
        "optimizedTranslationBody": essay.optimized_translation_body or "",
        "coverUrl": essay.cover_url or "",
        "wordCount": int(essay.word_count or 0),
        "optimizedWordCount": int(essay.optimized_word_count or 0),
        "writingScore": min(max(int(essay.writing_score or 0), 0), 100),
        "writingScoreBreakdown": score_breakdown,
        "writingPoints": writing_points,
        "bestWritingScore": best_writing_score,
        "bestWritingPoints": best_writing_points,
        "writingAdvice": normalize_essay_advice_items(writing_advice),
        "aiModel": essay.ai_model or "",
        "translationModel": essay.translation_model or "",
        "coverModel": essay.cover_model or "",
        "createdAt": essay.created_at.isoformat() if essay.created_at else "",
        "updatedAt": essay.updated_at.isoformat() if essay.updated_at else "",
    }


def essays_for_phone(db: Session, phone: str) -> list[EssayEntry]:
    return db.scalars(
        select(EssayEntry)
        .where(EssayEntry.phone == phone)
        .order_by(EssayEntry.created_at.desc(), EssayEntry.id.desc())
    ).all()


def essays_payload(db: Session, request: Request) -> dict[str, Any]:
    user = current_admin_user(request, db)
    essays = essays_for_phone(db, user.phone)
    return {
        "essays": [serialize_essay(essay) for essay in essays],
        "limits": {
            "titleMaxChars": ESSAY_TITLE_MAX_CHARS,
            "bodyMaxChars": ESSAY_BODY_MAX_CHARS,
        },
    }


def get_owned_essay(db: Session, request: Request, essay_id: int) -> EssayEntry:
    user = current_admin_user(request, db)
    essay = db.scalar(select(EssayEntry).where(EssayEntry.id == essay_id, EssayEntry.phone == user.phone))
    if not essay:
        raise HTTPException(status_code=404, detail="没有找到这篇作文。")
    return essay


ESSAY_OPTIMIZATION_SYSTEM_PROMPT = (
    "You are a supportive English writing coach for a student. "
    "Improve grammar, clarity, story flow, vocabulary, and sentence variety while preserving the student's meaning, events, and voice. "
    "Evaluate the original student composition, not the polished rewrite. "
    "Return only one valid JSON object with this exact shape: "
    '{"optimizedBody":"polished English composition","assessment":{"scale":100,"content":0,"length":0,"vocabulary":0,'
    '"grammar":0,"structure":0,"advice":[{"kind":"词汇表达","title":"简短标题","observation":"中文老师观察",'
    '"guidance":"中文具体改法","original":"学生原文中的英文短语或句子","example":"保留原意的英文参考改写",'
    '"wordChoices":[{"original":"原词或短语","better":"更准确的词或短语","reason":"中文说明语气、含义或使用场景"}]}]}}. '
    "Each of the five scores is an integer from 0 to 100. Content measures ideas and development; length measures whether the composition is sufficiently developed; "
    "vocabulary measures variety, difficulty, and appropriate word choice; grammar measures correctness; structure measures organization and flow. "
    "Give 3 to 5 warm, age-appropriate, highly specific teaching suggestions. Every suggestion must explain what the child can improve and how to improve it, "
    "quote a relevant phrase or sentence from the original composition, and provide one correct English example that keeps the child's intended meaning. "
    "At least one suggestion must focus on vocabulary: compare actual words from the composition with more precise or more tactful alternatives, and explain "
    "their meaning, tone, and suitable context in Chinese. Include another suggestion about grammar or sentence expression and another about content or structure. "
    'Set each advice "kind" to exactly one of: "词汇表达", "委婉表达", "语法修正", "句式表达", "内容描写", or "结构组织". '
    "When an expression sounds blunt or overly direct, explicitly teach a gentler alternative and explain why it is more appropriate. "
    "Do not use vague praise, do not invent unrelated story facts, and do not choose difficult words merely to sound advanced. "
    "Do not include markdown or any text outside the JSON object."
)


def essay_optimization_messages(*, title: str, body: str) -> list[dict[str, str]]:
    student_context = f"Title: {title}\n\nStudent composition:\n{body}" if title else f"Student composition:\n{body}"
    return [
        {
            "role": "system",
            "content": ESSAY_OPTIMIZATION_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": student_context,
        },
    ]


def local_essay_assessment(body: str) -> dict[str, Any]:
    words = re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*", body)
    word_count = max(len(words), essay_word_count(body))
    sentences = [part.strip() for part in re.split(r"[.!?]+", body) if part.strip()]
    paragraphs = [part.strip() for part in body.splitlines() if part.strip()]
    unique_ratio = len({word.lower() for word in words}) / max(len(words), 1)
    long_word_ratio = sum(1 for word in words if len(word) >= 7) / max(len(words), 1)
    average_sentence = word_count / max(len(sentences), 1)
    capital_starts = sum(1 for sentence in sentences if sentence[:1].isupper()) / max(len(sentences), 1)
    twenty_point_breakdown = {
        "content": min(20, 8 + min(len(sentences), 6) + min(word_count // 30, 5)),
        "length": min(20, max(4, round(word_count / 6))),
        "vocabulary": min(20, max(5, round(6 + unique_ratio * 8 + long_word_ratio * 20))),
        "grammar": min(
            20,
            max(
                5,
                round(
                    8
                    + capital_starts * 4
                    + (4 if body.rstrip().endswith((".", "!", "?")) else 0)
                    + (3 if 6 <= average_sentence <= 24 else 1)
                ),
            ),
        ),
        "structure": min(
            20,
            max(5, 7 + min(len(sentences), 5) * 2 + min(max(len(paragraphs) - 1, 0), 3)),
        ),
    }
    breakdown = {key: score * 5 for key, score in twenty_point_breakdown.items()}
    sentence_samples = [
        part.strip()
        for part in re.findall(r"[^.!?]+[.!?]?", body)
        if part.strip()
    ]
    sample_sentence = (sentence_samples[0] if sentence_samples else body.strip())[:500]
    vocabulary_options = (
        ("mean", "harsh / difficult", "mean 常形容人刻薄；形容生活或处境时，harsh 或 difficult 更自然。"),
        ("good", "memorable / effective", "good 含义较宽，可以根据“令人难忘”或“有效”选择更准确的词。"),
        ("bad", "unpleasant / disappointing", "bad 比较笼统，换词后能说清楚究竟是令人不快还是令人失望。"),
        ("nice", "kind / welcoming / pleasant", "nice 很常用；写人、环境和感受时可以分别选择更具体的词。"),
        ("said", "explained / replied / whispered", "said 只表示“说”，更具体的动词还能告诉读者说话方式。"),
        ("went", "walked / hurried / traveled", "went 没有动作画面，可以按速度和方式选择更具体的动词。"),
        ("got", "received / became / reached", "got 的含义很多，明确是“获得、变得”还是“到达”会更准确。"),
        ("thing", "object / idea / event", "thing 过于宽泛，直接写出事物、想法或事件更清楚。"),
        ("big", "enormous / spacious / important", "big 可分别表示体积、空间或重要性，选词时要对应具体含义。"),
        ("small", "tiny / narrow / minor", "small 可分别描述尺寸、空间或程度，准确词语能让画面更清楚。"),
    )
    vocabulary_match: tuple[str, str, str] | None = None
    for option in vocabulary_options:
        if re.search(rf"\b{re.escape(option[0])}\b", body, flags=re.IGNORECASE):
            vocabulary_match = option
            break
    if vocabulary_match:
        original_word, better_words, reason = vocabulary_match
        primary_replacement = better_words.split(" / ")[0]
        vocabulary_example = re.sub(
            rf"\b{re.escape(original_word)}\b",
            primary_replacement,
            sample_sentence,
            count=1,
            flags=re.IGNORECASE,
        )
        vocabulary_original = sample_sentence
        word_choices = [{
            "original": original_word,
            "better": better_words,
            "reason": reason,
        }]
    else:
        vocabulary_original = sample_sentence
        vocabulary_example = "The room was nice. → The room felt warm and welcoming."
        word_choices = [{
            "original": "nice",
            "better": "warm and welcoming",
            "reason": "nice 比较笼统；warm and welcoming 能具体表现环境带给人的感受。",
        }]
    advice: list[dict[str, Any]] = [
        {
            "kind": "词汇表达",
            "title": "把宽泛的词换成更准确的表达",
            "observation": "文章意思已经能读懂，再把关键词说得更具体，读者会更容易看见画面和感受到语气。",
            "guidance": "先问自己这个词是在写人物、动作、环境还是感受，再选择含义最贴近的词，不需要为了显得高级而使用生僻词。",
            "original": vocabulary_original,
            "example": vocabulary_example,
            "wordChoices": word_choices,
        },
        {
            "kind": "句式表达",
            "title": "用连接词讲清句子之间的关系",
            "observation": (
                "部分句子较长，信息挤在一起，读者不容易分清先后和因果。"
                if average_sentence > 24
                else "可以让相邻句子之间的先后、原因或转折关系更明确。"
            ),
            "guidance": "两个意思关系紧密时，可以用 because、although、when 或 while 连接；信息太多时则拆成两个完整句。",
            "original": sample_sentence,
            "example": "The rain was heavy. We kept walking. → Although the rain was heavy, we kept walking.",
            "wordChoices": [],
        },
        {
            "kind": "内容描写",
            "title": "补一个动作或感官细节",
            "observation": (
                f"全文约 {word_count} 词，故事主线已经出现，还可以把一个关键时刻写得更具体。"
                if word_count < 80
                else "内容已经有一定展开，可以选择最重要的一个瞬间增加动作、声音或感受。"
            ),
            "guidance": "不要一次增加很多新情节，只挑一个关键画面，补充人物做了什么、听见什么或心里有什么感觉。",
            "original": sample_sentence,
            "example": "I entered the room. → As I stepped into the quiet room, the cold air brushed my face.",
            "wordChoices": [],
        },
    ]
    return {
        "total": round(sum(breakdown.values()) / len(ESSAY_SCORE_KEYS)),
        "breakdown": breakdown,
        "advice": normalize_essay_advice_items(advice),
    }


def normalize_essay_assessment(value: Any, body: str) -> dict[str, Any]:
    fallback = local_essay_assessment(body)
    source = value if isinstance(value, dict) else {}
    raw_scores: dict[str, int] = {}
    for key in ESSAY_SCORE_KEYS:
        try:
            raw_scores[key] = int(round(float(source[key])))
        except (KeyError, TypeError, ValueError):
            continue
    declared_scale = source.get("scale") or source.get("_scale")
    hundred_point_scale = str(declared_scale or "").strip() == "100"
    legacy_twenty_point_scale = not hundred_point_scale and raw_scores and all(score <= 20 for score in raw_scores.values())
    breakdown: dict[str, int] = {}
    for key in ESSAY_SCORE_KEYS:
        score = raw_scores.get(key)
        if score is None:
            score = int(fallback["breakdown"][key])
        elif legacy_twenty_point_scale:
            score *= 5
        breakdown[key] = min(max(score, 0), 100)
    advice = normalize_essay_advice_items(source.get("advice"))
    if not advice:
        advice = fallback["advice"]
    return {
        "total": round(sum(breakdown.values()) / len(ESSAY_SCORE_KEYS)),
        "breakdown": breakdown,
        "advice": advice,
    }


def parse_essay_optimization_result(text_value: str, body: str) -> tuple[str, dict[str, Any]]:
    raw = str(text_value or "").strip()
    json_text = raw
    if raw.startswith("```"):
        json_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        try:
            parsed = json.loads(raw[start:end + 1]) if start >= 0 and end > start else None
        except json.JSONDecodeError:
            parsed = None
    if isinstance(parsed, dict):
        optimized_body = clean_essay_body(
            parsed.get("optimizedBody")
            or parsed.get("optimized_body")
            or parsed.get("composition")
        )
        if optimized_body:
            assessment = normalize_essay_assessment(parsed.get("assessment"), body)
            return optimized_body, assessment
    if not raw:
        raise RuntimeError("AI 没有返回优化后的作文。")
    return clean_essay_body(raw), local_essay_assessment(body)


def chat_completion_text(data: dict[str, Any]) -> str:
    return str(((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()


ESSAY_TRANSLATION_SYSTEM_PROMPT = (
    "You are a professional English-to-Simplified-Chinese translator for student compositions. "
    "Translate accurately and naturally while preserving meaning, names, tone, paragraph breaks, and story details. "
    "Do not correct, expand, summarize, explain, or add facts. "
    'Return only one valid JSON object with this exact shape: {"draft":"原稿的简体中文译文","optimized":"AI稿的简体中文译文"}. '
    'If the input field "optimized" is empty, return an empty string for "optimized". '
    "Do not include markdown or any text outside the JSON object."
)


def essay_translation_messages(*, title: str, body: str, optimized_body: str | None) -> list[dict[str, str]]:
    source = {
        "title": title,
        "draft": body,
        "optimized": optimized_body or "",
    }
    return [
        {
            "role": "system",
            "content": ESSAY_TRANSLATION_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": json.dumps(source, ensure_ascii=False),
        },
    ]


def parse_essay_translation_result(
    text_value: str,
    *,
    require_optimized: bool,
) -> tuple[str, str]:
    raw = str(text_value or "").strip()
    json_text = raw
    if raw.startswith("```"):
        json_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        try:
            parsed = json.loads(raw[start:end + 1]) if start >= 0 and end > start else None
        except json.JSONDecodeError:
            parsed = None
    if not isinstance(parsed, dict):
        raise RuntimeError("AI 没有返回有效的中文译文。")

    translation_body = clean_essay_body(
        parsed.get("draft")
        or parsed.get("translation")
        or parsed.get("translationBody")
    )
    optimized_translation_body = clean_essay_body(
        parsed.get("optimized")
        or parsed.get("optimizedTranslation")
        or parsed.get("optimizedTranslationBody")
    )
    if not translation_body:
        raise RuntimeError("AI 没有返回原稿的中文译文。")
    if require_optimized and not optimized_translation_body:
        raise RuntimeError("AI 没有返回优化稿的中文译文。")
    return translation_body, optimized_translation_body


async def translate_essay_with_dashscope(
    *,
    title: str,
    body: str,
    optimized_body: str | None,
) -> tuple[str, str, str]:
    api_key = settings.dashscope_api_key.strip()
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is not configured on the server.")
    model = (settings.dashscope_text_model or "qwen-plus").strip()
    endpoint = (settings.dashscope_text_endpoint or "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions").strip()
    payload = {
        "model": model,
        "messages": essay_translation_messages(title=title, body=body, optimized_body=optimized_body),
        "temperature": 0.1,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
    translation_body, optimized_translation_body = parse_essay_translation_result(
        chat_completion_text(response.json()),
        require_optimized=bool(optimized_body),
    )
    return translation_body, optimized_translation_body, f"dashscope:{model}"


async def translate_essay_with_openai(
    *,
    title: str,
    body: str,
    optimized_body: str | None,
) -> tuple[str, str, str]:
    api_key = settings.openai_api_key.strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured on the server.")
    model = (settings.openai_text_model or "gpt-4o-mini").strip()
    payload = {
        "model": model,
        "messages": essay_translation_messages(title=title, body=body, optimized_body=optimized_body),
        "temperature": 0.1,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
    translation_body, optimized_translation_body = parse_essay_translation_result(
        chat_completion_text(response.json()),
        require_optimized=bool(optimized_body),
    )
    return translation_body, optimized_translation_body, f"openai:{model}"


async def translate_essay_with_ai(
    *,
    title: str,
    body: str,
    optimized_body: str | None,
) -> tuple[str, str, str]:
    provider = (settings.ai_text_provider or "dashscope").strip().lower()
    providers = ["openai", "dashscope"] if provider == "openai" else ["dashscope", "openai"]
    configuration_errors: list[str] = []
    for candidate in providers:
        try:
            if candidate == "dashscope":
                return await translate_essay_with_dashscope(
                    title=title,
                    body=body,
                    optimized_body=optimized_body,
                )
            return await translate_essay_with_openai(
                title=title,
                body=body,
                optimized_body=optimized_body,
            )
        except RuntimeError as exc:
            detail = str(exc)
            if "not configured" in detail:
                configuration_errors.append(detail)
                continue
            raise
    raise RuntimeError("；".join(configuration_errors) or "没有可用的 AI 文本模型。")


async def optimize_essay_with_dashscope(*, title: str, body: str) -> tuple[str, str, dict[str, Any]]:
    api_key = settings.dashscope_api_key.strip()
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is not configured on the server.")
    model = (settings.dashscope_text_model or "qwen-plus").strip()
    endpoint = (settings.dashscope_text_endpoint or "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions").strip()
    payload = {
        "model": model,
        "messages": essay_optimization_messages(title=title, body=body),
        "temperature": 0.2,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
    optimized_body, assessment = parse_essay_optimization_result(chat_completion_text(response.json()), body)
    return optimized_body, f"dashscope:{model}", assessment


async def optimize_essay_with_openai(*, title: str, body: str) -> tuple[str, str, dict[str, Any]]:
    api_key = settings.openai_api_key.strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured on the server.")
    model = (settings.openai_text_model or "gpt-4o-mini").strip()
    payload = {
        "model": model,
        "messages": essay_optimization_messages(title=title, body=body),
        "temperature": 0.2,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
    optimized_body, assessment = parse_essay_optimization_result(chat_completion_text(response.json()), body)
    return optimized_body, f"openai:{model}", assessment


async def optimize_essay_with_ai(*, title: str, body: str) -> tuple[str, str, dict[str, Any]]:
    provider = (settings.ai_text_provider or "dashscope").strip().lower()
    providers = ["openai", "dashscope"] if provider == "openai" else ["dashscope", "openai"]
    configuration_errors: list[str] = []
    for candidate in providers:
        try:
            if candidate == "dashscope":
                return await optimize_essay_with_dashscope(title=title, body=body)
            return await optimize_essay_with_openai(title=title, body=body)
        except RuntimeError as exc:
            detail = str(exc)
            if "not configured" in detail:
                configuration_errors.append(detail)
                continue
            raise
    raise RuntimeError("；".join(configuration_errors) or "没有可用的 AI 文本模型。")


async def generate_essay_cover_image(*, title: str, body: str, optimized_body: str | None = None) -> tuple[str, str]:
    selected_model = "wan2.7-image-pro"
    story_source = optimized_body or body
    prompt = " ".join(
        part
        for part in [
            "Create a polished cover image for a student's story collection.",
            f"Story title: {title}.",
            f"Story content summary: {story_source[:1600]}.",
            "Use a vivid cinematic scene that reflects the story's main mood, setting, and characters.",
            "Children's literature cover quality, warm and imaginative, realistic photo-illustration style.",
            "No readable text, no letters, no Chinese characters, no logos, no watermark, no UI elements.",
        ]
        if part
    )
    content = await generate_dashscope_prompt_image(
        api_key=settings.dashscope_api_key,
        endpoint=settings.dashscope_image_endpoint,
        task_endpoint=settings.dashscope_task_endpoint,
        poll_seconds=settings.dashscope_image_poll_seconds,
        timeout_seconds=settings.dashscope_image_timeout_seconds,
        model=selected_model,
        prompt=prompt,
    )
    return store_essay_cover_image(title, content), selected_model


def apply_essay_payload(
    essay: EssayEntry,
    payload: dict[str, Any],
    *,
    clear_generated_on_change: bool = False,
) -> bool:
    title = clean_essay_title(payload.get("title"))
    body = clean_essay_body(payload.get("body"))
    if not body:
        raise HTTPException(status_code=400, detail="请输入作文正文。")
    content_changed = bool(essay.id) and (essay.title != title or essay.body != body)
    if clear_generated_on_change and content_changed:
        preserve_essay_best_writing_result(essay)
    essay.title = title
    essay.body = body
    essay.word_count = essay_word_count(body)
    if clear_generated_on_change and content_changed:
        essay.optimized_body = None
        essay.translation_body = None
        essay.optimized_translation_body = None
        essay.optimized_word_count = 0
        essay.writing_score = 0
        essay.writing_score_breakdown = None
        essay.writing_advice = None
        essay.ai_model = None
        essay.translation_model = None
        essay.cover_url = None
        essay.cover_model = None
    return content_changed


@app.get("/api/vue/essays")
def vue_essays_api(request: Request, db: Session = Depends(get_db)):
    return essays_payload(db, request)


@app.post("/api/vue/essays")
async def vue_create_essay_api(request: Request, db: Session = Depends(get_db)):
    user = current_admin_user(request, db)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="作文数据不是有效 JSON。") from exc

    essay = EssayEntry(phone=user.phone, title="", body="")
    apply_essay_payload(essay, payload or {})
    db.add(essay)
    db.commit()
    db.refresh(essay)
    response = essays_payload(db, request)
    response["essay"] = serialize_essay(essay)
    return response


@app.post("/api/vue/essays/{essay_id}")
async def vue_update_essay_api(essay_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="作文数据不是有效 JSON。") from exc

    essay = get_owned_essay(db, request, essay_id)
    apply_essay_payload(essay, payload or {}, clear_generated_on_change=True)
    db.add(essay)
    db.commit()
    db.refresh(essay)
    response = essays_payload(db, request)
    response["essay"] = serialize_essay(essay)
    return response


@app.post("/api/vue/essays/{essay_id}/optimize")
async def vue_optimize_essay_api(essay_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="作文数据不是有效 JSON。") from exc

    essay = get_owned_essay(db, request, essay_id)
    previous_current_points = current_essay_writing_points(essay)
    preserve_essay_best_writing_result(essay)
    content_changed = apply_essay_payload(essay, payload or {}, clear_generated_on_change=True)
    energy_gain_eligible = content_changed or previous_current_points <= 0
    try:
        optimized_body, model, assessment = await optimize_essay_with_ai(title=essay.title, body=essay.body)
    except RuntimeError as exc:
        detail = str(exc)
        if "not configured" in detail:
            raise HTTPException(status_code=400, detail=detail) from exc
        raise HTTPException(status_code=502, detail=f"AI 优化失败: {detail}") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:400] if exc.response is not None else str(exc)
        if is_ai_quota_error(detail):
            raise HTTPException(status_code=402, detail="额度已经用完") from exc
        raise HTTPException(status_code=502, detail=f"AI 优化失败: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI 优化失败: {exc}") from exc

    essay.optimized_body = optimized_body
    essay.optimized_translation_body = None
    essay.optimized_word_count = essay_word_count(optimized_body)
    essay.writing_score = int(assessment["total"])
    essay.writing_score_breakdown = json.dumps(
        {**assessment["breakdown"], "_scale": 100},
        ensure_ascii=False,
        sort_keys=True,
    )
    essay.writing_advice = json.dumps(assessment["advice"], ensure_ascii=False)
    essay.ai_model = model
    current_points = min(max(sum(int(value or 0) for value in assessment["breakdown"].values()), 0), 500)
    energy_gain = award_essay_writing_improvement(
        essay,
        writing_score=int(assessment["total"]),
        writing_points=current_points,
        eligible=energy_gain_eligible,
    )
    db.add(essay)
    db.commit()
    db.refresh(essay)
    response = essays_payload(db, request)
    response["essay"] = serialize_essay(essay)
    response["energyGain"] = energy_gain
    response["energyGainEligible"] = energy_gain_eligible
    return response


@app.post("/api/vue/essays/{essay_id}/translate")
async def vue_translate_essay_api(essay_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="作文数据不是有效 JSON。") from exc

    essay = get_owned_essay(db, request, essay_id)
    apply_essay_payload(essay, payload or {}, clear_generated_on_change=True)
    try:
        translation_body, optimized_translation_body, model = await translate_essay_with_ai(
            title=essay.title,
            body=essay.body,
            optimized_body=essay.optimized_body,
        )
    except RuntimeError as exc:
        detail = str(exc)
        if "not configured" in detail:
            raise HTTPException(status_code=400, detail=detail) from exc
        raise HTTPException(status_code=502, detail=f"一键翻译失败: {detail}") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:400] if exc.response is not None else str(exc)
        if is_ai_quota_error(detail):
            raise HTTPException(status_code=402, detail="额度已经用完") from exc
        raise HTTPException(status_code=502, detail=f"一键翻译失败: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"一键翻译失败: {exc}") from exc

    essay.translation_body = translation_body
    essay.optimized_translation_body = optimized_translation_body or None
    essay.translation_model = model
    db.add(essay)
    db.commit()
    db.refresh(essay)
    response = essays_payload(db, request)
    response["essay"] = serialize_essay(essay)
    return response


@app.post("/api/vue/essays/{essay_id}/cover")
async def vue_generate_essay_cover_api(essay_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="作文数据不是有效 JSON。") from exc

    essay = get_owned_essay(db, request, essay_id)
    apply_essay_payload(essay, payload or {}, clear_generated_on_change=True)
    try:
        cover_url, model = await generate_essay_cover_image(
            title=essay.title,
            body=essay.body,
            optimized_body=essay.optimized_body,
        )
    except RuntimeError as exc:
        detail = str(exc)
        if "not configured" in detail:
            raise HTTPException(status_code=400, detail=detail) from exc
        if is_ai_quota_error(detail):
            raise HTTPException(status_code=402, detail="额度已经用完") from exc
        raise HTTPException(status_code=502, detail=f"作文封面生成失败: {detail}") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:400] if exc.response is not None else str(exc)
        if is_ai_quota_error(detail):
            raise HTTPException(status_code=402, detail="额度已经用完") from exc
        raise HTTPException(status_code=502, detail=f"作文封面生成失败: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"作文封面生成失败: {exc}") from exc

    essay.cover_url = cover_url
    essay.cover_model = model
    db.add(essay)
    db.commit()
    db.refresh(essay)
    response = essays_payload(db, request)
    response["essay"] = serialize_essay(essay)
    return response


@app.post("/api/vue/essays/{essay_id}/delete")
async def vue_delete_essay_api(essay_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="删除作文数据不是有效 JSON。") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="删除作文数据不是有效 JSON。")

    user = current_admin_user(request, db)
    password = normalize_login_password(payload.get("password"))
    if not user.login_password_hash:
        raise HTTPException(status_code=400, detail="请先给当前账号设置登录密码。")
    if not password or not verify_login_password(password, user.login_password_hash):
        raise HTTPException(status_code=403, detail="登录密码不正确。")

    essay = db.scalar(select(EssayEntry).where(EssayEntry.id == essay_id, EssayEntry.phone == user.phone))
    if not essay:
        raise HTTPException(status_code=404, detail="没有找到这篇作文。")
    db.delete(essay)
    db.commit()
    return essays_payload(db, request)


def parse_debate_json(value: str | None, fallback: Any) -> Any:
    try:
        parsed = json.loads(value or "")
    except (json.JSONDecodeError, TypeError):
        return fallback
    return parsed


def debate_datetime_text(value: datetime | None) -> str:
    return value.replace(microsecond=0).isoformat() + "Z" if value else ""


def debate_topic_payload(debate_day: date, level: str) -> dict[str, Any]:
    topic = debate_topic_for_day(debate_day, level)
    return {
        "key": topic["key"],
        "category": topic["category"],
        "title": topic["title"],
        "hints": list(topic.get("hints") or []),
    }


def debate_stances_for_turn(turn_count: int) -> tuple[str, str]:
    user_stance = "pro" if int(turn_count or 0) < DEBATE_ROUNDS_PER_SIDE else "con"
    return user_stance, "con" if user_stance == "pro" else "pro"


def debate_stage_round_for_turn(turn_count: int) -> int:
    return (max(int(turn_count or 0), 0) % DEBATE_ROUNDS_PER_SIDE) + 1


def debate_session_uses_current_scoring(session: DebateSession) -> bool:
    return int(session.max_turns or 0) >= DEBATE_MAX_TURNS


def debate_entry_points(entry: dict[str, Any], *, legacy: bool = False) -> int:
    try:
        points = int(round(float(entry.get("points") or 0)))
    except (TypeError, ValueError):
        return 0
    if legacy:
        points = round(points * DEBATE_TURN_MAX_POINTS / 30)
    return min(max(points, 0), DEBATE_TURN_MAX_POINTS)


def debate_dimensions_for_points(points: int) -> dict[str, int]:
    remaining = min(max(int(points or 0), 0), DEBATE_TURN_MAX_POINTS)
    dimensions: dict[str, int] = {}
    for key, maximum in (("claim", 3), ("reason", 3), ("evidence", 2), ("rebuttal", 2)):
        dimensions[key] = min(remaining, maximum)
        remaining -= dimensions[key]
    return dimensions


def debate_side_points(
    transcript: list[dict[str, Any]],
    *,
    legacy: bool = False,
) -> dict[str, int]:
    totals = {"pro": 0, "con": 0}
    for entry in transcript:
        if not isinstance(entry, dict) or entry.get("role") != "user":
            continue
        round_number = max(int(entry.get("round") or 1), 1)
        stance = str(entry.get("stance") or "").lower()
        if stance not in totals:
            stance = "pro" if round_number <= (1 if legacy else DEBATE_ROUNDS_PER_SIDE) else "con"
        totals[stance] += debate_entry_points(entry, legacy=legacy)
    return totals


def upgrade_active_debate_transcript(transcript: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for entry in transcript:
        if not isinstance(entry, dict):
            continue
        round_number = max(int(entry.get("round") or 1), 1)
        entry["stageRound"] = ((round_number - 1) % DEBATE_ROUNDS_PER_SIDE) + 1
        if entry.get("role") == "user":
            points = debate_entry_points(entry, legacy=True)
            entry["points"] = points
            entry["dimensions"] = debate_dimensions_for_points(points)
    return transcript


def debate_format_label(session: DebateSession) -> str:
    if debate_session_uses_current_scoring(session):
        return f"PRO {DEBATE_ROUNDS_PER_SIDE} + CON {DEBATE_ROUNDS_PER_SIDE}"
    if session.user_stance == "both" or (session.status == "active" and session.debate_date == date.today()):
        return "PRO + CON"
    return "CON" if session.user_stance == "con" else "PRO"


def serialize_debate_session(session: DebateSession | None) -> dict[str, Any] | None:
    if not session:
        return None
    topic = debate_topic_payload(session.debate_date, session.level)
    if topic["key"] != session.topic_key:
        topic.update(
            {
                "key": session.topic_key,
                "category": session.category,
                "title": session.topic,
            }
        )
    transcript = parse_debate_json(session.transcript, [])
    final_feedback = parse_debate_json(session.final_feedback, {})
    if not isinstance(transcript, list):
        transcript = []
    if not isinstance(final_feedback, dict):
        final_feedback = {}
    status = "active" if session.status == "active" else "completed"
    current_scoring = debate_session_uses_current_scoring(session)
    if status == "active" and not current_scoring:
        transcript = upgrade_active_debate_transcript(transcript)
        current_scoring = True
    side_points = debate_side_points(transcript, legacy=False) if current_scoring else {"pro": 0, "con": 0}
    user_points = sum(side_points.values()) if current_scoring else max(int(session.user_points or 0), 0)
    final_score = min(max(int(session.final_score or 0), 0), 100)
    if status == "completed":
        final_score = max(final_score, DEBATE_PASS_SCORE)
    current_user_stance, current_ai_stance = debate_stances_for_turn(session.turn_count)
    return {
        "id": session.id,
        "date": session.debate_date.isoformat(),
        "level": session.level,
        "topic": topic,
        "userStance": session.user_stance,
        "aiStance": session.ai_stance,
        "formatLabel": (
            f"PRO {DEBATE_ROUNDS_PER_SIDE} + CON {DEBATE_ROUNDS_PER_SIDE}"
            if current_scoring
            else debate_format_label(session)
        ),
        "currentUserStance": current_user_stance,
        "currentAiStance": current_ai_stance,
        "status": status,
        "statusLabel": "In progress" if status == "active" else "Completed",
        "userPoints": user_points,
        "proPoints": side_points["pro"],
        "conPoints": side_points["con"],
        "totalPoints": sum(side_points.values()),
        "turnCount": max(int(session.turn_count or 0), 0),
        "targetPoints": DEBATE_TARGET_POINTS,
        "maxTurns": DEBATE_MAX_TURNS,
        "challengeRounds": DEBATE_CHALLENGE_ROUNDS,
        "roundsPerSide": DEBATE_ROUNDS_PER_SIDE,
        "sideTargetPoints": DEBATE_SIDE_TARGET_POINTS,
        "turnMaxPoints": DEBATE_TURN_MAX_POINTS,
        "currentStageRound": (
            debate_stage_round_for_turn(session.turn_count)
            if status == "active"
            else DEBATE_ROUNDS_PER_SIDE
        ),
        "scoringVersion": 2 if current_scoring else 1,
        "transcript": transcript,
        "finalScore": final_score,
        "finalFeedback": final_feedback,
        "energyAwarded": max(int(session.energy_awarded or 0), 0),
        "aiModel": session.ai_model or "",
        "createdAt": debate_datetime_text(session.created_at),
        "updatedAt": debate_datetime_text(session.updated_at),
    }


def debate_session_for_day(db: Session, phone: str, debate_day: date) -> DebateSession | None:
    return db.scalar(
        select(DebateSession).where(
            DebateSession.phone == phone,
            DebateSession.debate_date == debate_day,
        )
    )


def serialize_debate_history_item(session: DebateSession) -> dict[str, Any]:
    topic = debate_topic_payload(session.debate_date, session.level)
    if topic["key"] != session.topic_key:
        topic.update({"category": session.category, "title": session.topic})
    completed = session.status != "active"
    transcript = parse_debate_json(session.transcript, [])
    if not isinstance(transcript, list):
        transcript = []
    current_scoring = debate_session_uses_current_scoring(session)
    side_points = debate_side_points(transcript, legacy=False) if current_scoring else {"pro": 0, "con": 0}
    final_score = min(max(int(session.final_score or 0), 0), 100)
    if completed:
        final_score = max(final_score, DEBATE_PASS_SCORE)
    return {
        "id": session.id,
        "date": session.debate_date.isoformat(),
        "level": session.level,
        "levelLabel": "Primary" if session.level == "primary" else "Middle School",
        "topic": topic,
        "userStance": session.user_stance,
        "formatLabel": debate_format_label(session),
        "status": "completed" if completed else "active",
        "statusLabel": "Completed" if completed else "In progress",
        "userPoints": max(int(session.user_points or 0), 0),
        "proPoints": side_points["pro"],
        "conPoints": side_points["con"],
        "totalPoints": sum(side_points.values()),
        "scoringVersion": 2 if current_scoring else 1,
        "finalScore": final_score,
        "energyAwarded": max(int(session.energy_awarded or 0), 0),
        "createdAt": debate_datetime_text(session.created_at),
    }


def debate_history_payload(db: Session, phone: str, limit: int = 50) -> list[dict[str, Any]]:
    sessions = db.scalars(
        select(DebateSession)
        .where(DebateSession.phone == phone)
        .order_by(DebateSession.debate_date.desc(), DebateSession.id.desc())
        .limit(limit)
    ).all()
    return [serialize_debate_history_item(session) for session in sessions]


def debate_page_payload(db: Session, request: Request) -> dict[str, Any]:
    user = current_admin_user(request, db)
    today = date.today()
    return {
        "today": today.isoformat(),
        "levels": DEBATE_LEVELS,
        "dailyTopics": {
            level["key"]: debate_topic_payload(today, level["key"])
            for level in DEBATE_LEVELS
        },
        "rules": {
            "targetPoints": DEBATE_TARGET_POINTS,
            "passScore": DEBATE_PASS_SCORE,
            "maxTurns": DEBATE_MAX_TURNS,
            "challengeRounds": DEBATE_CHALLENGE_ROUNDS,
            "roundsPerSide": DEBATE_ROUNDS_PER_SIDE,
            "sideTargetPoints": DEBATE_SIDE_TARGET_POINTS,
            "turnMaxPoints": DEBATE_TURN_MAX_POINTS,
            "argumentMaxChars": DEBATE_ARGUMENT_MAX_CHARS,
            "scoreDimensions": [
                {"key": "claim", "label": "观点清楚", "max": 3},
                {"key": "reason", "label": "理由充分", "max": 3},
                {"key": "evidence", "label": "例子有效", "max": 2},
                {"key": "rebuttal", "label": "回应对方", "max": 2},
            ],
        },
        "session": serialize_debate_session(debate_session_for_day(db, user.phone, today)),
        "history": debate_history_payload(db, user.phone),
    }


def owned_debate_session(db: Session, request: Request, session_id: int) -> DebateSession:
    user = current_admin_user(request, db)
    session = db.scalar(
        select(DebateSession).where(
            DebateSession.id == session_id,
            DebateSession.phone == user.phone,
        )
    )
    if not session:
        raise HTTPException(status_code=404, detail="没有找到这场辩论赛。")
    return session


@app.get("/api/vue/debate")
def vue_debate_api(request: Request, db: Session = Depends(get_db)):
    return debate_page_payload(db, request)


@app.get("/api/vue/debate/session/{session_id}")
def vue_debate_session_api(session_id: int, request: Request, db: Session = Depends(get_db)):
    return {"session": serialize_debate_session(owned_debate_session(db, request, session_id))}


@app.post("/api/vue/debate/start")
async def vue_start_debate_api(request: Request, db: Session = Depends(get_db)):
    user = current_admin_user(request, db)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="辩论赛设置不是有效 JSON。") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="辩论赛设置不是有效 JSON。")

    today = date.today()
    existing = debate_session_for_day(db, user.phone, today)
    if existing:
        response = debate_page_payload(db, request)
        response["session"] = serialize_debate_session(existing)
        return response

    level = str(payload.get("level") or "").strip().lower()
    if level not in {item["key"] for item in DEBATE_LEVELS}:
        raise HTTPException(status_code=400, detail="请选择小学组或初中组。")
    topic = debate_topic_for_day(today, level)
    session = DebateSession(
        phone=user.phone,
        debate_date=today,
        level=level,
        topic_key=topic["key"],
        topic=topic["title"],
        category=topic["category"],
        user_stance="both",
        ai_stance="opponent",
        status="active",
        user_points=0,
        ai_points=0,
        turn_count=0,
        target_points=DEBATE_TARGET_POINTS,
        max_turns=DEBATE_MAX_TURNS,
        transcript="[]",
        final_score=0,
        energy_awarded=0,
    )
    db.add(session)
    try:
        db.commit()
        db.refresh(session)
    except IntegrityError:
        db.rollback()
        session = debate_session_for_day(db, user.phone, today)
        if not session:
            raise
    response = debate_page_payload(db, request)
    response["session"] = serialize_debate_session(session)
    return response


@app.post("/api/vue/debate/{session_id}/turn")
async def vue_debate_turn_api(session_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="辩论内容不是有效 JSON。") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="辩论内容不是有效 JSON。")

    session = owned_debate_session(db, request, session_id)
    if session.debate_date != date.today():
        raise HTTPException(status_code=400, detail="这场辩论已经结束，请参加今天的新辩题。")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="这场辩论已经完成。")
    argument = re.sub(r"\s+", " ", str(payload.get("argument") or "").strip())[:DEBATE_ARGUMENT_MAX_CHARS]
    english_words = re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*", argument)
    if len(english_words) < 3:
        raise HTTPException(status_code=400, detail="请至少用 3 个英文单词表达你的观点。")

    transcript = parse_debate_json(session.transcript, [])
    if not isinstance(transcript, list):
        transcript = []
    initial_turn_count = int(session.turn_count or 0)
    legacy_active_session = not debate_session_uses_current_scoring(session)
    if legacy_active_session:
        transcript = upgrade_active_debate_transcript(transcript)
    side_points_before_turn = debate_side_points(transcript)
    user_points_before_turn = sum(side_points_before_turn.values())
    round_user_stance, round_ai_stance = debate_stances_for_turn(initial_turn_count)
    current_topic = debate_topic_for_day(session.debate_date, session.level)
    topic_text = current_topic["title"] if current_topic["key"] == session.topic_key else session.topic
    try:
        result, model = await debate_turn_with_ai(
            level=session.level,
            topic=topic_text,
            user_stance=round_user_stance,
            ai_stance=round_ai_stance,
            user_points=user_points_before_turn,
            turn_count=initial_turn_count,
            argument=argument,
            transcript=transcript,
        )
    except RuntimeError as exc:
        detail = str(exc)
        if "not configured" in detail:
            raise HTTPException(status_code=400, detail=detail) from exc
        if is_ai_quota_error(detail):
            raise HTTPException(status_code=402, detail="AI 文本额度已经用完") from exc
        raise HTTPException(status_code=502, detail=f"AI 辩手暂时没有回应：{detail}") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:400] if exc.response is not None else str(exc)
        if is_ai_quota_error(detail):
            raise HTTPException(status_code=402, detail="AI 文本额度已经用完") from exc
        raise HTTPException(status_code=502, detail=f"AI 辩手暂时没有回应：{detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI 辩手暂时没有回应：{exc}") from exc

    db.expire_all()
    session = owned_debate_session(db, request, session_id)
    if session.status != "active" or int(session.turn_count or 0) != initial_turn_count:
        raise HTTPException(status_code=409, detail="这一轮已经提交，请刷新页面查看最新赛况。")

    round_number = initial_turn_count + 1
    stage_round = debate_stage_round_for_turn(initial_turn_count)
    now = datetime.utcnow()
    transcript = parse_debate_json(session.transcript, [])
    if not isinstance(transcript, list):
        transcript = []
    if legacy_active_session:
        transcript = upgrade_active_debate_transcript(transcript)
    side_points_before_turn = debate_side_points(transcript)
    transcript.extend(
        [
            {
                "role": "user",
                "round": round_number,
                "stageRound": stage_round,
                "stance": round_user_stance,
                "text": argument,
                "points": int(result["userPoints"]),
                "dimensions": result["userDimensions"],
                "createdAt": debate_datetime_text(now),
            },
            {
                "role": "ai",
                "round": round_number,
                "stageRound": stage_round,
                "stance": round_ai_stance,
                "text": result["aiReply"],
                "coachNote": result["coachNote"],
                "highlight": result["highlight"],
                "createdAt": debate_datetime_text(now),
            },
        ]
    )
    session.user_points = sum(side_points_before_turn.values()) + int(result["userPoints"])
    session.ai_points = 0
    session.user_stance = "both"
    session.ai_stance = "opponent"
    session.turn_count = round_number
    session.target_points = DEBATE_TARGET_POINTS
    session.max_turns = DEBATE_MAX_TURNS
    if current_topic["key"] == session.topic_key:
        session.topic = current_topic["title"]
        session.category = current_topic["category"]
    session.status = debate_result_status(
        session.user_points,
        session.turn_count,
        target_points=session.target_points,
        max_turns=session.max_turns,
    )
    session.transcript = json.dumps(transcript, ensure_ascii=False)
    session.ai_model = model
    energy_gain = 0
    if session.status != "active":
        review = result["finalReview"]
        session.final_score = debate_encouragement_score(
            session.user_points,
            session.turn_count,
        )
        session.final_feedback = json.dumps(review, ensure_ascii=False)
        if int(session.energy_awarded or 0) <= 0:
            energy_gain = debate_energy_reward(session.final_score)
            session.energy_awarded = energy_gain
            db.add(
                CatWorldEnergyGrant(
                    phone=session.phone,
                    amount=energy_gain,
                    reason=f"AI辩论赛 {session.debate_date.isoformat()} {session.topic[:80]}",
                    granted_by_phone="system:debate",
                    created_at=now,
                )
            )
    db.add(session)
    db.commit()
    db.refresh(session)
    response = debate_page_payload(db, request)
    response["session"] = serialize_debate_session(session)
    response["energyGain"] = energy_gain
    return response


@app.get("/api/vue/lists")
def vue_lists_api(db: Session = Depends(get_db)):
    return lists_payload(db)


@app.post("/api/vue/lists/groups")
async def vue_create_word_list_group_api(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="单词组数据不是有效 JSON。") from exc

    name = clean_list_name(str((payload or {}).get("name") or ""))
    if not name:
        raise HTTPException(status_code=400, detail="请输入单词组名称。")

    group = get_or_create_word_list_group_by_name(db, name)
    response = lists_payload(db)
    response["group"] = serialize_word_list_group(db, group)
    return response


@app.post("/api/vue/lists/{word_list_id}/group")
async def vue_move_word_list_group_api(word_list_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="单词组数据不是有效 JSON。") from exc

    word_list = db.get(WordList, word_list_id)
    if not word_list or is_wrong_word_list_name(word_list.name):
        raise HTTPException(status_code=404, detail="没有找到这个单词表。")

    raw_group_id = (payload or {}).get("group_id")
    group_id: int | None = None
    if raw_group_id not in (None, "", 0, "0", "none", "null"):
        try:
            group_id = int(raw_group_id)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="单词组编号无效。") from exc
        if not db.get(WordListGroup, group_id):
            raise HTTPException(status_code=404, detail="没有找到这个单词组。")

    word_list.group_id = group_id
    db.add(word_list)
    db.commit()
    return lists_payload(db)


@app.post("/api/vue/lists/groups/{group_id}/delete")
async def vue_delete_word_list_group_api(group_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="删除单词组数据不是有效 JSON。") from exc

    password = str((payload or {}).get("password") or "")
    if password != settings.list_delete_password:
        raise HTTPException(status_code=403, detail="删除密码不正确")

    group = db.get(WordListGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="没有找到这个单词组。")

    list_count = db.scalar(select(func.count(WordList.id)).where(WordList.group_id == group_id)) or 0
    if list_count:
        raise HTTPException(status_code=400, detail="这个单词组里还有单词表，请先移出后再删除。")

    db.delete(group)
    db.commit()
    return lists_payload(db)


@app.post("/api/vue/lists/reorder")
async def vue_reorder_lists_api(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="排序数据不是有效 JSON。") from exc

    raw_ids = payload.get("ordered_ids") if isinstance(payload, dict) else None
    if not isinstance(raw_ids, list):
        raise HTTPException(status_code=400, detail="缺少单词表排序数据。")

    word_lists = regular_word_lists(db)
    by_id = {word_list.id: word_list for word_list in word_lists}
    ordered_ids: list[int] = []
    seen: set[int] = set()
    for raw_id in raw_ids:
        try:
            word_list_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if word_list_id in by_id and word_list_id not in seen:
            ordered_ids.append(word_list_id)
            seen.add(word_list_id)

    if not ordered_ids:
        raise HTTPException(status_code=400, detail="没有可保存的单词表顺序。")

    final_ids = ordered_ids + [word_list.id for word_list in word_lists if word_list.id not in seen]
    for index, word_list_id in enumerate(final_ids, start=1):
        word_list = by_id[word_list_id]
        word_list.display_order = index * 10
        db.add(word_list)
    db.commit()

    response = lists_payload(db)
    response["ok"] = True
    return response


@app.get("/api/vue/lists/search")
def vue_list_word_search_api(q: str = Query(default="", max_length=80), db: Session = Depends(get_db)):
    query = " ".join(q.strip().split())
    if not query:
        return {"query": "", "results": []}

    like_query = f"%{query.lower()}%"
    rows = db.execute(
        select(Word, WordList)
        .join(WordListItem, WordListItem.word_id == Word.id)
        .join(WordList, WordList.id == WordListItem.word_list_id)
        .where(func.lower(Word.word).like(like_query))
        .order_by(Word.word.asc(), WordList.name.asc(), WordList.id.asc())
        .limit(300)
    ).all()

    grouped: dict[int, dict[str, Any]] = {}
    for word, word_list in rows:
        if is_wrong_word_list_name(word_list.name):
            continue
        item = grouped.setdefault(
            word.id,
            {
                "word": serialize_word(word),
                "lists": [],
            },
        )
        item["lists"].append({"id": word_list.id, "name": word_list.name})

    normalized_query = query.lower()
    results = sorted(
        grouped.values(),
        key=lambda item: (
            not str(item["word"].get("word") or "").lower().startswith(normalized_query),
            str(item["word"].get("word") or "").lower(),
        ),
    )[:40]
    for item in results:
        item["list_count"] = len(item["lists"])
    return {"query": query, "results": results}


@app.get("/api/vue/lists/{word_list_id}")
def vue_list_detail_api(word_list_id: int, db: Session = Depends(get_db)):
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")
    groups = [serialize_word_list_group(db, group) for group in word_list_groups(db)]
    current_group = db.get(WordListGroup, word_list.group_id) if word_list.group_id else None
    words = db.scalars(
        select(Word)
        .join(WordListItem, WordListItem.word_id == Word.id)
        .where(WordListItem.word_list_id == word_list_id)
        .order_by(WordListItem.id.asc())
    ).all()
    apply_word_resources(db, words, include_image=False)
    stats = challenge_counts_for_words(db, [word.id for word in words])
    return {
        "word_list": {
            "id": word_list.id,
            "name": word_list.name,
            "sequence_offset": word_list.sequence_offset,
            "group_id": word_list.group_id,
            "group": serialize_word_list_group_brief(current_group),
        },
        "groups": groups,
        "current_group": serialize_word_list_group_brief(current_group),
        "challenge": challenge_state(db, word_list),
        "ai_image_quota": ai_image_quota_status(db, model=LIST_AI_IMAGE_DEFAULT_MODEL),
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


@app.get("/api/vue/lists/{word_list_id}/words/candidates")
def vue_word_candidates_for_list(
    word_list_id: int,
    q: str = Query(default=""),
    db: Session = Depends(get_db),
):
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")
    word_text = clean_manual_word_text(q)
    candidates = manual_word_candidates(db, word_text, word_list.id)
    return {
        "ok": True,
        "query": word_text,
        "candidates": candidates,
    }


@app.post("/api/vue/lists/{word_list_id}/words")
def vue_create_word_in_list(
    word_list_id: int,
    word: str = Form(default=""),
    existing_word_id: int | None = Form(default=None),
    phonetic: str = Form(default=""),
    part_of_speech: str = Form(default=""),
    english_definition: str = Form(default=""),
    chinese_definition: str = Form(default=""),
    english_example: str = Form(default=""),
    note: str = Form(default=""),
    db: Session = Depends(get_db),
):
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")
    if existing_word_id:
        existing_word = db.get(Word, existing_word_id)
        if not existing_word:
            raise HTTPException(status_code=404, detail="Word not found")
        link_word_to_list(db, word_list.id, existing_word.id)
        return {
            "ok": True,
            "source": "existing",
            "word": serialize_word(existing_word),
            "word_list_id": word_list.id,
            "word_list_name": word_list.name,
            "detail_url": f"/words/{existing_word.id}?edit=1&list_id={word_list.id}",
        }
    word_text = clean_manual_word_text(word)
    row = {
        "word": word_text,
        "phonetic": optional_manual_word_text(phonetic),
        "part_of_speech": optional_manual_word_text(part_of_speech),
        "english_definition": optional_manual_word_text(english_definition),
        "chinese_definition": optional_manual_word_text(chinese_definition),
        "english_example": optional_manual_word_text(english_example),
        "note": optional_manual_word_text(note),
        "row_number": 1,
    }
    word_ids = import_rows([row], db, word_list)
    if not word_ids:
        raise HTTPException(status_code=400, detail="单词保存失败，请检查输入内容。")
    created_word = db.get(Word, word_ids[0])
    if not created_word:
        raise HTTPException(status_code=404, detail="Word not found")
    start_enrichment_thread(word_ids, include_images=False)
    return {
        "ok": True,
        "word": serialize_word(created_word),
        "word_list_id": word_list.id,
        "word_list_name": word_list.name,
        "detail_url": f"/words/{created_word.id}?edit=1&list_id={word_list.id}",
    }


@app.get("/api/vue/wrong-words")
def vue_wrong_words_api(db: Session = Depends(get_db)):
    groups = [wrong_word_date_group_payload(db, wrong_date) for wrong_date in wrong_word_dates(db)]
    return {
        "groups": groups,
        "counts": {
            "all": sum(group["count"] for group in groups),
            "pending": sum(group["pending_count"] for group in groups),
            "corrected": sum(group["corrected_count"] for group in groups),
        },
    }


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
    apply_word_resource(db, word, commit=True, include_image=False)
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
    audio_sources = {
        "us": word_audio_source(word, "us", audio_version),
        "gb": word_audio_source(word, "gb", audio_version),
    }
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
        "audio_sources": audio_sources,
        "media_sources": word_media_sources(db, word, audio_sources=audio_sources),
        "navigation": nav,
    }


def word_audio_source(word: Word, accent: str, audio_version: str | None = None) -> str:
    audio_url = word.british_audio_url if accent == "gb" else word.american_audio_url
    source = audio_url if is_local_audio_url(audio_url) else f"/tts?word={quote_plus(word.word)}&accent={accent}&v=2"
    if audio_version:
        separator = "&" if "?" in source else "?"
        return f"{source}{separator}av={audio_version}"
    return source


def media_path_without_query(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.split("?", 1)[0].split("#", 1)[0]


def media_filename(value: str | None) -> str:
    path = media_path_without_query(value)
    if not path:
        return ""
    parsed_path = urlparse(path).path if "://" in path else path
    return Path(parsed_path).name


def audio_source_meta(source: str | None = None, audio_url: str | None = None) -> dict[str, str]:
    source_marker = str(source or "").strip()
    filename = media_filename(audio_url)
    combined = f"{source_marker.lower()} {filename.lower()} {str(audio_url or '').lower()}"
    if not audio_url:
        prefix, label = "未配置", "暂无音频"
    elif (
        source_marker.lower().startswith("spb")
        or "miniprogram" in combined
        or filename.lower().startswith("spb-")
        or "-spb-" in filename.lower()
    ):
        prefix, label = "SPB", "SPB小程序"
    elif (
        filename.lower().startswith("ai-")
        or source_marker.lower().startswith("ai")
        or "ai-tts" in combined
        or "aliyun" in combined
        or "dashscope" in combined
        or "phoneme" in combined
    ):
        prefix, label = "AI", "AI生成"
    elif (
        filename.lower().startswith("dict-")
        or "dictionary" in combined
        or "youdao" in combined
        or "free-dictionary" in combined
        or "google" in combined
        or "tts" in combined
    ):
        prefix, label = "词典", "词典音源"
    elif filename.lower().startswith("record-") or "record" in combined:
        prefix, label = "录音", "本地录音"
    elif "upload" in combined:
        prefix, label = "上传", "上传音频"
    elif is_local_audio_url(audio_url):
        prefix, label = "本地", "服务器音频"
    elif str(audio_url or "").startswith(("http://", "https://")):
        prefix, label = "外链", "外链音频"
    else:
        prefix, label = "未知", "来源未知"
    return {"source": source_marker, "prefix": prefix, "label": label, "filename": filename}


def image_source_meta(source: str | None = None, image_url: str | None = None) -> dict[str, str]:
    source_marker = str(source or "").strip()
    filename = media_filename(image_url)
    combined = f"{source_marker.lower()} {filename.lower()} {str(image_url or '').lower()}"
    if not image_url:
        prefix, label = "未配置", "暂无图片"
    elif (
        source_marker.lower().startswith("spb")
        or "miniprogram" in combined
        or filename.lower().startswith("spb-")
        or "-spb-" in filename.lower()
    ):
        prefix, label = "SPB", "SPB图片"
    elif (
        filename.lower().startswith("ai-")
        or "ai-image" in combined
        or "generated" in combined
        or "dashscope" in combined
        or "qwen" in combined
        or "wan" in combined
    ):
        prefix, label = "AI", "AI生成图"
    elif "upload" in combined or "batch-upload" in combined:
        prefix, label = "上传", "上传图片"
    elif "network" in combined or str(image_url or "").startswith(("http://", "https://")):
        prefix, label = "网络", "网络选图"
    elif is_local_media_url(image_url):
        prefix, label = "本地", "服务器图片"
    else:
        prefix, label = "未知", "来源未知"
    return {"source": source_marker, "prefix": prefix, "label": label, "filename": filename}


def media_value_matches(current_url: str | None, resource_url: str | None) -> bool:
    current = media_path_without_query(current_url)
    resource = media_path_without_query(resource_url)
    if not current or not resource:
        return False
    if current == resource:
        return True
    return media_filename(current) == media_filename(resource)


def word_media_sources(db: Session, word: Word, audio_sources: dict[str, str] | None = None) -> dict[str, Any]:
    resource = get_word_resource(db, word.word)

    def resource_source(current_url: str | None, resource_url: str | None, source: str | None) -> str | None:
        if resource and media_value_matches(current_url, resource_url):
            return source
        return None

    us_audio = word.american_audio_url or (audio_sources or {}).get("us")
    gb_audio = word.british_audio_url or (audio_sources or {}).get("gb")
    return {
        "image": image_source_meta(
            resource_source(word.image_url, getattr(resource, "image_url", None), getattr(resource, "image_source", None)),
            word.image_url,
        ),
        "audio": {
            "us": audio_source_meta(
                resource_source(word.american_audio_url, getattr(resource, "american_audio_url", None), getattr(resource, "american_audio_source", None)),
                us_audio,
            ),
            "gb": audio_source_meta(
                resource_source(word.british_audio_url, getattr(resource, "british_audio_url", None), getattr(resource, "british_audio_source", None)),
                gb_audio,
            ),
            "definition": audio_source_meta(
                resource_source(
                    word.english_definition_audio_url,
                    getattr(resource, "english_definition_audio_url", None),
                    getattr(resource, "english_definition_audio_source", None),
                ),
                word.english_definition_audio_url,
            ),
            "example": audio_source_meta(
                resource_source(
                    word.english_example_audio_url,
                    getattr(resource, "english_example_audio_url", None),
                    getattr(resource, "english_example_audio_source", None),
                ),
                word.english_example_audio_url,
            ),
        },
    }


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
        "phonetic",
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
    previous_value = getattr(word, field, None)
    definition_audio_invalidated = False
    example_audio_invalidated = False
    setattr(word, field, next_value)
    if field == "english_definition":
        word.english_definition_locked = True
        if (previous_value or "").strip() != (next_value or "").strip():
            word.english_definition_audio_url = None
            definition_audio_invalidated = True
    if field == "chinese_definition":
        word.chinese_definition_locked = True
    if field == "english_example":
        word.english_example_locked = True
        if (previous_value or "").strip() != (next_value or "").strip():
            word.english_example_audio_url = None
            example_audio_invalidated = True
    word.enrichment_error = None
    db.add(word)
    if definition_audio_invalidated or example_audio_invalidated:
        resource = get_word_resource(db, word.word)
        if resource:
            if definition_audio_invalidated:
                resource.english_definition_audio_url = None
                resource.english_definition_audio_source = None
            if example_audio_invalidated:
                resource.english_example_audio_url = None
                resource.english_example_audio_source = None
            db.add(resource)
    db.commit()
    remember_word_resource(db, word, override_text=True, commit=True)
    return {"ok": True, "field": field, "value": next_value}


@app.post("/api/vue/words/{word_id}/remove-from-list")
def vue_remove_word_from_list(
    word_id: int,
    request: Request,
    list_id: int = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = current_admin_user(request, db)
    cleaned_password = normalize_login_password(password)
    if not cleaned_password or not verify_login_password(cleaned_password, user.login_password_hash):
        raise HTTPException(status_code=403, detail="登录密码不正确。")

    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    word_list = db.get(WordList, list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")

    item = db.scalar(
        select(WordListItem).where(
            WordListItem.word_list_id == list_id,
            WordListItem.word_id == word_id,
        )
    )
    if not item:
        raise HTTPException(status_code=404, detail="这个单词不在当前单词表中。")

    db.delete(item)
    db.execute(delete(ChallengeProgress).where(ChallengeProgress.word_list_id == list_id))
    db.commit()
    return {
        "ok": True,
        "word_id": word_id,
        "word": word.word,
        "list_id": list_id,
        "word_list_name": word_list.name,
        "redirect_url": f"/lists/{list_id}",
    }


@app.post("/api/vue/words/{word_id}/refresh")
async def vue_refresh_word(
    word_id: int,
    edit_token: str = Form(default=""),
    list_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    apply_word_resource(db, word, commit=False, include_image=False)
    await apply_spb_details_to_word(db, word, list_id=list_id)
    db.add(word)
    db.commit()
    db.refresh(word)
    await enrich_word(db, word, include_images=False)
    remember_word_resource(db, word, commit=True)
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


def update_import_preview_job(job_id: str, **changes) -> None:
    with IMPORT_PREVIEW_JOB_LOCK:
        job = IMPORT_PREVIEW_JOBS.get(job_id)
        if not job:
            return
        job.update(changes)
        total = max(int(job.get("total") or 0), 0)
        processed = min(max(int(job.get("processed") or 0), 0), total) if total else 0
        job["processed"] = processed
        job["percent"] = 100 if job.get("status") == "complete" else round((processed / total) * 100) if total else 0
        job["updated_at"] = datetime.utcnow().isoformat()


def import_preview_job_snapshot(job_id: str) -> dict[str, Any] | None:
    with IMPORT_PREVIEW_JOB_LOCK:
        job = IMPORT_PREVIEW_JOBS.get(job_id)
        return dict(job) if job else None


def store_import_preview_job(job: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    with IMPORT_PREVIEW_JOB_LOCK:
        existing_job = IMPORT_PREVIEW_JOBS.get(job["id"])
        if existing_job and existing_job.get("status") in {"queued", "running"}:
            return dict(existing_job), False
        terminal_jobs = sorted(
            (
                item
                for item in IMPORT_PREVIEW_JOBS.values()
                if item.get("status") in {"complete", "failed"} and item.get("id") != job["id"]
            ),
            key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""),
            reverse=True,
        )
        for stale_job in terminal_jobs[99:]:
            IMPORT_PREVIEW_JOBS.pop(str(stale_job["id"]), None)
        IMPORT_PREVIEW_JOBS[job["id"]] = job
        return dict(job), True


def run_import_preview_job(
    job_id: str,
    rows: list[dict[str, Any]],
    word_list_id: str,
    word_list_name: str,
) -> None:
    db = SessionLocal()
    chunk_size = 500
    total = len(rows)
    total_lists = max((total + chunk_size - 1) // chunk_size, 1)
    base_name = clean_list_name(word_list_name)
    word_ids: list[int] = []
    split_lists: list[WordList] = []
    target_list: WordList | None = None

    try:
        update_import_preview_job(
            job_id,
            status="running",
            stage="importing",
            total=total,
            total_lists=total_lists,
            completed_lists=0,
            current_list=1,
            message=f"正在写入第 1 / {total_lists} 个词表。",
        )

        if total > chunk_size:
            split_group = get_or_create_word_list_group_by_name(db, base_name)
            for chunk_index in range(0, total, chunk_size):
                chunk_number = (chunk_index // chunk_size) + 1
                chunk = rows[chunk_index : chunk_index + chunk_size]
                chunk_list = get_or_create_word_list_by_name(db, f"{base_name}-{chunk_number}")
                clear_word_list_items(db, chunk_list.id)
                chunk_list.group_id = split_group.id
                chunk_list.sequence_offset = chunk_index
                db.add(chunk_list)
                db.commit()
                split_lists.append(chunk_list)
                update_import_preview_job(
                    job_id,
                    current_list=chunk_number,
                    message=f"正在写入第 {chunk_number} / {total_lists} 个词表。",
                )

                def report_chunk_progress(chunk_processed: int, *, start: int = chunk_index, size: int = len(chunk)) -> None:
                    if chunk_processed == size or chunk_processed % 10 == 0:
                        update_import_preview_job(job_id, processed=start + chunk_processed)

                word_ids.extend(import_rows(chunk, db, chunk_list, progress_callback=report_chunk_progress))
                update_import_preview_job(
                    job_id,
                    processed=min(chunk_index + len(chunk), total),
                    completed_lists=chunk_number,
                )
            target_list = split_lists[0]
        else:
            target_list = get_or_create_word_list(db, word_list_id, base_name)
            if not word_list_id:
                target_list.sequence_offset = 0
                db.add(target_list)
                db.commit()

            def report_single_list_progress(processed: int) -> None:
                if processed == total or processed % 10 == 0:
                    update_import_preview_job(job_id, processed=processed)

            word_ids = import_rows(rows, db, target_list, progress_callback=report_single_list_progress)
            update_import_preview_job(job_id, processed=total, completed_lists=1)

        update_import_preview_job(
            job_id,
            status="running",
            stage="finalizing",
            processed=total,
            message="正在完成导入并准备单词详情。",
        )
        if word_ids:
            start_enrichment_thread(word_ids, include_images=False)
        if target_list is None:
            raise RuntimeError("导入完成后没有找到目标词表")

        result = {
            "ok": True,
            "word_list_id": target_list.id,
            "word_list_name": target_list.name,
            "count": len(word_ids),
            "split_word_lists": [
                {"id": word_list.id, "name": word_list.name, "sequence_offset": word_list.sequence_offset}
                for word_list in split_lists
            ],
            "image_result": {"matched": 0, "unmatched": 0, "failed": 0},
        }
        update_import_preview_job(
            job_id,
            status="complete",
            stage="complete",
            processed=total,
            completed_lists=total_lists,
            current_list=total_lists,
            message=f"导入完成：{len(word_ids)} 个单词，{total_lists} 个词表。",
            result=result,
        )
        preview_path(job_id).unlink(missing_ok=True)
        preview_excel_path(job_id).unlink(missing_ok=True)
    except Exception as exc:
        db.rollback()
        update_import_preview_job(
            job_id,
            status="failed",
            stage="failed",
            message=f"导入失败：{str(exc)[:240]}",
        )
    finally:
        db.close()


@app.get("/api/vue/import-preview/{job_id}/status")
def vue_import_preview_status(job_id: str):
    preview_path(job_id)
    job = import_preview_job_snapshot(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="没有找到这个导入任务")
    return {"ok": True, "job": job}


@app.post("/api/vue/import-preview")
async def vue_import_preview(
    preview_id: str = Form(...),
    word_list_id: str = Form(default=""),
    word_list_name: str = Form(...),
    word_columns: list[str] = Form(default=[]),
    selected_rows: list[int] = Form(default=[]),
    selected_columns: list[str] = Form(default=[]),
    image_files: list[UploadFile] = File(default=[]),
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
    total = len(rows)
    total_lists = max((total + 499) // 500, 1)
    now = datetime.utcnow().isoformat()
    job, should_start = store_import_preview_job({
        "id": preview_id,
        "status": "queued",
        "stage": "queued",
        "total": total,
        "processed": 0,
        "percent": 0,
        "total_lists": total_lists,
        "completed_lists": 0,
        "current_list": 0,
        "message": f"准备导入 {total} 个单词，将生成 {total_lists} 个词表。",
        "created_at": now,
        "updated_at": now,
        "result": None,
    })
    if should_start:
        Thread(
            target=run_import_preview_job,
            args=(preview_id, rows, word_list_id, word_list_name),
            daemon=True,
        ).start()
    return JSONResponse({
        "ok": True,
        "job": job,
    }, status_code=202)


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
    request: Request,
    action: str = Form(default="known"),
    daily_count: str = Form(default="20"),
    start_count: str = Form(default="0"),
    session_correct: str = Form(default="0"),
    session_wrong: str = Form(default="0"),
    spelling: str = Form(default=""),
    word_id: str = Form(default=""),
    wrong_date: str = Form(default=""),
    client_trace_id: str = Form(default=""),
    client_page_url: str = Form(default=""),
    client_page_version: str = Form(default=""),
    db: Session = Depends(get_db),
):
    trace_id = challenge_trace_id(client_trace_id)
    daily_count_value = parse_form_int(daily_count, default=20, min_value=1, max_value=500)
    start_count_value = parse_form_int(start_count, default=0, min_value=0)
    session_correct_value = parse_form_int(session_correct, default=0, min_value=0)
    session_wrong_value = parse_form_int(session_wrong, default=0, min_value=0)
    answer_word_id = parse_form_int(word_id, default=0, min_value=0) or None
    client_host = request.client.host if request.client else "-"
    try:
        result = None
        for attempt in range(2):
            try:
                result = apply_challenge_answer(
                    db,
                    word_list_id=word_list_id,
                    action=action,
                    daily_count=daily_count_value,
                    start_count=start_count_value,
                    session_correct=session_correct_value,
                    session_wrong=session_wrong_value,
                    spelling=spelling,
                    answer_word_id=answer_word_id,
                    wrong_date=wrong_date,
                )
                break
            except (IntegrityError, OperationalError):
                db.rollback()
                CHALLENGE_LOGGER.warning(
                    "challenge answer db retry trace_id=%s attempt=%s word_list_id=%s word_id=%s action=%s daily_count=%s start_count=%s session_correct=%s session_wrong=%s wrong_date=%s page_version=%s page_url=%s client=%s",
                    trace_id,
                    attempt + 1,
                    word_list_id,
                    answer_word_id or "",
                    action,
                    daily_count_value,
                    start_count_value,
                    session_correct_value,
                    session_wrong_value,
                    wrong_date,
                    client_page_version,
                    client_page_url,
                    client_host,
                    exc_info=True,
                )
                if attempt:
                    raise
        if result is None:
            raise challenge_http_error(503, "提交暂时失败，请刷新后继续挑战。", trace_id)
        query = {
            "daily_count": result["daily_count"],
            "start_count": result["start_count"],
            "session_correct": result["session_correct"],
            "session_wrong": result["session_wrong"],
        }
        if result["wrong_date"]:
            query["wrong_date"] = result["wrong_date"].isoformat()
        next_state = None
        try:
            next_state = challenge_payload(
                db,
                word_list_id=word_list_id,
                daily_count=result["daily_count"],
                start_count=result["start_count"],
                session_correct=result["session_correct"],
                session_wrong=result["session_wrong"],
                wrong_date=result["wrong_date"].isoformat() if result["wrong_date"] else None,
            )
        except Exception:
            db.rollback()
            CHALLENGE_LOGGER.exception(
                "challenge answer state reload failed trace_id=%s word_list_id=%s word_id=%s page_version=%s page_url=%s client=%s",
                trace_id,
                word_list_id,
                answer_word_id or "",
                client_page_version,
                client_page_url,
                client_host,
            )
        CHALLENGE_LOGGER.warning(
            "challenge answer accepted trace_id=%s word_list_id=%s word_id=%s action=%s daily_count=%s start_count=%s session_correct=%s session_wrong=%s wrong_date=%s next_state=%s page_version=%s page_url=%s client=%s",
            trace_id,
            word_list_id,
            answer_word_id or "",
            action,
            daily_count_value,
            start_count_value,
            result["session_correct"],
            result["session_wrong"],
            result["wrong_date"].isoformat() if result["wrong_date"] else "",
            "yes" if next_state else "no",
            client_page_version,
            client_page_url,
            client_host,
        )
        return {"ok": True, "query": query, "state": next_state, "answer": result.get("answer"), "trace_id": trace_id}
    except HTTPException as exc:
        detail = str(exc.detail or "提交失败")
        if trace_id not in detail:
            detail = f"{detail}（追踪码：{trace_id}）"
        CHALLENGE_LOGGER.warning(
            "challenge answer rejected trace_id=%s status=%s word_list_id=%s word_id=%s action=%s daily_count=%s start_count=%s session_correct=%s session_wrong=%s wrong_date=%s page_version=%s page_url=%s client=%s detail=%s",
            trace_id,
            exc.status_code,
            word_list_id,
            answer_word_id or "",
            action,
            daily_count_value,
            start_count_value,
            session_correct_value,
            session_wrong_value,
            wrong_date,
            client_page_version,
            client_page_url,
            client_host,
            detail,
            exc_info=exc.status_code >= 500,
        )
        raise HTTPException(
            status_code=exc.status_code,
            detail=detail,
            headers={**(exc.headers or {}), "X-SpeakEasy-Trace-Id": trace_id},
        )
    except (IntegrityError, OperationalError):
        db.rollback()
        CHALLENGE_LOGGER.exception(
            "challenge answer database failed trace_id=%s word_list_id=%s word_id=%s action=%s daily_count=%s start_count=%s session_correct=%s session_wrong=%s wrong_date=%s page_version=%s page_url=%s client=%s",
            trace_id,
            word_list_id,
            answer_word_id or "",
            action,
            daily_count_value,
            start_count_value,
            session_correct_value,
            session_wrong_value,
            wrong_date,
            client_page_version,
            client_page_url,
            client_host,
        )
        raise challenge_http_error(503, "提交暂时失败，请刷新后继续挑战。", trace_id)
    except Exception:
        db.rollback()
        CHALLENGE_LOGGER.exception(
            "challenge answer failed trace_id=%s word_list_id=%s word_id=%s action=%s daily_count=%s start_count=%s session_correct=%s session_wrong=%s wrong_date=%s page_version=%s page_url=%s client=%s",
            trace_id,
            word_list_id,
            answer_word_id or "",
            action,
            daily_count_value,
            start_count_value,
            session_correct_value,
            session_wrong_value,
            wrong_date,
            client_page_version,
            client_page_url,
            client_host,
        )
        raise challenge_http_error(500, "提交失败，服务器已记录错误。", trace_id)


@app.post("/api/challenge/words/{word_id}/audio-issue")
async def challenge_word_audio_issue_api(
    word_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    flag = bool(payload.get("audio_issue", True)) if isinstance(payload, dict) else True
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    word.audio_issue = flag
    db.add(word)
    db.commit()
    db.refresh(word)
    return {"ok": True, "word_id": word.id, "audio_issue": word.audio_issue}


@app.post("/api/challenge/words/{word_id}/image-issue")
async def challenge_word_image_issue_api(
    word_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    flag = bool(payload.get("image_issue", True)) if isinstance(payload, dict) else True
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    word.image_issue = flag
    db.add(word)
    db.commit()
    db.refresh(word)
    return {"ok": True, "word_id": word.id, "image_issue": word.image_issue}


@app.get("/wrong-words", response_class=HTMLResponse)
def wrong_words_page(request: Request, db: Session = Depends(get_db)):
    return vue_shell(request, db, "wrong-words")


@app.get("/growth", response_class=HTMLResponse)
def growth_page(request: Request, db: Session = Depends(get_db)):
    return vue_shell(request, db, "growth")


@app.get("/cat-world", response_class=HTMLResponse)
def cat_world_page(request: Request, db: Session = Depends(get_db)):
    return vue_shell(request, db, "cat-world")


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, db: Session = Depends(get_db)):
    return vue_shell(request, db, "admin")


@app.get("/spb", response_class=HTMLResponse)
def spb_page(request: Request, db: Session = Depends(get_db)):
    return vue_shell(request, db, "spb")


@app.get("/spb/{collection_key}", response_class=HTMLResponse)
def spb_collection_page(collection_key: str, request: Request, db: Session = Depends(get_db)):
    if collection_key not in {"team"}:
        raise HTTPException(status_code=404, detail="SPB collection not found")
    return vue_shell(request, db, f"spb/{collection_key}")


SPB_INDIVIDUAL_WORD_BANK_GROUPS = [
    {
        "key": "beginner",
        "title": "小初组",
        "subtitle": "Beginner Group(G1-G2)",
        "status": "available",
        "prefix": "SPB个人赛冠军词库-小初组",
        "source_count": 1299,
        "source_file": "spb_individual_beginner_g1_g2_words.json",
        "source_url": "https://cdn.spbcn.org/DownloadFile/en_word_thesaurus/2025_BEGINNER_GROUP0_null.txt?v=1783513437372",
        "spb_product_id": 1,
        "spb_flag": "BEGINNER_GROUP0",
    },
    {
        "key": "intermediate",
        "title": "小中组",
        "subtitle": "Intermediate Group(G3-G4)",
        "status": "available",
        "prefix": "SPB个人赛冠军词库-小中组",
        "source_count": 1900,
        "source_file": "spb_individual_intermediate_g3_g4_words.json",
        "source_url": "https://cdn.spbcn.org/DownloadFile/en_word_thesaurus/2025_BEGINNER_GROUP1_null.txt?v=1783513802350",
        "spb_product_id": 2,
        "spb_flag": "BEGINNER_GROUP1",
    },
    {
        "key": "advanced",
        "title": "小高组",
        "subtitle": "Advanced Group(G5-G6)",
        "status": "available",
        "prefix": "SPB个人赛冠军词库-小高组",
        "source_count": 2300,
        "source_file": "spb_individual_advanced_g5_g6_words.json",
        "source_url": "https://cdn.spbcn.org/DownloadFile/en_word_thesaurus/2025_BEGINNER_GROUP2_null.txt?v=1783513810146",
        "spb_product_id": 3,
        "spb_flag": "BEGINNER_GROUP2",
    },
    {
        "key": "middle",
        "title": "初中组",
        "subtitle": "Middle School(G7-G9)",
        "status": "available",
        "prefix": "SPB个人赛冠军词库-初中组",
        "source_count": 3400,
        "source_file": "spb_individual_middle_g7_g9_words.json",
        "source_url": "https://cdn.spbcn.org/DownloadFile/en_word_thesaurus/2025_BEGINNER_GROUP3_null.txt?v=1783514057432",
        "spb_product_id": 4,
        "spb_flag": "BEGINNER_GROUP3",
    },
    {
        "key": "high",
        "title": "高中组",
        "subtitle": "High School(G10-G12)",
        "status": "available",
        "prefix": "SPB个人赛冠军词库-高中组",
        "source_count": 3300,
        "source_file": "spb_individual_high_g10_g12_words.json",
        "source_url": "https://cdn.spbcn.org/DownloadFile/en_word_thesaurus/2025_BEGINNER_GROUP4_null.txt?v=1783514147067",
        "spb_product_id": 5,
        "spb_flag": "BEGINNER_GROUP4",
    },
    {
        "key": "origin",
        "title": "词源单词",
        "subtitle": "Language Origin",
        "status": "available",
        "prefix": "SPB个人赛冠军词库-词源单词",
        "source_count": 120,
        "source_file": "spb_individual_language_origin_words.json",
        "source_url": "https://cdn.spbcn.org/DownloadFile/en_word_thesaurus/2025_Asian_Languages_null.txt?v=1783514166982",
        "spb_product_id": 6,
        "spb_flag": "Asian_Languages",
    },
    {
        "key": "challenge",
        "title": "挑战词汇",
        "subtitle": "Challenge Words",
        "status": "available",
        "prefix": "SPB个人赛冠军词库-挑战词汇",
        "source_count": 1300,
        "source_file": "spb_individual_challenge_words.json",
        "source_url": "https://cdn.spbcn.org/DownloadFile/en_word_thesaurus/2025_CHALLENGE_WORDS_null.txt?v=1783514205665",
        "spb_product_id": 7,
        "spb_flag": "CHALLENGE_WORDS",
    },
]


SPB_RESERVE_PACKAGE_WORD_BANK_GROUPS = [
    {
        "key": "reserve-beginner",
        "title": "小初组开心备赛",
        "subtitle": "Beginner Happy Prep",
        "status": "available",
        "prefix": "SPB全方位备赛套餐-小初组开心备赛",
        "spb_product_id": 10,
        "spb_flag": "Beginner_Group0_happy",
    },
    {
        "key": "reserve-intermediate",
        "title": "小中组快乐备赛",
        "subtitle": "Intermediate Fun Prep",
        "status": "available",
        "prefix": "SPB全方位备赛套餐-小中组快乐备赛",
        "spb_product_id": 11,
        "spb_flag": "Beginner_Group1_fun",
    },
    {
        "key": "reserve-advanced",
        "title": "小高组轻松备赛",
        "subtitle": "Advanced Relaxed Prep",
        "status": "available",
        "prefix": "SPB全方位备赛套餐-小高组轻松备赛",
        "spb_product_id": 12,
        "spb_flag": "Beginner_Group2_relaxed",
    },
    {
        "key": "reserve-middle",
        "title": "初中组超速备赛",
        "subtitle": "Middle School Speed Prep",
        "status": "available",
        "prefix": "SPB全方位备赛套餐-初中组超速备赛",
        "spb_product_id": 13,
        "spb_flag": "Beginner_Group4_speeding",
    },
    {
        "key": "reserve-perfect",
        "title": "课外组完美备赛",
        "subtitle": "Perfect Extra Prep",
        "status": "available",
        "prefix": "SPB全方位备赛套餐-课外组完美备赛",
        "spb_product_id": 14,
        "spb_flag": "Beginner_Group_perfect",
    },
]


SPB_BABY_WORD_BANK_GROUPS = [
    {
        "key": "baby",
        "title": "SPBCNxBABY词库",
        "subtitle": "SPBCN x BABY",
        "status": "available",
        "prefix": "SPB-SPBCNxBABY词库",
        "spb_product_id": 36,
        "spb_flag": "baby_thesaurus",
    }
]


SPB_TEAM_WORD_BANK_GROUPS = [
    {
        "key": "team-beginner-basic",
        "title": "小学组基础",
        "subtitle": "Beginner Group(G1-G2)",
        "status": "available",
        "prefix": "SPB团队赛冠军词库-小学组基础",
        "source_count": 1299,
        "source_url": "https://cdn.spbcn.org/DownloadFile/en_word_thesaurus/2025_BEGINNER_GROUP0_null.txt?v=1783238815790",
        "spb_flag": "BEGINNER_GROUP",
    },
    {
        "key": "team-beginner-intermediate",
        "title": "小学组进阶",
        "subtitle": "Intermediate Group(G3-G4)",
        "status": "available",
        "prefix": "SPB团队赛冠军词库-小学组进阶",
        "source_count": 1900,
        "source_url": "https://cdn.spbcn.org/DownloadFile/en_word_thesaurus/2025_BEGINNER_GROUP1_null.txt?v=1783238948991",
        "spb_flag": "BEGINNER_GROUP",
    },
    {
        "key": "team-beginner-advanced",
        "title": "小学组高阶",
        "subtitle": "Advanced Group(G5-G6)",
        "status": "available",
        "prefix": "SPB团队赛冠军词库-小学组高阶",
        "source_count": 2300,
        "source_url": "https://cdn.spbcn.org/DownloadFile/en_word_thesaurus/2025_BEGINNER_GROUP2_null.txt?v=1783238959379",
        "spb_flag": "BEGINNER_GROUP",
    },
    {
        "key": "team-beginner-core",
        "title": "小学组核心词汇",
        "subtitle": "Core Words",
        "status": "available",
        "prefix": "SPB团队赛冠军词库-小学组核心词汇",
        "source_count": 500,
        "source_url": "https://cdn.spbcn.org/DownloadFile/en_word_thesaurus/2025_BEGINNER_GROUP0_true.txt?v=1783238968660",
        "spb_flag": "BEGINNER_GROUP",
    },
    {
        "key": "team-middle-all",
        "title": "初中组全部词汇",
        "subtitle": "Middle School(G7-G9)",
        "status": "available",
        "prefix": "SPB团队赛冠军词库-初中组全部词汇",
        "source_count": 3398,
        "source_url": "https://cdn.spbcn.org/DownloadFile/en_word_thesaurus/2025_Itso_middle_School_null.txt?v=1783238979259",
        "spb_flag": "Itso_middle_School",
    },
    {
        "key": "team-middle-core",
        "title": "初中组核心词汇",
        "subtitle": "Middle School Core Words",
        "status": "available",
        "prefix": "SPB团队赛冠军词库-初中组核心词汇",
        "source_count": 1045,
        "source_url": "https://cdn.spbcn.org/DownloadFile/en_word_thesaurus/2025_Itso_middle_School_true.txt?v=1783239007475",
        "spb_flag": "Itso_middle_School",
    },
    {
        "key": "team-high-all",
        "title": "高中组全部词汇",
        "subtitle": "High School(G10-G12)",
        "status": "available",
        "prefix": "SPB团队赛冠军词库-高中组全部词汇",
        "source_count": 3298,
        "source_url": "https://cdn.spbcn.org/DownloadFile/en_word_thesaurus/2025_Itso_high_School_null.txt?v=1783239024165",
        "spb_flag": "Itso_high_School",
    },
    {
        "key": "team-origin-all",
        "title": "词源单词",
        "subtitle": "Asian Languages",
        "status": "available",
        "prefix": "SPB团队赛冠军词库-词源单词",
        "source_count": 120,
        "source_url": "https://cdn.spbcn.org/DownloadFile/en_word_thesaurus/2025_Asian_Languages_null.txt?v=1783239042794",
        "spb_flag": "Asian_Languages",
    },
]


SPB_WORD_BANK_COLLECTIONS = [
    {
        "key": "individual",
        "name": "个人赛冠军词库",
        "subtitle": "Champion Word Bank for Individual Competitions",
        "source_type": "individual_champion_thesaurus",
        "groups": SPB_INDIVIDUAL_WORD_BANK_GROUPS,
    },
    {
        "key": "reserve",
        "name": "全方位备赛套餐",
        "subtitle": "SPB Practice Packages",
        "source_type": "reserve_package",
        "groups": SPB_RESERVE_PACKAGE_WORD_BANK_GROUPS,
    },
    {
        "key": "team",
        "name": "团体赛冠军词库",
        "subtitle": "Team Competition Word Banks",
        "source_type": "itso_champion_thesaurus",
        "groups": SPB_TEAM_WORD_BANK_GROUPS,
        "sync_note": "已记录 SPB 公共团队赛词库源，可直接按组同步。",
    },
    {
        "key": "baby",
        "name": "SPBCNxBABY词库",
        "subtitle": "SPBCN x BABY Word Bank",
        "source_type": "baby_thesaurus",
        "groups": SPB_BABY_WORD_BANK_GROUPS,
    },
    {
        "key": "toefl",
        "name": "国际考试（托福）",
        "subtitle": "TOEFL Word Banks",
        "source_type": "toefl_thesaurus",
        "groups": [],
        "sync_note": "小程序公开产品接口暂未返回托福词库；拿到公共源文件或授权后会出现在这里。",
    },
    {
        "key": "ielts",
        "name": "国际考试（雅思）",
        "subtitle": "IELTS Word Banks",
        "source_type": "ielts_thesaurus",
        "groups": [],
        "sync_note": "小程序公开产品接口暂未返回雅思词库；拿到公共源文件或授权后会出现在这里。",
    },
]


def spb_collection_by_key(collection_key: str | None) -> dict[str, Any]:
    key = str(collection_key or "").strip() or "individual"
    return next(
        (collection for collection in SPB_WORD_BANK_COLLECTIONS if collection["key"] == key),
        SPB_WORD_BANK_COLLECTIONS[0],
    )


def spb_collection_group_by_keys(collection_key: str | None, group_key: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    collection = spb_collection_by_key(collection_key)
    key = str(group_key or "").strip()
    group = next((item for item in collection.get("groups", []) if item["key"] == key), None)
    if not group:
        raise HTTPException(status_code=404, detail="没有找到这个 SPB 词库组")
    return collection, group


def serialize_spb_word_bank_collection(db: Session, collection: dict[str, Any]) -> dict[str, Any]:
    groups = [serialize_spb_word_bank_group(db, group) for group in collection.get("groups", [])]
    total_count = sum(int(group.get("total_count") or 0) for group in groups)
    list_count = sum(int(group.get("list_count") or 0) for group in groups)
    cached_source_count = sum(int(group.get("cached_source_count") or 0) for group in groups)
    return {
        "key": collection["key"],
        "name": collection["name"],
        "subtitle": collection["subtitle"],
        "source_type": collection.get("source_type"),
        "sync_note": collection.get("sync_note") or "",
        "total_count": total_count,
        "list_count": list_count,
        "cached_source_count": cached_source_count,
        "groups": groups,
    }


def spb_payload(db: Session, collection_key: str | None = None) -> dict[str, Any]:
    active_collection = spb_collection_by_key(collection_key)
    collections = [serialize_spb_word_bank_collection(db, collection) for collection in SPB_WORD_BANK_COLLECTIONS]
    active_payload = next(
        (collection for collection in collections if collection["key"] == active_collection["key"]),
        collections[0],
    )
    return {
        "collection": active_payload,
        "collections": collections,
        "groups": active_payload.get("groups", []),
        "active_sync_job": spb_active_sync_job_for_collection(active_collection["key"]),
    }


def update_spb_sync_job(job_id: str, **changes) -> None:
    with IMAGE_SYNC_LOCK:
        job = SPB_SYNC_JOBS.get(job_id)
        if not job:
            return
        job.update(changes)
        job["updated_at"] = datetime.utcnow().isoformat()


def spb_sync_job_snapshot(job_id: str) -> dict[str, Any] | None:
    with IMAGE_SYNC_LOCK:
        job = SPB_SYNC_JOBS.get(job_id)
        return dict(job) if job else None


def spb_active_sync_job_for_collection(collection_key: str | None) -> dict[str, Any] | None:
    key = str(collection_key or "individual").strip() or "individual"
    with IMAGE_SYNC_LOCK:
        active_jobs = [
            dict(job)
            for job in SPB_SYNC_JOBS.values()
            if str(job.get("collection") or "") == key and job.get("status") in {"queued", "running"}
        ]
    if not active_jobs:
        return None
    return max(active_jobs, key=lambda job: str(job.get("updated_at") or job.get("created_at") or ""))


def spb_sync_response(db: Session, job: dict[str, Any]) -> dict[str, Any]:
    response = spb_payload(db, str(job.get("collection") or "individual"))
    response["job"] = dict(job)
    response["message"] = job.get("message") or ""
    response["source"] = job.get("source") or ""
    return response


def run_spb_sync_job(
    job_id: str,
    collection_key: str,
    group_key: str,
    rows: list[dict[str, Any]],
    source_name: str,
) -> None:
    db = SessionLocal()
    try:
        collection, group = spb_collection_group_by_keys(collection_key, group_key)
        total = len(rows)
        prepared_rows: list[dict[str, Any]] = []
        update_spb_sync_job(
            job_id,
            status="running",
            stage="preparing",
            total=total,
            processed=0,
            current_word="",
            message=f"正在准备 {group['title']}，共 {total} 个单词。",
        )
        for start in range(0, total, SPB_SYNC_BATCH_SIZE):
            batch = rows[start : start + SPB_SYNC_BATCH_SIZE]
            first_word = str(batch[0].get("word") or "") if batch else ""
            update_spb_sync_job(
                job_id,
                current_word=first_word,
                message=f"正在补充详情和下载小程序音频：{len(prepared_rows)} / {total}",
            )
            prepared_batch = asyncio.run(prepare_spb_rows_with_local_audio(batch, group, db=db))
            prepared_rows.extend(prepared_batch)
            update_spb_sync_job(
                job_id,
                processed=len(prepared_rows),
                text_detail_count=sum(1 for row in prepared_rows if spb_has_text_fields(row)),
                local_audio_count=sum(spb_local_audio_count(row) for row in prepared_rows),
                message=f"正在补充详情和下载小程序音频：{len(prepared_rows)} / {total}",
            )

        update_spb_sync_job(
            job_id,
            status="running",
            stage="importing",
            current_word="",
            message="正在写入数据库并按 500 个单词拆分分表。",
        )
        text_detail_count = sum(1 for row in prepared_rows if spb_has_text_fields(row))
        local_audio_count = sum(spb_local_audio_count(row) for row in prepared_rows)
        word_ids, split_lists = import_spb_word_bank_rows(db, group, prepared_rows)
        if word_ids:
            start_enrichment_thread(word_ids, include_images=False)
        message = f"已同步 {group['title']}：{len(word_ids)} 个单词，{len(split_lists)} 个分表。"
        if text_detail_count:
            message += f" 已写入详情字段 {text_detail_count} 个。"
        elif not spb_miniprogram_authorization_configured():
            message += " 服务器未配置 SPB 小程序授权，暂时只能导入词表，不能读取小程序详情字段。"
        if local_audio_count:
            message += f" 已保存小程序音频 {local_audio_count} 个到本地。"
        update_spb_sync_job(
            job_id,
            status="complete",
            stage="complete",
            processed=total,
            current_word="",
            word_count=len(word_ids),
            list_count=len(split_lists),
            text_detail_count=text_detail_count,
            local_audio_count=local_audio_count,
            message=message,
            source=source_name,
            collection=collection["key"],
            key=group["key"],
        )
    except Exception as exc:
        db.rollback()
        update_spb_sync_job(
            job_id,
            status="failed",
            stage="failed",
            current_word="",
            message=f"同步失败：{str(exc)[:240]}",
        )
    finally:
        db.close()


@app.get("/api/vue/spb")
def vue_spb_api(collection: str = Query(default="individual"), db: Session = Depends(get_db)):
    return spb_payload(db, collection)


@app.post("/api/vue/spb/sync")
async def vue_spb_sync_api(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    collection_key = str(payload.get("collection") or "individual").strip() or "individual"
    group_key = str(payload.get("key") or "").strip()
    collection, group = spb_collection_group_by_keys(collection_key, group_key)
    if group.get("status") == "locked":
        raise HTTPException(status_code=400, detail="这组还在小程序里锁定，暂时不能同步")

    rows, source_path = load_spb_source_rows(group)
    if not rows:
        detail = (
            f"{group['title']} 缺少小程序授权，服务器也没有这组公共源词库。请先配置 SPB 小程序授权后再同步。"
            if not spb_miniprogram_authorization_configured()
            else f"{group['title']} 已尝试调用小程序接口，但没有拿到可导入词库；请确认小程序账号已开通这组词库。"
        )
        raise HTTPException(
            status_code=404,
            detail=detail,
        )

    job_id = uuid4().hex
    job = {
        "id": job_id,
        "collection": collection["key"],
        "key": group["key"],
        "title": group["title"],
        "status": "queued",
        "stage": "queued",
        "total": len(rows),
        "processed": 0,
        "word_count": 0,
        "list_count": 0,
        "text_detail_count": 0,
        "local_audio_count": 0,
        "current_word": "",
        "source": source_path.name,
        "message": f"已创建同步任务：{group['title']}，共 {len(rows)} 个单词。",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    with IMAGE_SYNC_LOCK:
        SPB_SYNC_JOBS[job_id] = job
    Thread(
        target=run_spb_sync_job,
        args=(job_id, collection["key"], group["key"], rows, source_path.name),
        daemon=True,
    ).start()
    return spb_sync_response(db, job)


@app.get("/api/vue/spb/sync/{job_id}")
def vue_spb_sync_status_api(job_id: str, db: Session = Depends(get_db)):
    job = spb_sync_job_snapshot(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="同步任务不存在或已过期")
    if job.get("status") in {"complete", "failed"}:
        return spb_sync_response(db, job)
    return {
        "job": job,
        "message": job.get("message") or "",
        "source": job.get("source") or "",
    }


@app.post("/api/vue/spb/backfill-details")
async def vue_spb_backfill_details_api(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    collection_key = str(payload.get("collection") or "individual").strip() or "individual"
    group_key = str(payload.get("key") or "").strip()
    collection, group = spb_collection_group_by_keys(collection_key, group_key)
    words = spb_words_for_group(db, group)
    if not words:
        raise HTTPException(status_code=404, detail="这组还没有同步到 SpeakEasy，先同步词库后再补全详情。")

    force_audio_download = bool(payload.get("force_audio_download") or payload.get("forceAudioDownload"))
    if collection["key"] == "individual" and str(group.get("source_url") or "").strip():
        force_audio_download = True
    resource_applied = apply_word_resources(db, words, include_image=False)
    source_rows, _source_path = load_spb_source_rows(group)
    source_rows_by_word = {normalize_resource_word(row.get("word")): row for row in source_rows}
    if force_audio_download:
        repair_words = [
            word
            for word in words
            if source_rows_by_word.get(normalize_resource_word(word.word))
        ]
        queued_ids = [word.id for word in repair_words]
        remaining_after_batch = 0
    else:
        repair_words = [
            word
            for word in words
            if word_needs_spb_detail_repair(word)
            or word_needs_spb_group_audio_repair(
                word,
                group,
                source_rows_by_word.get(normalize_resource_word(word.word)),
            )
        ]
        queued_ids = [word.id for word in repair_words[:SPB_DETAIL_BACKFILL_BATCH_LIMIT]]
        remaining_after_batch = max(len(repair_words) - len(queued_ids), 0)
    if queued_ids:
        job_id = uuid4().hex
        action_label = "强制下载小程序音频并更新" if force_audio_download else "检查"
        job = {
            "id": job_id,
            "collection": collection["key"],
            "key": group["key"],
            "title": group["title"],
            "status": "queued",
            "stage": "detail_backfill",
            "total": len(queued_ids),
            "processed": 0,
            "word_count": len(queued_ids),
            "list_count": int(group.get("list_count") or 0),
            "text_detail_count": 0,
            "local_audio_count": 0,
            "current_word": "",
            "source": "spb-public-detail-audio",
            "force_audio_download": force_audio_download,
            "message": (
                f"已从公共资源表补齐 {resource_applied} 个；准备{action_label} {len(queued_ids)} 个单词的 SPB 详情和音频来源。"
            ),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        with IMAGE_SYNC_LOCK:
            SPB_SYNC_JOBS[job_id] = job
        start_spb_detail_backfill_thread(
            queued_ids,
            job_id=job_id,
            collection_key=collection["key"],
            group_key=group["key"],
            force_audio_download=force_audio_download,
        )
        response = spb_sync_response(db, job)
        response["queued_detail_count"] = len(queued_ids)
        response["remaining_detail_count"] = remaining_after_batch
        response["resource_applied_count"] = resource_applied
        if remaining_after_batch:
            response["message"] += f" 还有 {remaining_after_batch} 个会留到下一批，避免一次任务过大。"
        return response

    response = spb_payload(db, collection["key"])
    response["message"] = f"已从公共资源表补齐 {resource_applied} 个；这组 SPB 详情、定义/例句音频和单词音频来源没有明显缺口。"
    response["queued_detail_count"] = len(queued_ids)
    response["remaining_detail_count"] = remaining_after_batch
    response["resource_applied_count"] = resource_applied
    return response


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
    answer_word_id: int | None,
    wrong_date: str,
) -> dict[str, Any]:
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")

    wrong_date_value = parse_wrong_date(wrong_date)
    correction_mode = bool(wrong_date_value)
    words = (
        correction_challenge_words(db, word_list_id, wrong_date_value)
        if correction_mode
        else get_words_for_list(db, word_list_id)
    )
    progress = get_or_create_challenge_progress(db, word_list_id)
    total = len(words)
    answer_feedback = None

    if action == "reset":
        progress.current_index = 0
        progress.completed_count = 0
        session_correct = 0
        session_wrong = 0
    elif total:
        progress.current_index = min(max(progress.current_index, 0), max(total - 1, 0))
        requested_index = None
        if answer_word_id:
            requested_index = next((index for index, word in enumerate(words) if word.id == answer_word_id), None)
        if requested_index is not None:
            progress.current_index = requested_index
        current_word = (
            None
            if answer_word_id and requested_index is None
            else words[progress.current_index] if 0 <= progress.current_index < total else None
        )
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
            record_wrong_word(db, current_word.id, wrong_date_value if correction_mode else None)
        if action == "known":
            if current_word:
                clear_wrong_word_if_passed(db, current_word.id, wrong_date_value)
        if action in {"known", "wrong"}:
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
            if correction_mode:
                progress.completed_count = 0
                if action == "known":
                    remaining_total = len(correction_challenge_words(db, word_list_id, wrong_date_value))
                    progress.current_index = min(progress.current_index, max(remaining_total - 1, 0))
                else:
                    progress.current_index = (progress.current_index + 1) % total
            else:
                progress.completed_count = min(progress.completed_count + 1, total)
                if progress.completed_count < total:
                    progress.current_index = (progress.current_index + 1) % total
                else:
                    progress.current_index = max(total - 1, 0)

    db.add(progress)
    db.commit()
    session_correct = max(session_correct, 0)
    session_wrong = max(session_wrong, 0)
    if correction_mode:
        daily_count = max(session_correct + len(correction_challenge_words(db, word_list_id, wrong_date_value)), 1)
        start_count = 0
    else:
        daily_count = min(max(daily_count, 1), 500)
        start_count = max(start_count, 0)
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

    correction_mode = bool(wrong_date_value)
    words = (
        correction_challenge_words(db, word_list_id, wrong_date_value)
        if correction_mode
        else get_words_for_list(db, word_list_id)
    )
    progress = get_or_create_challenge_progress(db, word_list_id)
    total = len(words)
    if correction_mode:
        if restart:
            progress.current_index = 0
        progress.completed_count = 0
        progress.current_index = min(max(progress.current_index, 0), max(total - 1, 0))
    elif restart:
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

    session_correct = max(session_correct, 0)
    session_wrong = max(session_wrong, 0)
    if correction_mode:
        start_count = 0
        daily_remaining = total
        daily_total = session_correct + daily_remaining
        daily_count = max(daily_total, 1)
        daily_target = daily_total
        session_answered = session_correct
        daily_done = session_correct
        is_daily_complete = daily_remaining == 0
        challenge_summary = {
            "completed": session_correct,
            "total": daily_total,
            "percent": round((session_correct / daily_total) * 100) if daily_total else 100,
            "is_complete": is_daily_complete,
            "completed_rounds": progress.completed_rounds or 0,
        }
    else:
        start_count = progress.completed_count if start_count is None else start_count
        start_count = min(max(start_count, 0), total)
        daily_count = min(max(daily_count, 1), max(total, 1))
        daily_target = min(total, start_count + daily_count)
        daily_total = max(0, daily_target - start_count)
        session_answered = min(session_correct + session_wrong, daily_total) if daily_total else 0
        daily_done = session_answered
        daily_remaining = max(0, daily_total - session_answered)
        is_daily_complete = bool(total and daily_total and session_answered >= daily_total)
        challenge_summary = challenge_state(db, word_list)

    current_word = None if is_daily_complete or not words else words[progress.current_index]
    if not correction_mode and progress.completed_count >= total:
        current_word = None
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

    accuracy_attempts = session_correct + session_wrong if correction_mode else session_answered
    today_challenge = {
        "daily_count": daily_count,
        "start_count": start_count,
        "target": daily_target,
        "done": daily_done,
        "total": daily_total,
        "percent": round((daily_done / daily_total) * 100) if daily_total else 100,
        "is_complete": is_daily_complete,
        "all_complete": bool(daily_remaining == 0) if correction_mode else bool(total and progress.completed_count >= total),
        "correct": session_correct,
        "wrong": session_wrong,
        "answered": session_answered,
        "remaining": daily_remaining,
        "accuracy": round((session_correct / accuracy_attempts) * 100) if accuracy_attempts else 0,
    }
    return {
        "word_list": {"id": word_list.id, "name": word_list.name},
        "current_word": serialize_challenge_word(current_word),
        "progress": {
            "current_index": progress.current_index,
            "completed_count": progress.completed_count,
            "completed_rounds": progress.completed_rounds,
        },
        "challenge": challenge_summary,
        "today_challenge": today_challenge,
        "challenge_audio_sources": challenge_audio_sources,
        "challenge_image_url": challenge_image_url,
        "masked_example": masked_example,
        "wrong_date": wrong_date_value.isoformat() if wrong_date_value else None,
        "correction_mode": correction_mode,
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
        "audio_issue": word.audio_issue,
        "image_issue": word.image_issue,
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
        "english_definition_audio_url": word.english_definition_audio_url,
        "chinese_definition": word.chinese_definition,
        "english_example": word.english_example,
        "english_example_audio_url": word.english_example_audio_url,
        "image_url": word.image_url,
        "american_audio_url": word.american_audio_url,
        "british_audio_url": word.british_audio_url,
        "has_audio": has_audio,
        "has_playable_audio": has_playable_audio,
        "audio_issue": word.audio_issue,
        "image_issue": word.image_issue,
    }


def serialize_word_list_group(db: Session, group: WordListGroup) -> dict[str, Any]:
    word_lists = [
        word_list
        for word_list in regular_word_lists(db)
        if word_list.group_id == group.id
    ]
    total_words = sum(
        db.scalar(select(func.count(WordListItem.id)).where(WordListItem.word_list_id == word_list.id)) or 0
        for word_list in word_lists
    )
    return {
        "id": group.id,
        "name": group.name,
        "display_order": group.display_order,
        "list_count": len(word_lists),
        "word_count": int(total_words),
        "list_ids": [word_list.id for word_list in word_lists],
    }


def serialize_word_list_group_brief(group: WordListGroup | None) -> dict[str, Any] | None:
    if not group:
        return None
    return {"id": group.id, "name": group.name}


def serialize_word_list_card(card: dict[str, Any], group: WordListGroup | None = None) -> dict[str, Any]:
    word_list = card["list"]
    cover_word = card.get("cover_word")
    return {
        "list": {
            "id": word_list.id,
            "name": word_list.name,
            "display_order": word_list.display_order,
            "group_id": word_list.group_id,
            "group": serialize_word_list_group_brief(group),
        },
        "count": card["count"],
        "cover_word": serialize_word(cover_word) if cover_word else None,
        "challenge": card["challenge"],
    }


def word_list_group_map(db: Session) -> dict[int, WordListGroup]:
    return {group.id: group for group in word_list_groups(db)}


def lists_payload(db: Session) -> dict[str, Any]:
    groups = [serialize_word_list_group(db, group) for group in word_list_groups(db)]
    groups_by_id = {group["id"]: group for group in groups}
    model_groups = word_list_group_map(db)
    cards: list[dict[str, Any]] = []
    for index, word_list in enumerate(regular_word_lists(db), start=1):
        group = model_groups.get(word_list.group_id or 0)
        card = serialize_word_list_card(word_list_card(db, word_list), group)
        card["sequence"] = index
        if word_list.group_id and word_list.group_id in groups_by_id:
            card["list"]["group"] = {
                "id": word_list.group_id,
                "name": groups_by_id[word_list.group_id]["name"],
            }
        cards.append(card)
    return {"groups": groups, "cards": cards}


def spb_word_lists_for_group(db: Session, group: dict[str, Any]) -> list[WordList]:
    prefix = str(group["prefix"])
    group_model = db.scalar(select(WordListGroup).where(WordListGroup.name == prefix).limit(1))
    conditions = [WordList.name == prefix, WordList.name.like(f"{prefix}-%")]
    if group_model:
        conditions.append(WordList.group_id == group_model.id)
    return db.scalars(
        select(WordList)
        .where(or_(*conditions))
        .order_by(WordList.sequence_offset.asc(), WordList.name.asc(), WordList.id.asc())
    ).all()


def spb_words_for_group(db: Session, group: dict[str, Any]) -> list[Word]:
    word_lists = spb_word_lists_for_group(db, group)
    list_ids = [word_list.id for word_list in word_lists]
    if not list_ids:
        return []
    return db.scalars(
        select(Word)
        .join(WordListItem, WordListItem.word_id == Word.id)
        .where(WordListItem.word_list_id.in_(list_ids))
        .distinct()
        .order_by(Word.word.asc(), Word.id.asc())
    ).all()


def spb_missing_detail_count(db: Session, group: dict[str, Any]) -> int:
    word_lists = spb_word_lists_for_group(db, group)
    list_ids = [word_list.id for word_list in word_lists]
    if not list_ids:
        return 0
    return int(
        db.scalar(
            select(func.count(func.distinct(Word.id)))
            .join(WordListItem, WordListItem.word_id == Word.id)
            .where(
                WordListItem.word_list_id.in_(list_ids),
                or_(
                    Word.phonetic.is_(None),
                    Word.phonetic == "",
                    Word.part_of_speech.is_(None),
                    Word.part_of_speech == "",
                    Word.english_definition.is_(None),
                    Word.english_definition == "",
                    Word.english_example.is_(None),
                    Word.english_example == "",
                ),
            )
        )
        or 0
    )


def serialize_spb_word_bank_group(db: Session, group: dict[str, Any]) -> dict[str, Any]:
    word_lists = spb_word_lists_for_group(db, group)
    cards = [serialize_word_list_card(word_list_card(db, word_list)) for word_list in word_lists]
    total_count = sum(int(card.get("count") or 0) for card in cards)
    synced = total_count > 0
    cached_source_count = count_spb_cached_source_words(group)
    source_url_configured = bool(str(group.get("source_url") or "").strip())
    authorization_configured = spb_miniprogram_authorization_configured()
    sync_ready = (
        group.get("status") != "locked"
        and not synced
        and (authorization_configured or cached_source_count > 0 or source_url_configured)
    )
    sync_note = spb_group_sync_note(group, synced, cached_source_count, authorization_configured)
    return {
        "key": group["key"],
        "title": group["title"],
        "subtitle": group["subtitle"],
        "status": "synced" if synced else group.get("status", "available"),
        "source_count": group.get("source_count") or cached_source_count or None,
        "cached_source_count": cached_source_count,
        "source_url_configured": source_url_configured,
        "sync_ready": sync_ready,
        "sync_note": sync_note,
        "total_count": total_count,
        "list_count": len(cards),
        "cards": cards,
    }


def spb_source_dirs() -> list[Path]:
    return [MEDIA_DIR / "spb", BASE_DIR.parent / "spb_sources"]


def spb_cached_source_path(group: dict[str, Any]) -> Path:
    source_file = str(group.get("source_file") or "").strip()
    if not source_file:
        return Path("")
    for source_dir in spb_source_dirs():
        path = source_dir / source_file
        if path.exists():
            return path
    return Path(source_file)


def count_spb_cached_source_words(group: dict[str, Any]) -> int:
    path = spb_cached_source_path(group)
    if not path.exists():
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    return len(normalize_spb_word_rows(extract_spb_word_values(payload), group))


def spb_miniprogram_authorization_configured() -> bool:
    return bool((settings.spb_miniprogram_authorization or "").strip())


def spb_group_sync_note(
    group: dict[str, Any],
    synced: bool,
    cached_source_count: int,
    authorization_configured: bool,
) -> str:
    if synced:
        return "已同步到 SpeakEasy。"
    if group.get("status") == "locked":
        return "这组仍在小程序里锁定，暂时不能同步。"
    if str(group.get("source_url") or "").strip():
        return "已配置 SPB 公共源词库，可直接同步。"
    if authorization_configured:
        return "可从小程序接口同步；如果接口返回空结果，会自动尝试本地公共源词库。"
    if cached_source_count:
        return f"已找到本地公共源词库，可导入 {cached_source_count} 个单词。"
    return "缺少小程序授权，且本地没有这组公共源词库；请先配置服务器小程序授权。"


SPB_MINIPROGRAM_WORD_FILE_ENDPOINT = "wordThesaurus/spbcnInfoFile"
SPB_MINIPROGRAM_WORD_FILE_BY_ID_ENDPOINT = "wordThesaurus/spbcnInfoByIdFile"
SPB_MINIPROGRAM_WORD_DETAIL_ENDPOINT = "wordThesaurus/getWordInfo"
SPB_TEXT_IMPORT_FIELDS = ("phonetic", "part_of_speech", "english_definition", "chinese_definition", "english_example")


def spb_miniprogram_api_url(path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    return f"{settings.spb_miniprogram_api_base.rstrip('/')}/{path.lstrip('/')}"


def spb_miniprogram_headers(include_auth: bool = True) -> dict[str, str]:
    headers = {
        "Terminal": "WECHAT_APP",
        "content-type": "application/x-www-form-urlencoded;charset=UTF-8;",
    }
    authorization = (settings.spb_miniprogram_authorization or "").strip()
    if include_auth and authorization:
        headers["Authorization"] = authorization
    return headers


def spb_miniprogram_get(path: str, params: dict[str, Any], *, require_auth: bool = True) -> Any:
    if require_auth and not (settings.spb_miniprogram_authorization or "").strip():
        return None
    try:
        response = httpx.get(
            spb_miniprogram_api_url(path),
            params=params,
            headers=spb_miniprogram_headers(include_auth=require_auth),
            timeout=settings.spb_miniprogram_timeout_seconds,
            follow_redirects=True,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    if not isinstance(payload, dict) or int(payload.get("code") or 0) not in {200, 2014}:
        return None
    return payload.get("data")


async def spb_miniprogram_get_async(path: str, params: dict[str, Any], *, require_auth: bool = True) -> Any:
    if require_auth and not (settings.spb_miniprogram_authorization or "").strip():
        return None
    try:
        async with httpx.AsyncClient(
            timeout=settings.spb_miniprogram_timeout_seconds,
            headers=spb_miniprogram_headers(include_auth=require_auth),
            follow_redirects=True,
        ) as client:
            response = await client.get(spb_miniprogram_api_url(path), params=params)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    if not isinstance(payload, dict) or int(payload.get("code") or 0) not in {200, 2014}:
        return None
    return payload.get("data")


def spb_source_payload_from_api_data(data: Any) -> Any:
    if not data:
        return None
    if isinstance(data, dict):
        if extract_spb_word_values(data):
            return data
        for key in ("url", "fileUrl", "file_url", "jsonUrl", "json_url", "downloadUrl", "download_url"):
            value = str(data.get(key) or "").strip()
            if value:
                return spb_download_source_payload(value)
        return data
    if isinstance(data, str):
        value = data.strip()
        if value.startswith(("http://", "https://")):
            return spb_download_source_payload(value)
        try:
            return json.loads(value)
        except ValueError:
            return None
    return data


def spb_download_source_payload(source_url: str) -> Any:
    if not source_url.startswith(("http://", "https://")):
        source_url = spb_miniprogram_api_url(source_url)
    try:
        response = httpx.get(
            source_url,
            timeout=settings.spb_miniprogram_timeout_seconds,
            follow_redirects=True,
        )
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError):
        return None


def fetch_spb_source_rows_from_miniprogram(group: dict[str, Any]) -> tuple[list[dict[str, Any]], Path]:
    flag = str(group.get("spb_flag") or "").strip()
    product_id = group.get("spb_product_id")
    candidates: list[tuple[str, dict[str, Any], str]] = []
    if flag:
        candidates.append(
            (
                SPB_MINIPROGRAM_WORD_FILE_ENDPOINT,
                {"terminal": "WECHAT", "code": flag},
                f"mini-program-{flag}.json",
            )
        )
    if product_id:
        candidates.append(
            (
                SPB_MINIPROGRAM_WORD_FILE_BY_ID_ENDPOINT,
                {"terminal": "WECHAT", "id": product_id},
                f"mini-program-product-{product_id}.json",
            )
        )

    for endpoint, params, source_name in candidates:
        payload = spb_source_payload_from_api_data(spb_miniprogram_get(endpoint, params))
        rows = normalize_spb_word_rows(extract_spb_word_values(payload), group)
        if rows:
            return rows, Path(source_name)
    return [], Path(f"mini-program-{flag or product_id or group.get('key')}.json")


def fetch_spb_source_rows_from_url(group: dict[str, Any]) -> tuple[list[dict[str, Any]], Path]:
    source_url = str(group.get("source_url") or "").strip()
    if not source_url:
        return [], Path("")
    payload = spb_download_source_payload(source_url)
    rows = normalize_spb_word_rows(extract_spb_word_values(payload), group)
    if rows:
        source_name = Path(urlparse(source_url).path).name or f"{group.get('key') or 'source'}.json"
        return rows, Path(source_name)
    return [], Path(source_url)


def load_spb_source_rows(group: dict[str, Any]) -> tuple[list[dict[str, Any]], Path]:
    url_rows, url_source = fetch_spb_source_rows_from_url(group)
    if url_rows:
        return url_rows, url_source

    api_rows, api_source = fetch_spb_source_rows_from_miniprogram(group)
    if api_rows:
        return api_rows, api_source

    path = spb_cached_source_path(group)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        return normalize_spb_word_rows(extract_spb_word_values(payload), group), path
    return [], path


def extract_spb_word_values(payload: Any) -> list[Any]:
    if isinstance(payload, dict):
        for key in ("words", "spellGroup", "spell_group", "items", "list"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                return extract_spb_word_values(value)
        values: list[Any] = []
        for value in payload.values():
            nested = extract_spb_word_values(value)
            if nested:
                values.extend(nested)
        return values
    if isinstance(payload, list):
        return payload
    return []


def normalize_spb_word_values(values: list[Any]) -> list[str]:
    return [row["word"] for row in normalize_spb_word_rows(values, {})]


def normalize_spb_word_rows(values: list[Any], group: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in values:
        raw = spb_word_text_from_source_value(value)
        word, alternate_spellings = split_spb_word_spellings(raw)
        if not is_valid_spb_word_text(word):
            continue
        normalized = normalize_resource_word(word).casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        row: dict[str, Any] = {
            "word": word,
            "spb_word_id": spb_word_id_from_source_value(value),
            "spb_product_flag": group.get("spb_flag"),
            "spb_product_id": group.get("spb_product_id"),
            "spb_kernel": value.get("kernel") if isinstance(value, dict) else None,
        }
        if alternate_spellings:
            row["alternate_spellings"] = alternate_spellings
        row.update(spb_audio_urls_from_payload(value))
        text_fields = spb_text_fields_from_payload(value)
        if text_fields:
            row.update(text_fields)
            row["spb_text_source"] = "spb-public-source"
        rows.append(row)
    return rows


SPB_WORD_PUNCTUATION = {" ", "'", "’", "-", "‐", "‑", "–", "—", "."}


def normalize_spb_source_word_text(value: Any) -> str:
    text = " ".join(str(value or "").strip().split())
    return unicodedata.normalize("NFC", text)[:128]


def split_spb_word_spellings(value: Any) -> tuple[str, str | None]:
    text = normalize_spb_source_word_text(value)
    if "/" not in text and "／" not in text:
        return text, None

    candidates = [
        normalize_spb_source_word_text(part)
        for part in re.split(r"[/／]+", text)
        if normalize_spb_source_word_text(part)
    ]
    valid_spellings = [part for part in candidates if is_valid_spb_word_text(part)]
    if not valid_spellings:
        return text, None
    return valid_spellings[0], "\n".join(valid_spellings[1:]) or None


def is_valid_spb_word_text(word: str) -> bool:
    if not word:
        return False
    has_letter = False
    first_letter_seen = False
    for char in word:
        category = unicodedata.category(char)
        if category.startswith("L"):
            has_letter = True
            first_letter_seen = True
            continue
        if category in {"Mn", "Mc"}:
            continue
        if char in SPB_WORD_PUNCTUATION:
            if not first_letter_seen:
                return False
            continue
        return False
    return has_letter


def spb_word_text_from_source_value(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("word", "name", "spell", "text", "vocabulary"):
            if value.get(key):
                return value.get(key)
        return None
    return value


def spb_word_id_from_source_value(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in ("id", "wordId", "word_id", "spellingId", "spellId"):
        if value.get(key) is not None:
            return str(value.get(key)).strip() or None
    return None


def spb_find_first_field(payload: Any, field_names: tuple[str, ...]) -> str | None:
    targets = {field_name.lower() for field_name in field_names}
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.lower() in targets:
                text = spb_clean_field_text(value)
                if text:
                    return text
        for value in payload.values():
            nested = spb_find_first_field(value, field_names)
            if nested:
                return nested
    elif isinstance(payload, list):
        for value in payload:
            nested = spb_find_first_field(value, field_names)
            if nested:
                return nested
    return None


def spb_find_preferred_field(payload: Any, field_names: tuple[str, ...]) -> str | None:
    for field_name in field_names:
        text = spb_find_first_field(payload, (field_name,))
        if text:
            return text
    return None


def spb_word_compound_audio_url(payload: Any, field_names: tuple[str, ...]) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key, value in payload.items():
        if key.lower() in {"wordcompoundaudio", "word_compound_audio", "compoundaudio", "compound_audio"}:
            return spb_find_preferred_field(value, field_names)
    return None


def spb_clean_field_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = html_to_text(value)
    elif isinstance(value, (int, float)):
        text = str(value)
    elif isinstance(value, list):
        parts = [spb_clean_field_text(item) for item in value]
        text = "\n".join(part for part in parts if part)
    elif isinstance(value, dict):
        for key in (
            "text",
            "value",
            "content",
            "definition",
            "meaning",
            "translation",
            "sentence",
            "example",
            "en",
            "cn",
            "zh",
            "name",
        ):
            if value.get(key) is not None:
                text = spb_clean_field_text(value.get(key))
                if text:
                    return text
        parts = [spb_clean_field_text(item) for item in value.values()]
        text = "\n".join(part for part in parts if part)
    else:
        text = str(value)
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text).strip()
    return text[:4000] if text else None


def spb_audio_urls_from_payload(payload: Any) -> dict[str, str]:
    us_url = spb_find_first_field(
        payload,
        (
            "purl",
            "american_audio_url",
            "americanAudioUrl",
            "usAudioUrl",
            "us_audio_url",
            "usaudio",
            "usUrl",
            "us_url",
            "purl",
        ),
    )
    gb_url = spb_find_first_field(
        payload,
        (
            "british_audio_url",
            "britishAudioUrl",
            "ukAudioUrl",
            "uk_audio_url",
            "ukaudio",
            "ukUrl",
            "uk_url",
        ),
    )
    generic_url = spb_find_first_field(payload, ("audioUrl", "audio_url", "audio", "voiceUrl", "voice_url", "durl"))
    example_url = spb_example_audio_url_from_payload(payload)
    definition_url = spb_definition_audio_url_from_payload(payload)
    result: dict[str, str] = {}
    if spb_looks_like_audio_url(example_url):
        result["english_example_audio_url"] = example_url
    if spb_looks_like_audio_url(definition_url):
        result["english_definition_audio_url"] = definition_url
    if spb_looks_like_audio_url(us_url):
        if spb_looks_like_example_audio_url(us_url):
            result.setdefault("english_example_audio_url", us_url)
        else:
            result["american_audio_url"] = us_url
    elif spb_looks_like_audio_url(generic_url):
        if spb_looks_like_example_audio_url(generic_url):
            result.setdefault("english_example_audio_url", generic_url)
        else:
            result["american_audio_url"] = generic_url
    if spb_looks_like_audio_url(gb_url):
        if spb_looks_like_example_audio_url(gb_url):
            result.setdefault("english_example_audio_url", gb_url)
        else:
            result["british_audio_url"] = gb_url
    return result


def spb_definition_audio_url_from_payload(payload: Any) -> str | None:
    compound_url = spb_word_compound_audio_url(payload, ("definitionUrl", "definition_url"))
    if spb_looks_like_audio_url(compound_url) and not spb_looks_like_example_audio_url(compound_url):
        return compound_url

    specific_url = spb_find_preferred_field(
        payload,
        (
            "definitionUrl",
            "DefinitionUrl",
            "definition_url",
            "english_definition_audio_url",
            "englishDefinitionAudioUrl",
            "enDefinitionAudioUrl",
            "definitionAudioUrl",
            "definition_audio_url",
            "definitionVoiceUrl",
            "definition_voice_url",
            "definitionSoundUrl",
            "definition_sound_url",
            "definitionMp3",
            "definition_mp3",
            "definitionMp3Url",
            "definition_mp3_url",
            "definitionAudio",
            "definition_audio",
            "meaningAudioUrl",
            "meaning_audio_url",
            "meaningAudio",
            "meaning_audio",
            "defAudioUrl",
            "def_audio_url",
        ),
    )
    if spb_looks_like_audio_url(specific_url) and not spb_looks_like_example_audio_url(specific_url):
        return specific_url

    lexicon_url = spb_find_preferred_field(payload, ("durl",))
    if spb_looks_like_audio_url(lexicon_url) and not spb_looks_like_example_audio_url(lexicon_url):
        return lexicon_url

    if isinstance(payload, dict):
        for key, value in payload.items():
            lower_key = key.lower()
            is_definition_key = any(marker in lower_key for marker in ("definition", "meaning", "defaudio"))
            is_other_field = any(marker in lower_key for marker in ("example", "sentence", "chinese", "translation"))
            if is_definition_key and not is_other_field:
                nested_url = spb_find_first_field(
                    value,
                    ("audioUrl", "audio_url", "audio", "voiceUrl", "voice_url", "soundUrl", "sound_url", "url"),
                )
                if spb_looks_like_audio_url(nested_url) and not spb_looks_like_example_audio_url(nested_url):
                    return nested_url
            nested = spb_definition_audio_url_from_payload(value)
            if nested:
                return nested
    elif isinstance(payload, list):
        for value in payload:
            nested = spb_definition_audio_url_from_payload(value)
            if nested:
                return nested
    return None


def spb_example_audio_url_from_payload(payload: Any) -> str | None:
    compound_url = spb_word_compound_audio_url(payload, ("sentenceUrl", "sentence_url"))
    if spb_looks_like_audio_url(compound_url):
        return compound_url

    specific_url = spb_find_preferred_field(
        payload,
        (
            "sentenceUrl",
            "SentenceUrl",
            "sentence_url",
            "english_example_audio_url",
            "englishExampleAudioUrl",
            "enExampleAudioUrl",
            "exampleAudioUrl",
            "example_audio_url",
            "exampleVoiceUrl",
            "example_voice_url",
            "exampleSoundUrl",
            "example_sound_url",
            "exampleMp3",
            "example_mp3",
            "exampleMp3Url",
            "example_mp3_url",
            "exampleAudio",
            "example_audio",
            "sentenceAudioUrl",
            "sentence_audio_url",
            "sentenceAudio",
            "sentence_audio",
            "sentenceVoiceUrl",
            "sentence_voice_url",
            "sentenceSoundUrl",
            "sentence_sound_url",
            "sentenceMp3",
            "sentence_mp3",
            "sentenceMp3Url",
            "sentence_mp3_url",
            "enSentenceAudioUrl",
            "en_sentence_audio_url",
            "sentAudioUrl",
            "sent_audio_url",
        ),
    )
    if spb_looks_like_audio_url(specific_url):
        return specific_url

    lexicon_url = spb_find_preferred_field(payload, ("eurl",))
    if spb_looks_like_audio_url(lexicon_url):
        return lexicon_url

    if isinstance(payload, dict):
        for key, value in payload.items():
            lower_key = key.lower()
            if "example" in lower_key or "sentence" in lower_key:
                nested_url = spb_find_first_field(
                    value,
                    ("audioUrl", "audio_url", "audio", "voiceUrl", "voice_url", "soundUrl", "sound_url", "url"),
                )
                if spb_looks_like_audio_url(nested_url):
                    return nested_url
            nested = spb_example_audio_url_from_payload(value)
            if nested:
                return nested
    elif isinstance(payload, list):
        for value in payload:
            nested = spb_example_audio_url_from_payload(value)
            if nested:
                return nested
    return None


def spb_looks_like_audio_url(value: str | None) -> bool:
    if not value:
        return False
    lower_value = value.lower()
    return lower_value.startswith(("http://", "https://")) and any(
        marker in lower_value
        for marker in (".mp3", ".m4a", ".wav", ".aac", ".ogg", "/audio", "audio", "voice", "sound")
    )


def spb_looks_like_example_audio_url(value: str | None) -> bool:
    if not spb_looks_like_audio_url(value):
        return False
    lower_value = str(value or "").lower()
    return any(
        marker in lower_value
        for marker in (
            "example",
            "sentence",
            "sent_",
            "sent-",
            "/sent",
            "ensentence",
            "en_sentence",
            "exampleaudio",
            "sentenceaudio",
        )
    )


def spb_local_audio_count(row: dict[str, Any]) -> int:
    return sum(
        1
        for field in ("american_audio_url", "british_audio_url", "english_definition_audio_url", "english_example_audio_url")
        if is_local_audio_url(row.get(field))
    )


def spb_text_fields_from_payload(payload: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    phonetic = spb_find_preferred_field(
        payload,
        (
            "phonetic",
            "phoneticSymbol",
            "phonetic_symbol",
            "phone",
            "soundmark",
            "soundMark",
            "pronunciation",
            "pron",
            "ipa",
            "usphone",
            "usPhone",
            "ukphone",
            "ukPhone",
            "音标",
            "英标",
        ),
    )
    part_of_speech = spb_find_preferred_field(
        payload,
        (
            "part_of_speech",
            "partOfSpeech",
            "pos",
            "speech",
            "wordClass",
            "word_class",
            "wordType",
            "property",
            "cixing",
            "词性",
        ),
    )
    english_definition = spb_find_preferred_field(
        payload,
        (
            "Definition",
            "english_definition",
            "englishDefinition",
            "enDefinition",
            "definitionEn",
            "enExplain",
            "englishExplain",
            "enMeaning",
            "englishMeaning",
            "definition",
            "meaning",
            "英文释义",
        ),
    )
    chinese_definition = spb_find_preferred_field(
        payload,
        (
            "chinese_definition",
            "chineseDefinition",
            "cnDefinition",
            "zhDefinition",
            "definitionCn",
            "cnExplain",
            "zhExplain",
            "chineseExplain",
            "translation",
            "trans",
            "chinese",
            "meaningCn",
            "cnMeaning",
            "zhMeaning",
            "中文释义",
            "中文",
            "释义",
        ),
    )
    english_example = spb_find_preferred_field(
        payload,
        (
            "Sentence",
            "sentence",
            "sentenceEn",
            "sentences",
            "english_example",
            "englishExample",
            "enExample",
            "exampleEn",
            "exampleSentence",
            "example",
            "examples",
            "例句",
        ),
    )
    if phonetic:
        result["phonetic"] = phonetic
    if part_of_speech:
        result["part_of_speech"] = part_of_speech
    if english_definition:
        result["english_definition"] = english_definition
    if chinese_definition:
        result["chinese_definition"] = chinese_definition
    if english_example:
        result["english_example"] = english_example
    return result


def spb_has_text_fields(row: dict[str, Any]) -> bool:
    return any(str(row.get(field) or "").strip() for field in SPB_TEXT_IMPORT_FIELDS)


def spb_group_audio_rule_key(group: dict[str, Any], rule_version: str = SPB_WORD_AUDIO_SOURCE_RULE_VERSION) -> str:
    group_key = str(group.get("spb_flag") or group.get("key") or "example").strip()
    source_url = str(group.get("source_url") or "").strip()
    source_stem = Path(urlparse(source_url).path).stem if source_url else ""
    source_version_match = re.search(r"(?:\?|&)v=([^&]+)", source_url)
    source_version = source_version_match.group(1) if source_version_match else ""
    return "-".join(part for part in (group_key, source_stem, source_version, rule_version) if part)


def spb_word_audio_source_key(group: dict[str, Any]) -> str:
    return f"spb-{spb_group_audio_rule_key(group, SPB_WORD_AUDIO_SOURCE_RULE_VERSION)}"


def spb_detail_audio_source_key_prefix(group: dict[str, Any], kind: str) -> str:
    return f"spb-{kind}-{spb_group_audio_rule_key(group, SPB_DETAIL_AUDIO_SOURCE_RULE_VERSION)}"


def spb_example_audio_source_key(group: dict[str, Any], word: str | None, example: str | None, audio_url: str | None) -> str:
    text = re.sub(r"\s+", " ", (example or "").strip())
    source_url = str(audio_url or "").strip()
    text = "|".join(part for part in (text, source_url) if part) or str(word or "").strip()
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return f"{spb_detail_audio_source_key_prefix(group, 'example')}-{digest}"


def spb_definition_audio_source_key(
    group: dict[str, Any],
    word: str | None,
    definition: str | None,
    audio_url: str | None,
) -> str:
    text = re.sub(r"\s+", " ", (definition or "").strip())
    source_url = str(audio_url or "").strip()
    text = "|".join(part for part in (text, source_url) if part) or str(word or "").strip()
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return f"{spb_detail_audio_source_key_prefix(group, 'definition')}-{digest}"


def local_audio_url_matches_source_key(audio_url: str | None, source_key: str | None) -> bool:
    if not audio_url or not source_key:
        return False
    safe_source = (re.sub(r"[^a-zA-Z0-9_-]+", "-", source_key.lower()).strip("-") or "source")[:80]
    return safe_source in Path(str(audio_url)).name.lower()


def reusable_local_example_audio_for_word(
    db: Session | None,
    word_text: str | None,
    incoming_example: str | None,
    incoming_source: str | None = None,
    expected_source_key: str | None = None,
) -> tuple[str, str | None] | None:
    if db is None:
        return None
    resource = get_word_resource(db, word_text)
    if not resource:
        return None
    audio_url = (resource.english_example_audio_url or "").strip()
    if not is_local_audio_url(audio_url):
        return None
    if expected_source_key and not local_audio_url_matches_source_key(audio_url, expected_source_key):
        return None
    normalized_incoming = re.sub(r"\s+", " ", (incoming_example or "").strip())
    normalized_existing = re.sub(r"\s+", " ", (resource.english_example or "").strip())
    if normalized_incoming and normalized_existing and normalized_incoming != normalized_existing:
        return None
    if audio_source_priority(resource.english_example_audio_source, audio_url) < audio_source_priority(incoming_source, audio_url):
        return None
    return audio_url, resource.english_example_audio_source


def reusable_local_definition_audio_for_word(
    db: Session | None,
    word_text: str | None,
    incoming_definition: str | None,
    incoming_source: str | None = None,
    expected_source_key: str | None = None,
) -> tuple[str, str | None] | None:
    if db is None:
        return None
    resource = get_word_resource(db, word_text)
    if not resource:
        return None
    audio_url = (resource.english_definition_audio_url or "").strip()
    if not is_local_audio_url(audio_url):
        return None
    if expected_source_key and not local_audio_url_matches_source_key(audio_url, expected_source_key):
        return None
    normalized_incoming = re.sub(r"\s+", " ", (incoming_definition or "").strip())
    normalized_existing = re.sub(r"\s+", " ", (resource.english_definition or "").strip())
    if normalized_incoming and normalized_existing and normalized_incoming != normalized_existing:
        return None
    if audio_source_priority(resource.english_definition_audio_source, audio_url) < audio_source_priority(incoming_source, audio_url):
        return None
    return audio_url, resource.english_definition_audio_source


async def prepare_spb_rows_with_local_audio(
    rows: list[dict[str, Any]],
    group: dict[str, Any],
    db: Session | None = None,
    *,
    force_audio_download: bool = False,
) -> list[dict[str, Any]]:
    if not rows:
        return rows

    semaphore = asyncio.Semaphore(5)

    async def prepare(row: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            prepared = dict(row)
            forced_download_count = 0
            if spb_miniprogram_authorization_configured() and prepared.get("spb_word_id"):
                detail = await fetch_spb_word_detail_from_miniprogram(prepared, group)
                if isinstance(detail, dict):
                    detail_text_fields = spb_text_fields_from_payload(detail)
                    if detail_text_fields:
                        prepared["spb_text_source"] = "spb-miniprogram"
                    detail_audio_fields = spb_audio_urls_from_payload(detail)
                    if detail_audio_fields.get("american_audio_url"):
                        prepared["american_audio_url_source"] = "spb-miniprogram"
                    if detail_audio_fields.get("british_audio_url"):
                        prepared["british_audio_url_source"] = "spb-miniprogram"
                    if detail_audio_fields.get("english_definition_audio_url"):
                        prepared["english_definition_audio_url_source"] = "spb-miniprogram"
                    if detail_audio_fields.get("english_example_audio_url"):
                        prepared["english_example_audio_url_source"] = "spb-miniprogram"
                    for key, value in {**detail_audio_fields, **detail_text_fields}.items():
                        if value:
                            prepared[key] = value
            for accent, field_name in (("us", "american_audio_url"), ("gb", "british_audio_url")):
                audio_url = str(prepared.get(field_name) or "").strip()
                if not audio_url or is_local_audio_url(audio_url):
                    continue
                incoming_source = str(prepared.get(f"{field_name}_source") or "spb-miniprogram")
                if not force_audio_download:
                    reusable_audio = reusable_local_audio_for_word(db, prepared.get("word"), accent, incoming_source)
                    if reusable_audio:
                        prepared[field_name] = reusable_audio[0]
                        prepared[f"{field_name}_source"] = reusable_audio[1] or incoming_source
                        continue
                try:
                    local_url = await store_audio_candidate(
                        prepared["word"],
                        accent,
                        spb_word_audio_source_key(group),
                        audio_url,
                        AUDIO_DIR,
                        force_download=force_audio_download,
                    )
                except Exception:
                    local_url = None
                if local_url:
                    prepared[field_name] = local_url
                    prepared[f"{field_name}_source"] = "spb-miniprogram"
                    if force_audio_download:
                        forced_download_count += 1
            example_audio_url = str(prepared.get("english_example_audio_url") or "").strip()
            if example_audio_url and not is_local_audio_url(example_audio_url):
                incoming_source = str(prepared.get("english_example_audio_url_source") or "spb-miniprogram")
                example_source_key = spb_example_audio_source_key(
                    group,
                    prepared.get("word"),
                    prepared.get("english_example"),
                    example_audio_url,
                )
                reusable_example_audio = None
                if not force_audio_download:
                    reusable_example_audio = reusable_local_example_audio_for_word(
                        db,
                        prepared.get("word"),
                        prepared.get("english_example"),
                        incoming_source,
                        expected_source_key=example_source_key,
                    )
                if reusable_example_audio:
                    prepared["english_example_audio_url"] = reusable_example_audio[0]
                    prepared["english_example_audio_url_source"] = reusable_example_audio[1] or incoming_source
                else:
                    try:
                        local_url = await store_audio_candidate(
                            prepared["word"],
                            "example",
                            example_source_key,
                            example_audio_url,
                            AUDIO_DIR,
                            force_download=force_audio_download,
                        )
                    except Exception:
                        local_url = None
                    if local_url:
                        prepared["english_example_audio_url"] = local_url
                        prepared["english_example_audio_url_source"] = "spb-miniprogram"
                        if force_audio_download:
                            forced_download_count += 1
            definition_audio_url = str(prepared.get("english_definition_audio_url") or "").strip()
            if definition_audio_url and not is_local_audio_url(definition_audio_url):
                incoming_source = str(prepared.get("english_definition_audio_url_source") or "spb-miniprogram")
                definition_source_key = spb_definition_audio_source_key(
                    group,
                    prepared.get("word"),
                    prepared.get("english_definition"),
                    definition_audio_url,
                )
                reusable_definition_audio = None
                if not force_audio_download:
                    reusable_definition_audio = reusable_local_definition_audio_for_word(
                        db,
                        prepared.get("word"),
                        prepared.get("english_definition"),
                        incoming_source,
                        expected_source_key=definition_source_key,
                    )
                if reusable_definition_audio:
                    prepared["english_definition_audio_url"] = reusable_definition_audio[0]
                    prepared["english_definition_audio_url_source"] = reusable_definition_audio[1] or incoming_source
                else:
                    try:
                        local_url = await store_audio_candidate(
                            prepared["word"],
                            "definition",
                            definition_source_key,
                            definition_audio_url,
                            AUDIO_DIR,
                            force_download=force_audio_download,
                        )
                    except Exception:
                        local_url = None
                    if local_url:
                        prepared["english_definition_audio_url"] = local_url
                        prepared["english_definition_audio_url_source"] = "spb-miniprogram"
                        if force_audio_download:
                            forced_download_count += 1
            if forced_download_count:
                prepared["_spb_force_downloaded_audio_count"] = forced_download_count
            return prepared

    return await asyncio.gather(*(prepare(row) for row in rows))


async def fetch_spb_word_detail_from_miniprogram(row: dict[str, Any], group: dict[str, Any]) -> Any:
    word_id = str(row.get("spb_word_id") or "").strip()
    if not word_id:
        return None
    flag = str(row.get("spb_product_flag") or group.get("spb_flag") or "").strip()
    product_id = row.get("spb_product_id") or group.get("spb_product_id")
    candidates: list[dict[str, Any]] = []
    if flag:
        candidates.append({"id": word_id, "productFlag": flag})
    if product_id:
        candidates.append({"id": word_id, "productId": product_id})
    candidates.append({"id": word_id})
    for params in candidates:
        data = await spb_miniprogram_get_async(SPB_MINIPROGRAM_WORD_DETAIL_ENDPOINT, params)
        if data:
            return data
    return None


def all_spb_word_bank_groups() -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for collection in SPB_WORD_BANK_COLLECTIONS:
        groups.extend(collection.get("groups", []))
    return groups


def spb_group_matches_name(group: dict[str, Any], name: str | None) -> bool:
    prefix = str(group.get("prefix") or "").strip()
    text_value = str(name or "").strip()
    return bool(prefix and (text_value == prefix or text_value.startswith(f"{prefix}-")))


def spb_group_from_word_list(db: Session, word_list: WordList | None) -> dict[str, Any] | None:
    if not word_list:
        return None
    group_name = None
    if word_list.group_id:
        word_list_group = db.get(WordListGroup, word_list.group_id)
        group_name = word_list_group.name if word_list_group else None
    for group in all_spb_word_bank_groups():
        if spb_group_matches_name(group, word_list.name) or spb_group_matches_name(group, group_name):
            return group
    return None


def spb_candidate_groups_for_word(db: Session, word: Word, list_id: int | None = None) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []

    def add_group(group: dict[str, Any] | None) -> None:
        if group and all(existing.get("prefix") != group.get("prefix") for existing in groups):
            groups.append(group)

    if list_id:
        add_group(spb_group_from_word_list(db, db.get(WordList, list_id)))

    word_lists = db.scalars(
        select(WordList)
        .join(WordListItem, WordListItem.word_list_id == WordList.id)
        .where(WordListItem.word_id == word.id)
        .order_by(WordList.id.asc())
    ).all()
    for word_list in word_lists:
        add_group(spb_group_from_word_list(db, word_list))
    return groups


def find_spb_source_row_for_word(group: dict[str, Any], word_text: str | None) -> dict[str, Any] | None:
    normalized_word = normalize_resource_word(word_text)
    if not normalized_word:
        return None
    rows, _source_path = load_spb_source_rows(group)
    return next((row for row in rows if normalize_resource_word(row.get("word")) == normalized_word), None)


async def apply_spb_details_to_word(
    db: Session,
    word: Word,
    *,
    list_id: int | None = None,
    preferred_group: dict[str, Any] | None = None,
    force_audio_download: bool = False,
) -> bool:
    changed = False
    candidate_groups: list[dict[str, Any]] = []
    if preferred_group:
        candidate_groups.append(preferred_group)
    for group in spb_candidate_groups_for_word(db, word, list_id):
        if all(existing.get("prefix") != group.get("prefix") for existing in candidate_groups):
            candidate_groups.append(group)

    for group in candidate_groups:
        row = find_spb_source_row_for_word(group, word.word)
        if not row:
            continue
        prepared = dict(row)
        if spb_miniprogram_authorization_configured() and prepared.get("spb_word_id"):
            detail = await fetch_spb_word_detail_from_miniprogram(prepared, group)
            if isinstance(detail, dict):
                detail_text_fields = spb_text_fields_from_payload(detail)
                if detail_text_fields:
                    prepared["spb_text_source"] = "spb-miniprogram"
                detail_audio_fields = spb_audio_urls_from_payload(detail)
                if detail_audio_fields.get("american_audio_url"):
                    prepared["american_audio_url_source"] = "spb-miniprogram"
                if detail_audio_fields.get("british_audio_url"):
                    prepared["british_audio_url_source"] = "spb-miniprogram"
                if detail_audio_fields.get("english_definition_audio_url"):
                    prepared["english_definition_audio_url_source"] = "spb-miniprogram"
                if detail_audio_fields.get("english_example_audio_url"):
                    prepared["english_example_audio_url_source"] = "spb-miniprogram"
                prepared.update(detail_audio_fields)
                prepared.update(detail_text_fields)

        prepared_rows = await prepare_spb_rows_with_local_audio(
            [prepared],
            group,
            db=db,
            force_audio_download=force_audio_download,
        )
        prepared = prepared_rows[0] if prepared_rows else prepared
        if apply_spb_text_fields_to_word(word, prepared):
            changed = True
        if apply_imported_local_audio(word, prepared):
            changed = True
        if int(prepared.get("_spb_force_downloaded_audio_count") or 0):
            changed = True
        if clear_misclassified_spb_audio_from_resource(db, word, prepared):
            changed = True
        if changed:
            remember_word_resource(
                db,
                word,
                american_audio_source=prepared.get("american_audio_url_source"),
                british_audio_source=prepared.get("british_audio_url_source"),
                english_definition_audio_source=prepared.get("english_definition_audio_url_source"),
                english_example_audio_source=prepared.get("english_example_audio_url_source"),
                override_text=bool(prepared.get("spb_text_source")),
                override_media=bool(
                    prepared.get("american_audio_url_source")
                    or prepared.get("british_audio_url_source")
                    or prepared.get("english_definition_audio_url_source")
                    or prepared.get("english_example_audio_url_source")
                ),
                commit=False,
            )
            return True
    return changed


async def spb_audio_options_for_word(db: Session, word: Word, accent: str, list_id: int | None = None) -> list[dict[str, str]]:
    field_name = "british_audio_url" if accent == "gb" else "american_audio_url"
    accent_label = "英式" if accent == "gb" else "美式"
    options: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for group in spb_candidate_groups_for_word(db, word, list_id):
        row = find_spb_source_row_for_word(group, word.word)
        if not row:
            continue
        prepared = dict(row)
        if spb_miniprogram_authorization_configured() and prepared.get("spb_word_id"):
            detail = await fetch_spb_word_detail_from_miniprogram(prepared, group)
            if isinstance(detail, dict):
                detail_audio_fields = spb_audio_urls_from_payload(detail)
                if detail_audio_fields.get("american_audio_url"):
                    prepared["american_audio_url_source"] = "spb-miniprogram"
                if detail_audio_fields.get("british_audio_url"):
                    prepared["british_audio_url_source"] = "spb-miniprogram"
                prepared.update(detail_audio_fields)

        prepared_rows = await prepare_spb_rows_with_local_audio([prepared], group, db=db)
        prepared = prepared_rows[0] if prepared_rows else prepared
        audio_url = local_import_audio_url(prepared.get(field_name))
        if audio_url and audio_url not in seen_urls:
            seen_urls.add(audio_url)
            options.append(
                {
                    "label": f"SPB小程序音频 · {accent_label} · {group.get('title') or '词库'}",
                    "url": audio_url,
                    "source": "spb-miniprogram",
                }
            )
    return options


def apply_spb_text_fields_to_word(word: Word, row: dict[str, Any]) -> bool:
    changed = False
    prefer_spb_detail = row.get("spb_text_source") == "spb-miniprogram"
    for field in ("phonetic", "part_of_speech"):
        value = str(row.get(field) or "").strip()
        if value and (prefer_spb_detail or not (getattr(word, field, None) or "").strip()):
            if getattr(word, field, None) == value:
                continue
            setattr(word, field, value)
            changed = True

    for field, lock_field in (
        ("english_definition", "english_definition_locked"),
        ("english_example", "english_example_locked"),
    ):
        value = str(row.get(field) or "").strip()
        if value and (prefer_spb_detail or not (getattr(word, field, None) or "").strip()):
            if getattr(word, field, None) == value and getattr(word, lock_field, False):
                continue
            incoming_definition_audio_url = local_import_audio_url(row.get("english_definition_audio_url"))
            incoming_example_audio_url = local_import_audio_url(row.get("english_example_audio_url"))
            if field == "english_definition" and getattr(word, field, None) != value and not incoming_definition_audio_url:
                word.english_definition_audio_url = None
            if field == "english_example" and getattr(word, field, None) != value and not incoming_example_audio_url:
                word.english_example_audio_url = None
            setattr(word, field, value)
            setattr(word, lock_field, True)
            changed = True

    chinese_value = str(row.get("chinese_definition") or "").strip()
    if chinese_value:
        chinese_value = (
            naturalize_chinese_definition(word.word, word.english_definition or row.get("english_definition"), chinese_value)
            or chinese_value
        )
    if chinese_value and (
        prefer_spb_detail
        or not (word.chinese_definition or "").strip()
        or should_refresh_chinese_definition(word.word, word.chinese_definition, word.english_definition)
    ):
        if word.chinese_definition == chinese_value and word.chinese_definition_locked:
            return changed
        word.chinese_definition = chinese_value
        word.chinese_definition_locked = True
        changed = True
    return changed


def import_spb_word_bank_rows(db: Session, group: dict[str, Any], source_rows: list[dict[str, Any]]) -> tuple[list[int], list[WordList]]:
    chunk_size = 500
    base_name = clean_list_name(str(group["prefix"]))
    rows = [
        {
            **row,
            "row_number": index + 1,
            "note": f"SPB {group['title']} {group['subtitle']}",
        }
        for index, row in enumerate(source_rows)
    ]
    word_ids: list[int] = []
    split_lists: list[WordList] = []
    if len(rows) > chunk_size:
        split_group = get_or_create_word_list_group_by_name(db, base_name)
        for chunk_index in range(0, len(rows), chunk_size):
            chunk_number = (chunk_index // chunk_size) + 1
            word_list = get_or_create_spb_word_list(
                db,
                f"{base_name}-{chunk_number}",
                group_id=split_group.id,
                sequence_offset=chunk_index,
            )
            clear_word_list_items(db, word_list.id)
            word_list.group_id = split_group.id
            word_list.sequence_offset = chunk_index
            db.add(word_list)
            db.commit()
            split_lists.append(word_list)
            word_ids.extend(import_rows(rows[chunk_index : chunk_index + chunk_size], db, word_list))
    else:
        word_list = get_or_create_word_list_by_name(db, base_name)
        clear_word_list_items(db, word_list.id)
        word_list.sequence_offset = 0
        db.add(word_list)
        db.commit()
        split_lists.append(word_list)
        word_ids.extend(import_rows(rows, db, word_list))
    return word_ids, split_lists


def is_wrong_word_list(word_list: WordList | None) -> bool:
    return bool(word_list and str(word_list.name or "").startswith("生词本 "))


def challenge_word_display_list(
    db: Session,
    word_id: int,
    preferred_list: WordList | None = None,
) -> WordList | None:
    if preferred_list and not is_wrong_word_list(preferred_list):
        return preferred_list
    row = db.execute(
        select(WordList)
        .join(WordListItem, WordListItem.word_list_id == WordList.id)
        .where(WordListItem.word_id == word_id)
        .where(WordList.name.not_like("生词本 %"))
        .order_by(WordList.display_order.asc(), WordList.sequence_offset.asc(), WordList.id.asc())
        .limit(1)
    ).first()
    return row[0] if row else preferred_list


def challenge_day_word_item(
    word: Word,
    *,
    status: str,
    daily_wrong_ids: set[int],
    corrected_wrong_ids: set[int],
    correct_count: int = 0,
    wrong_count: int = 0,
    word_list: WordList | None = None,
) -> dict[str, Any]:
    return {
        "id": word.id,
        "word": word.word,
        "status": status,
        "was_wrong": bool((wrong_count or 0) > 0 or word.id in daily_wrong_ids),
        "corrected": word.id in corrected_wrong_ids,
        "correct_count": max(int(correct_count or 0), 0),
        "wrong_count": max(int(wrong_count or 0), 0),
        "word_list_id": word_list.id if word_list else None,
        "word_list_name": word_list.name if word_list else "",
        "image_url": word.image_url,
        "phonetic": word.phonetic,
        "part_of_speech": word.part_of_speech,
        "english_definition": word.english_definition,
        "chinese_definition": word.chinese_definition,
    }


def challenge_day_wrong_word_counts(db: Session, challenge_date: date) -> dict[int, int]:
    return {
        int(word_id): max(int(wrong_count or 0), 1)
        for word_id, wrong_count in db.execute(
            select(WrongWord.word_id, WrongWord.wrong_count).where(WrongWord.wrong_date == challenge_date)
        ).all()
    }


def challenge_day_attempt_items(
    db: Session,
    challenge_date: date,
    daily_wrong_ids: set[int],
    corrected_wrong_ids: set[int],
) -> list[dict[str, Any]]:
    day_start = datetime.combine(challenge_date, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    attempt_rows = db.execute(
        select(ChallengeSpellingAttempt, Word, WordList)
        .join(Word, Word.id == ChallengeSpellingAttempt.word_id)
        .outerjoin(WordList, WordList.id == ChallengeSpellingAttempt.word_list_id)
        .where(ChallengeSpellingAttempt.created_at >= day_start)
        .where(ChallengeSpellingAttempt.created_at < day_end)
        .order_by(ChallengeSpellingAttempt.created_at.asc(), ChallengeSpellingAttempt.id.asc())
    ).all()
    summaries: dict[tuple[int, int | None], dict[str, Any]] = {}
    display_list_cache: dict[tuple[int, int | None], WordList | None] = {}
    for attempt, word, attempt_list in attempt_rows:
        cache_key = (word.id, attempt_list.id if attempt_list else None)
        if cache_key not in display_list_cache:
            display_list_cache[cache_key] = challenge_word_display_list(db, word.id, attempt_list)
        word_list = display_list_cache[cache_key]
        summary_key = (word.id, word_list.id if word_list else None)
        summary = summaries.get(summary_key)
        if not summary:
            summary = {
                "word": word,
                "word_list": word_list,
                "correct_count": 0,
                "wrong_count": 0,
                "last_result": "correct",
            }
            summaries[summary_key] = summary
        if attempt.is_correct:
            summary["correct_count"] += 1
            summary["last_result"] = "correct"
        else:
            summary["wrong_count"] += 1
            summary["last_result"] = "wrong"
    return [
        challenge_day_word_item(
            summary["word"],
            status=summary["last_result"],
            daily_wrong_ids=daily_wrong_ids,
            corrected_wrong_ids=corrected_wrong_ids,
            correct_count=summary["correct_count"],
            wrong_count=summary["wrong_count"],
            word_list=summary["word_list"],
        )
        for summary in summaries.values()
    ]


def challenge_calendar_day_payload(db: Session, challenge_date: date) -> dict:
    daily_wrong_ids = challenge_day_wrong_word_ids(db, challenge_date)
    corrected_wrong_ids = challenge_day_corrected_wrong_word_ids(db, challenge_date, daily_wrong_ids)
    pending_wrong_ids = daily_wrong_ids - corrected_wrong_ids
    wrong_word_list = get_wrong_word_list(db, challenge_date)
    wrong_count_by_word = challenge_day_wrong_word_counts(db, challenge_date)
    stat = db.scalar(select(ChallengeDailyStat).where(ChallengeDailyStat.stat_date == challenge_date))
    detail_rows = db.execute(
        select(ChallengeDailyWord, Word, WordList)
        .join(Word, Word.id == ChallengeDailyWord.word_id)
        .outerjoin(WordList, WordList.id == ChallengeDailyWord.word_list_id)
        .where(ChallengeDailyWord.challenge_date == challenge_date)
        .order_by(ChallengeDailyWord.updated_at.asc(), ChallengeDailyWord.id.asc())
    ).all()

    words = [
        challenge_day_word_item(
            word,
            status=detail.last_result,
            daily_wrong_ids=daily_wrong_ids,
            corrected_wrong_ids=corrected_wrong_ids,
            correct_count=detail.correct_count,
            wrong_count=detail.wrong_count,
            word_list=challenge_word_display_list(db, word.id, word_list),
        )
        for detail, word, word_list in detail_rows
    ]
    seen_word_ids = {item["id"] for item in words}
    missing_wrong_ids = sorted(daily_wrong_ids - seen_word_ids)
    if missing_wrong_ids:
        wrong_words = db.scalars(select(Word).where(Word.id.in_(missing_wrong_ids)).order_by(Word.word.asc())).all()
        words.extend(
            challenge_day_word_item(
                word,
                status="correct" if word.id in corrected_wrong_ids else "wrong",
                daily_wrong_ids=daily_wrong_ids,
                corrected_wrong_ids=corrected_wrong_ids,
                correct_count=0,
                wrong_count=wrong_count_by_word.get(word.id, 1),
                word_list=challenge_word_display_list(db, word.id, wrong_word_list),
            )
            for word in wrong_words
        )

    attempt_items = challenge_day_attempt_items(db, challenge_date, daily_wrong_ids, corrected_wrong_ids)
    words_by_pair: dict[tuple[int, int | None], dict[str, Any]] = {
        (item["id"], item.get("word_list_id")): item for item in words
    }
    words_by_id: dict[int, dict[str, Any]] = {item["id"]: item for item in words}
    for attempt_item in attempt_items:
        pair_key = (attempt_item["id"], attempt_item.get("word_list_id"))
        existing = words_by_pair.get(pair_key)
        fallback = words_by_id.get(attempt_item["id"])
        if (
            not existing
            and fallback
            and attempt_item.get("word_list_id")
            and (not fallback.get("word_list_name") or str(fallback.get("word_list_name")).startswith("生词本 "))
        ):
            existing = fallback
        if existing:
            existing["correct_count"] = max(
                int(existing.get("correct_count") or 0),
                int(attempt_item.get("correct_count") or 0),
            )
            existing["wrong_count"] = max(
                int(existing.get("wrong_count") or 0),
                int(attempt_item.get("wrong_count") or 0),
            )
            existing["was_wrong"] = bool(existing.get("was_wrong") or attempt_item.get("was_wrong"))
            if attempt_item.get("word_list_id") and (
                not existing.get("word_list_id") or str(existing.get("word_list_name") or "").startswith("生词本 ")
            ):
                old_pair_key = (existing["id"], existing.get("word_list_id"))
                existing["word_list_id"] = attempt_item.get("word_list_id")
                existing["word_list_name"] = attempt_item.get("word_list_name") or existing.get("word_list_name") or ""
                words_by_pair.pop(old_pair_key, None)
                words_by_pair[(existing["id"], existing.get("word_list_id"))] = existing
            if attempt_item.get("status"):
                existing["status"] = attempt_item["status"]
        else:
            words.append(attempt_item)
            words_by_pair[pair_key] = attempt_item
            words_by_id[attempt_item["id"]] = attempt_item

    correct = stat.correct_count if stat else sum(item["correct_count"] for item in words)
    wrong_attempts = stat.wrong_count if stat else sum(item["wrong_count"] for item in words)
    wrong_unique = len(daily_wrong_ids) if daily_wrong_ids else sum(1 for item in words if item["wrong_count"])
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
    list_summary_map: dict[str, dict[str, Any]] = {}
    for item in words:
        list_id = item.get("word_list_id")
        list_key = str(list_id) if list_id else "none"
        summary = list_summary_map.get(list_key)
        if not summary:
            summary = {
                "key": list_key,
                "id": list_id,
                "name": item.get("word_list_name") or "\u672a\u5f52\u5c5e\u5355\u8bcd\u8868",
                "word_count": 0,
                "correct": 0,
                "wrong": 0,
                "wrong_attempts": 0,
                "corrected": 0,
                "pending": 0,
            }
            list_summary_map[list_key] = summary
        summary["word_count"] += 1
        wrong_count = int(item.get("wrong_count") or 0)
        if item.get("was_wrong") or wrong_count:
            summary["wrong"] += 1
        elif int(item.get("correct_count") or 0) > 0 or item.get("status") == "correct":
            summary["correct"] += 1
        summary["wrong_attempts"] += wrong_count
        if item.get("corrected"):
            summary["corrected"] += 1
        if item.get("was_wrong") and not item.get("corrected"):
            summary["pending"] += 1
    list_summaries = list(list_summary_map.values())
    return {
        "date": challenge_date.isoformat(),
        "total": correct + wrong_attempts,
        "correct": correct,
        "wrong": wrong_unique,
        "wrong_attempts": wrong_attempts,
        "corrected": len(corrected_wrong_ids),
        "correction_pending": len(pending_wrong_ids),
        "wrong_challenge_count": len(pending_wrong_ids),
        "wrong_word_list_id": wrong_word_list.id if wrong_word_list else None,
        "list_summaries": list_summaries,
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
    word.image_issue = False
    word.enrichment_error = None
    db.add(word)
    db.commit()
    remember_word_resource(db, word, image_source="upload", override_media=True, commit=True)
    if previous_url != word.image_url:
        remove_local_image(previous_url, IMAGE_DIR)
    return {
        "ok": True,
        "word": word.word,
        "image_url": word.image_url,
        "source": "upload",
        "source_meta": image_source_meta("upload", word.image_url),
        "media_sources": word_media_sources(db, word),
    }


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


@app.post("/api/vue/public-assets/growth-trophy")
async def generate_growth_trophy_asset(
    edit_token: str = Form(default=""),
    model: str = Form(default="wan2.7-image-pro"),
):
    require_word_write_access(edit_token)
    selected_model = (model or "wan2.7-image-pro").strip()
    prompt = (
        "A beautiful premium game achievement trophy icon for a children's English learning app, "
        "golden trophy cup, PS5 style achievement badge, centered isolated object, cute but polished, "
        "soft highlights, transparent or clean light background, no text, no letters, no watermark, high quality"
    )
    try:
        content = await generate_dashscope_prompt_image(
            api_key=settings.dashscope_api_key,
            endpoint=settings.dashscope_image_endpoint,
            task_endpoint=settings.dashscope_task_endpoint,
            poll_seconds=settings.dashscope_image_poll_seconds,
            timeout_seconds=settings.dashscope_image_timeout_seconds,
            model=selected_model,
            prompt=prompt,
        )
    except RuntimeError as exc:
        detail = str(exc)
        if "not configured" in detail:
            raise HTTPException(status_code=400, detail=detail) from exc
        if is_ai_quota_error(detail):
            raise HTTPException(status_code=402, detail="额度已经用完") from exc
        raise HTTPException(status_code=502, detail=f"奖杯生成失败: {detail}") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:400] if exc.response is not None else str(exc)
        if is_ai_quota_error(detail):
            raise HTTPException(status_code=402, detail="额度已经用完") from exc
        raise HTTPException(status_code=502, detail=f"奖杯生成失败: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"奖杯生成失败: {exc}") from exc

    suffix = public_asset_extension(content)
    for old_asset in PUBLIC_ASSET_DIR.glob(f"{GROWTH_TROPHY_ASSET_STEM}.*"):
        if old_asset.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            try:
                old_asset.unlink()
            except OSError:
                pass
    target = PUBLIC_ASSET_DIR / f"{GROWTH_TROPHY_ASSET_STEM}{suffix}"
    target.write_bytes(content)
    return {
        "ok": True,
        "name": "成长奖杯",
        "model": selected_model,
        "image_url": f"/media/generated-assets/{target.name}",
    }


@app.post("/api/vue/words/{word_id}/ai-image")
async def generate_ai_word_image(
    word_id: int,
    request: Request,
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
    preferred_user = preferred_admin_user_ai(db, request)
    selected_provider = (provider or (preferred_user.image_ai_provider if preferred_user else "") or settings.ai_image_provider).strip()
    selected_model = (model or (preferred_user.image_ai_model if preferred_user else "") or "").strip()
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
        word.image_issue = False
        word.enrichment_error = None
        db.add(word)
        db.commit()
        committed_model = (
            selected_openai_model
            if selected_provider == "openai"
            else selected_dashscope_model
            if selected_provider == "dashscope"
            else selected_tencent_action
        )
        image_source = f"ai-image:{committed_model}"
        remember_word_resource(db, word, image_source=image_source, override_media=True, commit=True)
        if previous_url != word.image_url:
            remove_local_image(previous_url, IMAGE_DIR)
    else:
        committed_model = (
            selected_openai_model
            if selected_provider == "openai"
            else selected_dashscope_model
            if selected_provider == "dashscope"
            else selected_tencent_action
        )
        image_source = f"ai-image:{committed_model}"
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
        "source": image_source,
        "source_meta": image_source_meta(image_source, image_url),
        "media_sources": word_media_sources(db, word) if should_commit else {},
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
    decorated_images = []
    for image in images:
        if isinstance(image, dict):
            image_url = image.get("url") or image.get("image_url") or ""
            image_source = image.get("source") or image.get("provider") or "network"
            decorated_images.append({
                **image,
                "source": image_source,
                "source_meta": image_source_meta(image_source, image_url),
            })
    return {"ok": True, "word": word.word, "images": decorated_images}


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
    word.image_issue = False
    word.enrichment_error = None
    db.add(word)
    db.commit()
    remember_word_resource(db, word, image_source="network", override_media=True, commit=True)
    if previous_url != word.image_url:
        remove_local_image(previous_url, IMAGE_DIR)
    return {
        "ok": True,
        "word": word.word,
        "image_url": word.image_url,
        "source": "network",
        "source_meta": image_source_meta("network", word.image_url),
        "media_sources": word_media_sources(db, word),
    }


@app.post("/api/vue/words/{word_id}/sync-image")
async def sync_word_image(word_id: int, db: Session = Depends(get_db)):
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    return await sync_word_image_record(db, word)


async def sync_word_image_record(db: Session, word: Word) -> dict:
    if is_local_media_url(word.image_url):
        return {
            "ok": True,
            "id": word.id,
            "word": word.word,
            "image_url": word.image_url,
            "skipped": True,
            "source_meta": image_source_meta(None, word.image_url),
            "media_sources": word_media_sources(db, word),
        }

    if word.image_locked:
        return {
            "ok": True,
            "id": word.id,
            "word": word.word,
            "image_url": word.image_url,
            "skipped": True,
            "locked": True,
            "source_meta": image_source_meta(None, word.image_url),
            "media_sources": word_media_sources(db, word),
        }

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
                word.image_issue = False
                word.enrichment_error = None
                db.add(word)
                db.commit()
                remember_word_resource(db, word, image_source="network-sync", override_media=False, commit=True)
                return {
                    "ok": True,
                    "id": word.id,
                    "word": word.word,
                    "image_url": local_url,
                    "skipped": False,
                    "source": "network-sync",
                    "source_meta": image_source_meta("network-sync", local_url),
                    "media_sources": word_media_sources(db, word),
                }
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


@app.post("/api/vue/lists/{word_list_id}/ai-images/start")
def start_list_ai_image_batch(
    word_list_id: int,
    model: str = Query(default=LIST_AI_IMAGE_DEFAULT_MODEL),
    allow_paid: str = Query(default="0"),
    db: Session = Depends(get_db),
):
    word_list = db.get(WordList, word_list_id)
    if not word_list:
        raise HTTPException(status_code=404, detail="Word list not found")

    selected_model = normalize_list_ai_image_model(model)
    paid_confirmed = allow_paid.strip().lower() in {"1", "true", "yes", "paid"}
    pending_words = get_missing_image_words(db, word_list_id)
    quota = ai_image_quota_status(db, model=selected_model)
    job_id = uuid4().hex
    job = {
        "id": job_id,
        "word_list_id": word_list_id,
        "status": "queued",
        "total": len(pending_words),
        "done": 0,
        "generated": 0,
        "skipped": 0,
        "failed": 0,
        "current_word": "",
        "model": selected_model,
        "model_label": list_ai_image_model_label(selected_model),
        "paid_confirmed": paid_confirmed,
        "requires_paid_confirmation": False,
        "quota": quota,
        "results": [],
        "message": "批量 AI 生图任务已创建",
    }
    with IMAGE_SYNC_LOCK:
        LIST_AI_IMAGE_JOBS[job_id] = job

    if ai_image_quota_requires_confirmation(quota, paid_confirmed):
        update_list_ai_image_job(
            job_id,
            status="failed",
            message=ai_image_quota_confirmation_message(quota),
            requires_paid_confirmation=True,
        )
        with IMAGE_SYNC_LOCK:
            return dict(LIST_AI_IMAGE_JOBS[job_id])

    Thread(target=run_list_ai_image_job, args=(job_id, word_list_id, selected_model, paid_confirmed), daemon=True).start()
    return job


@app.get("/api/vue/lists/{word_list_id}/ai-images/{job_id}")
def list_ai_image_status(word_list_id: int, job_id: str):
    with IMAGE_SYNC_LOCK:
        job = LIST_AI_IMAGE_JOBS.get(job_id)
        if not job or job.get("word_list_id") != word_list_id:
            raise HTTPException(status_code=404, detail="AI image job not found")
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
    source: str = Form(default="dictionary"),
    list_id: str = Form(default=""),
    edit_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    if accent not in {"us", "gb"}:
        raise HTTPException(status_code=400, detail="Invalid accent")
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    selected_source = str(source or "dictionary").strip().lower()
    source_list_id = None
    if str(list_id or "").strip().isdigit():
        source_list_id = int(str(list_id).strip())

    if selected_source == "spb":
        options = await spb_audio_options_for_word(db, word, accent, source_list_id)
        if not options:
            if not spb_candidate_groups_for_word(db, word, source_list_id):
                error = "没有找到这个单词对应的 SPB 词库"
            elif not spb_miniprogram_authorization_configured():
                error = "服务器还没有配置 SPB 小程序授权，无法读取小程序音频"
            else:
                error = "没有从小程序拿到可用音频"
            return {"ok": False, "word": word.word, "accent": accent, "source": "spb", "options": [], "error": error}
        options = [
            {
                **option,
                "source_meta": audio_source_meta(option.get("source") or "spb-miniprogram", option.get("url")),
            }
            for option in options
            if isinstance(option, dict)
        ]
        return {"ok": True, "word": word.word, "accent": accent, "source": "spb", "options": options}

    options = []
    current_audio_url = word.british_audio_url if accent == "gb" else word.american_audio_url
    if is_local_audio_url(current_audio_url):
        current_meta = word_media_sources(db, word).get("audio", {}).get(accent) or audio_source_meta(None, current_audio_url)
        options.append({
            "label": "当前英式音源" if accent == "gb" else "当前美式音源",
            "url": current_audio_url,
            "source": current_meta.get("source") or "current",
            "source_meta": current_meta,
        })

    for candidate in await audio_candidates_with_dictionary(word.word, accent):
        try:
            local_url = await store_audio_candidate(word.word, accent, candidate["key"], candidate["url"], AUDIO_DIR)
        except Exception:
            local_url = None
        if local_url and all(option["url"] != local_url for option in options):
            source = f"dictionary:{candidate.get('key') or 'candidate'}"
            options.append({
                "label": candidate["label"],
                "url": local_url,
                "source": source,
                "source_meta": audio_source_meta(source, local_url),
            })

    if not options:
        return {"ok": False, "word": word.word, "accent": accent, "source": "dictionary", "options": [], "error": "没有找到可用音频"}
    return {"ok": True, "word": word.word, "accent": accent, "source": "dictionary", "options": options}


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

    current_audio_url = word.british_audio_url if accent == "gb" else word.american_audio_url
    can_commit_audio = should_replace_audio(current_audio_url, audio_url, incoming_source="choice")
    if can_commit_audio:
        if accent == "gb":
            word.british_audio_url = audio_url
            word.british_audio_locked = True
        else:
            word.american_audio_url = audio_url
            word.american_audio_locked = True
        word.audio_issue = False
        word.enrichment_error = None
        db.add(word)
        db.commit()
        remember_word_resource(
            db,
            word,
            american_audio_source="choice" if accent == "us" else None,
            british_audio_source="choice" if accent == "gb" else None,
            override_media=True,
            commit=True,
        )
    return {
        "ok": True,
        "word": word.word,
        "accent": accent,
        "audio_url": audio_url,
        "committed": can_commit_audio,
        "source": "choice",
        "source_meta": audio_source_meta("choice", audio_url),
        "media_sources": word_media_sources(db, word),
        "message": "" if can_commit_audio else "当前音频优先级更高，已保留原音频。",
    }


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
    target = AUDIO_DIR / f"record-{safe_word}-{accent}-{uuid4().hex[:8]}{suffix}"
    target.write_bytes(content)
    audio_url = f"/media/audio/{target.name}"

    current_audio_url = word.british_audio_url if accent == "gb" else word.american_audio_url
    can_commit_audio = should_replace_audio(current_audio_url, audio_url, incoming_source="recorded")
    if can_commit_audio:
        if accent == "gb":
            word.british_audio_url = audio_url
            word.british_audio_locked = True
        else:
            word.american_audio_url = audio_url
            word.american_audio_locked = True
        word.audio_issue = False
        word.enrichment_error = None
        db.add(word)
        db.commit()
        remember_word_resource(
            db,
            word,
            american_audio_source="recorded" if accent == "us" else None,
            british_audio_source="recorded" if accent == "gb" else None,
            override_media=True,
            commit=True,
        )
    return {
        "ok": True,
        "word": word.word,
        "accent": accent,
        "audio_url": audio_url,
        "committed": can_commit_audio,
        "source": "recorded",
        "source_meta": audio_source_meta("recorded", audio_url),
        "media_sources": word_media_sources(db, word),
        "message": "" if can_commit_audio else "当前音频优先级更高，已保留原音频。",
    }


@app.post("/api/vue/words/{word_id}/ai-audio")
async def word_ai_audio(
    word_id: int,
    request: Request,
    accent: str = Form(...),
    voice_gender: str = Form(default="female"),
    text_mode: str = Form(default="word"),
    commit: str = Form(default="1"),
    edit_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    if accent not in {"us", "gb"}:
        raise HTTPException(status_code=400, detail="Invalid accent")
    if voice_gender not in {"female", "male"}:
        raise HTTPException(status_code=400, detail="Invalid voice gender")
    if text_mode not in {"word", "phonetic"}:
        raise HTTPException(status_code=400, detail="Invalid text mode")

    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    if text_mode == "phonetic":
        display_phonetic = re.sub(r"^/+|/+$", "", (word.phonetic or "").strip()).strip()
        if not display_phonetic:
            raise HTTPException(status_code=400, detail="还没有音标，先补充音标后再生成。")
    preferred_user = preferred_admin_user_ai(db, request)
    selected_audio_provider = preferred_user.audio_ai_provider if preferred_user else settings.ai_tts_provider

    try:
        audio_url = await generate_ai_audio_with_settings(
            text_value=word.word,
            accent=accent,
            voice_gender=voice_gender,
            text_mode=text_mode,
            provider=selected_audio_provider,
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
    audio_source = selected_ai_tts_audio_source(text_mode, selected_audio_provider)
    current_audio_url = word.british_audio_url if accent == "gb" else word.american_audio_url
    can_commit_audio = should_replace_audio(current_audio_url, audio_url, incoming_source=audio_source)
    if should_commit and can_commit_audio:
        if accent == "gb":
            word.british_audio_url = audio_url
            word.british_audio_locked = True
        else:
            word.american_audio_url = audio_url
            word.american_audio_locked = True
        word.audio_issue = False
        word.enrichment_error = None
        db.add(word)
        db.commit()
        remember_word_resource(
            db,
            word,
            american_audio_source=audio_source if accent == "us" else None,
            british_audio_source=audio_source if accent == "gb" else None,
            override_media=True,
            commit=True,
        )
    return {
        "ok": True,
        "word": word.word,
        "accent": accent,
        "voice_gender": voice_gender,
        "text_mode": text_mode,
        "committed": should_commit and can_commit_audio,
        "message": "" if (not should_commit or can_commit_audio) else "当前音频优先级更高，已生成试听但未替换。",
        "audio_url": audio_url,
        "source": audio_source,
        "source_meta": audio_source_meta(audio_source, audio_url),
        "media_sources": word_media_sources(db, word) if should_commit and can_commit_audio else {},
    }


@app.post("/api/vue/words/{word_id}/definition-audio")
async def word_definition_audio(
    word_id: int,
    request: Request,
    edit_token: str = Form(default=""),
    list_id: int | None = Form(default=None),
    source: str = Form(default="auto"),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    source_mode = (source or "auto").strip().lower()
    resource_changed = apply_word_resource(db, word, commit=False, include_image=False)

    if source_mode in {"auto", "spb", "miniprogram", "mini-program", "spb-miniprogram"}:
        candidate_groups = spb_candidate_groups_for_word(db, word, list_id)
        spb_changed = await apply_spb_details_to_word(db, word, list_id=list_id)
        if spb_changed or resource_changed:
            db.add(word)
            db.commit()
            db.refresh(word)
        if is_local_audio_url(word.english_definition_audio_url) and is_spb_audio_source(
            audio_url=word.english_definition_audio_url
        ):
            remember_word_resource(
                db,
                word,
                english_definition_audio_source="spb-miniprogram",
                override_media=True,
                commit=True,
            )
            return {
                "ok": True,
                "word": serialize_word(word),
                "audio_url": word.english_definition_audio_url,
                "reused": False,
                "source": "spb-miniprogram",
                "source_meta": audio_source_meta("spb-miniprogram", word.english_definition_audio_url),
                "media_sources": word_media_sources(db, word),
            }
        if source_mode != "auto":
            if not candidate_groups:
                raise HTTPException(status_code=404, detail="没有找到这个单词对应的 SPB 词库，暂时不能同步小程序音频。")
            if not spb_miniprogram_authorization_configured():
                raise HTTPException(status_code=400, detail="服务器还没有配置 SPB 小程序授权，无法读取小程序音频。")
            raise HTTPException(status_code=404, detail="没有从 SPB 小程序拿到英文定义音频，可以改用生成英文定义音频。")

    if is_local_audio_url(word.english_definition_audio_url):
        if resource_changed:
            db.add(word)
            db.commit()
            db.refresh(word)
        return {
            "ok": True,
            "word": serialize_word(word),
            "audio_url": word.english_definition_audio_url,
            "reused": True,
            "source": "resource",
            "source_meta": audio_source_meta("resource", word.english_definition_audio_url),
            "media_sources": word_media_sources(db, word),
        }

    definition_text = re.sub(r"\s+", " ", (word.english_definition or "").strip())
    if not definition_text:
        raise HTTPException(status_code=400, detail="还没有英文定义，先补充英文定义后再生成音频。")
    preferred_user = preferred_admin_user_ai(db, request)
    selected_audio_provider = preferred_user.audio_ai_provider if preferred_user else settings.ai_tts_provider
    selected_voice_gender = preferred_user.audio_voice_gender if preferred_user else "female"

    try:
        audio_url = await generate_ai_audio_with_settings(
            text_value=definition_text,
            accent="gb",
            voice_gender=selected_voice_gender,
            text_mode="definition",
            provider=selected_audio_provider,
        )
    except RuntimeError as exc:
        detail = str(exc)
        if "not configured" in detail:
            raise HTTPException(status_code=400, detail=detail) from exc
        raise HTTPException(status_code=502, detail=f"英文定义音频生成失败: {detail}") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:400] if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"英文定义音频生成失败: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"英文定义音频生成失败: {exc}") from exc

    word.english_definition_audio_url = audio_url
    word.enrichment_error = None
    db.add(word)
    db.commit()
    db.refresh(word)
    audio_source = selected_ai_tts_audio_source("definition", selected_audio_provider)
    remember_word_resource(
        db,
        word,
        english_definition_audio_source=audio_source,
        override_media=True,
        commit=True,
    )
    return {
        "ok": True,
        "word": serialize_word(word),
        "audio_url": audio_url,
        "reused": False,
        "source": audio_source,
        "source_meta": audio_source_meta(audio_source, audio_url),
        "media_sources": word_media_sources(db, word),
    }


@app.post("/api/vue/words/{word_id}/example-audio")
async def word_example_audio(
    word_id: int,
    request: Request,
    edit_token: str = Form(default=""),
    list_id: int | None = Form(default=None),
    source: str = Form(default="auto"),
    db: Session = Depends(get_db),
):
    require_word_write_access(edit_token)
    word = db.get(Word, word_id)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    source_mode = (source or "auto").strip().lower()
    resource_changed = apply_word_resource(db, word, commit=False, include_image=False)

    if source_mode in {"auto", "spb", "miniprogram", "mini-program", "spb-miniprogram"}:
        candidate_groups = spb_candidate_groups_for_word(db, word, list_id)
        spb_changed = await apply_spb_details_to_word(db, word, list_id=list_id)
        if spb_changed or resource_changed:
            db.add(word)
            db.commit()
            db.refresh(word)
        if is_local_audio_url(word.english_example_audio_url) and is_spb_audio_source(
            audio_url=word.english_example_audio_url
        ):
            remember_word_resource(
                db,
                word,
                english_example_audio_source="spb-miniprogram",
                override_media=True,
                commit=True,
            )
            return {
                "ok": True,
                "word": serialize_word(word),
                "audio_url": word.english_example_audio_url,
                "reused": not spb_changed,
                "source": "spb-miniprogram",
                "source_meta": audio_source_meta("spb-miniprogram", word.english_example_audio_url),
                "media_sources": word_media_sources(db, word),
            }
        if source_mode != "auto":
            if not candidate_groups:
                raise HTTPException(status_code=404, detail="没有找到这个单词对应的 SPB 词库，暂时不能同步小程序例句音频。")
            if not spb_miniprogram_authorization_configured():
                raise HTTPException(status_code=400, detail="服务器还没有配置 SPB 小程序授权，无法读取小程序例句音频。")
            raise HTTPException(status_code=404, detail="没有从 SPB 小程序拿到英文例句音频，可以改用生成英文例句音频。")

    if is_local_audio_url(word.english_example_audio_url):
        if resource_changed:
            db.add(word)
            db.commit()
            db.refresh(word)
        return {
            "ok": True,
            "word": serialize_word(word),
            "audio_url": word.english_example_audio_url,
            "reused": True,
            "source": "resource",
            "source_meta": audio_source_meta("resource", word.english_example_audio_url),
            "media_sources": word_media_sources(db, word),
        }

    example_text = re.sub(r"\s+", " ", (word.english_example or "").strip())
    if not example_text:
        raise HTTPException(status_code=400, detail="还没有英文例句，先从 SPB 补全或手动补充例句。")
    preferred_user = preferred_admin_user_ai(db, request)
    selected_audio_provider = preferred_user.audio_ai_provider if preferred_user else settings.ai_tts_provider
    selected_voice_gender = preferred_user.audio_voice_gender if preferred_user else "female"

    try:
        audio_url = await generate_ai_audio_with_settings(
            text_value=example_text,
            accent="gb",
            voice_gender=selected_voice_gender,
            text_mode="example",
            provider=selected_audio_provider,
        )
    except RuntimeError as exc:
        detail = str(exc)
        if "not configured" in detail:
            raise HTTPException(status_code=400, detail=detail) from exc
        raise HTTPException(status_code=502, detail=f"英文例句音频生成失败: {detail}") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:400] if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"英文例句音频生成失败: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"英文例句音频生成失败: {exc}") from exc

    word.english_example_audio_url = audio_url
    word.enrichment_error = None
    db.add(word)
    db.commit()
    db.refresh(word)
    audio_source = selected_ai_tts_audio_source("example", selected_audio_provider)
    remember_word_resource(
        db,
        word,
        english_example_audio_source=audio_source,
        override_media=True,
        commit=True,
    )
    return {
        "ok": True,
        "word": serialize_word(word),
        "audio_url": audio_url,
        "reused": False,
        "source": audio_source,
        "source_meta": audio_source_meta(audio_source, audio_url),
        "media_sources": word_media_sources(db, word),
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


def import_rows(
    rows: list[dict],
    db: Session,
    word_list: WordList,
    progress_callback: Callable[[int], None] | None = None,
) -> list[int]:
    created = updated = skipped = 0
    errors: list[str] = []
    word_ids: list[int] = []

    for row_index, row in enumerate(rows, start=1):
        word_text = row["word"]
        existing = db.scalar(select(Word).where(func.lower(Word.word) == word_text.lower()))
        if existing:
            if existing.word != word_text:
                existing.word = word_text
            existing.phonetic = row.get("phonetic") or existing.phonetic
            existing.alternate_spellings = merge_spellings(
                existing.alternate_spellings,
                row.get("alternate_spellings"),
                primary=word_text,
            )
            existing.part_of_speech = row.get("part_of_speech") or existing.part_of_speech
            existing.english_definition = row.get("english_definition") or existing.english_definition
            existing.english_definition_locked = existing.english_definition_locked or bool(row.get("english_definition"))
            existing.english_definition_audio_url = (
                local_import_audio_url(row.get("english_definition_audio_url"))
                or existing.english_definition_audio_url
            )
            existing.chinese_definition = row.get("chinese_definition") or existing.chinese_definition
            existing.chinese_definition_locked = existing.chinese_definition_locked or bool(row.get("chinese_definition"))
            incoming_example = str(row.get("english_example") or "").strip()
            incoming_example_audio_url = local_import_audio_url(row.get("english_example_audio_url"))
            if incoming_example:
                if (existing.english_example or "").strip() != incoming_example and not incoming_example_audio_url:
                    existing.english_example_audio_url = None
                existing.english_example = incoming_example
            existing.english_example_locked = existing.english_example_locked or bool(incoming_example)
            existing.english_example_audio_url = incoming_example_audio_url or existing.english_example_audio_url
            apply_imported_local_audio(existing, row)
            existing.note = row.get("note") or existing.note
            word = existing
            word.enrichment_status = "pending"
            updated += 1
        else:
            word = Word(
                word=word_text,
                phonetic=row.get("phonetic"),
                alternate_spellings=merge_spellings(None, row.get("alternate_spellings"), primary=word_text),
                part_of_speech=row.get("part_of_speech"),
                english_definition=row.get("english_definition"),
                english_definition_locked=bool(row.get("english_definition")),
                english_definition_audio_url=local_import_audio_url(row.get("english_definition_audio_url")),
                chinese_definition=row.get("chinese_definition"),
                chinese_definition_locked=bool(row.get("chinese_definition")),
                english_example=row.get("english_example"),
                english_example_locked=bool(row.get("english_example")),
                english_example_audio_url=local_import_audio_url(row.get("english_example_audio_url")),
                american_audio_url=local_import_audio_url(row.get("american_audio_url")),
                american_audio_locked=bool(local_import_audio_url(row.get("american_audio_url"))),
                british_audio_url=local_import_audio_url(row.get("british_audio_url")),
                british_audio_locked=bool(local_import_audio_url(row.get("british_audio_url"))),
                note=row.get("note"),
                enrichment_status="pending",
            )
            db.add(word)
            created += 1

        try:
            db.commit()
            db.refresh(word)
            apply_word_resource(db, word, commit=False, include_image=False)
            remember_word_resource(
                db,
                word,
                american_audio_source=row.get("american_audio_url_source"),
                british_audio_source=row.get("british_audio_url_source"),
                english_definition_audio_source=row.get("english_definition_audio_url_source"),
                english_example_audio_source=row.get("english_example_audio_url_source"),
                override_text=bool(row.get("spb_text_source")),
                override_media=bool(
                    row.get("american_audio_url_source")
                    or row.get("british_audio_url_source")
                    or row.get("english_definition_audio_url_source")
                    or row.get("english_example_audio_url_source")
                ),
                commit=False,
            )
            db.commit()
            db.refresh(word)
            link_word_to_list(db, word_list.id, word.id)
            word_ids.append(word.id)
        except Exception as exc:
            db.rollback()
            skipped += 1
            errors.append(f"第 {row.get('row_number')} 行 {word_text}: {exc}")
        if progress_callback:
            progress_callback(row_index)

    return word_ids


def local_import_audio_url(value: str | None) -> str | None:
    audio_url = str(value or "").strip()
    return audio_url if is_local_audio_url(audio_url) else None


def local_spb_word_audio_url_for_accent(value: str | None, accent: str) -> bool:
    audio_url = str(value or "").strip()
    filename = Path(audio_url.split("?", 1)[0]).name.lower()
    return bool(
        is_local_audio_url(audio_url)
        and (filename.startswith("spb-") or "-spb-" in filename)
        and f"-{accent}-" in filename
    )


def legacy_word_audio_in_example_slot(value: str | None) -> bool:
    return local_spb_word_audio_url_for_accent(value, "gb")


def repair_legacy_spb_example_audio_slot(word: Word) -> bool:
    audio_url = (word.british_audio_url or "").strip()
    if not local_spb_word_audio_url_for_accent(audio_url, "gb"):
        return False

    changed = False
    if (word.english_example or "").strip() and not (word.english_example_audio_url or "").strip():
        word.english_example_audio_url = audio_url
        changed = True
    word.british_audio_url = None
    word.british_audio_locked = False
    changed = True
    return changed


def repair_legacy_spb_example_audio_resource(resource: WordResourcePool) -> bool:
    audio_url = (resource.british_audio_url or "").strip()
    if not local_spb_word_audio_url_for_accent(audio_url, "gb"):
        return False

    changed = False
    if (resource.english_example or "").strip() and not (resource.english_example_audio_url or "").strip():
        resource.english_example_audio_url = audio_url
        resource.english_example_audio_source = resource.british_audio_source or "spb-miniprogram"
        changed = True
    resource.british_audio_url = None
    resource.british_audio_source = None
    changed = True
    return changed


def audio_source_priority(source: str | None = None, audio_url: str | None = None) -> int:
    source_marker = (source or "").strip().lower()
    audio_filename = Path(str(audio_url or "").split("?", 1)[0]).name.lower()
    marker = f"{source_marker} {audio_filename}"
    is_local_audio = is_local_audio_url(audio_url)
    if is_local_audio:
        if audio_filename.startswith("spb-") or "-spb-" in audio_filename:
            return 300
        if audio_filename.startswith("ai-"):
            return 200 if any(token in marker for token in ("aliyun", "dashscope", "phoneme")) else 180
        if audio_filename.startswith("record-") or audio_filename.startswith("upload-") or "recorded" in audio_filename:
            return 150
        if audio_filename.startswith("dict-"):
            return 100
    if not is_local_audio and (
        source_marker.startswith("spb") or "spb-miniprogram" in source_marker or "miniprogram" in source_marker
    ):
        return 300
    if "aliyun" in marker or "dashscope" in marker or "phoneme" in marker:
        return 200
    if audio_filename.startswith("ai-") or "ai-tts" in marker or "openai" in marker or re.search(r"-(female|male)-ai-", marker):
        return 180
    if audio_filename.startswith("record-") or audio_filename.startswith("upload-") or "choice" in marker or "recorded" in marker:
        return 150
    if audio_filename.startswith("dict-") or any(token in marker for token in ("free-dictionary", "youdao", "google", "dictionary", "tts")):
        return 100
    return 0


def is_spb_audio_source(source: str | None = None, audio_url: str | None = None) -> bool:
    return audio_source_priority(source, audio_url) >= 300


def should_force_spb_audio(incoming_source: str | None, incoming_url: str | None) -> bool:
    return bool((incoming_url or "").strip()) and is_spb_audio_source(incoming_source, incoming_url)


def should_replace_audio(
    current_url: str | None,
    incoming_url: str | None,
    *,
    current_source: str | None = None,
    incoming_source: str | None = None,
) -> bool:
    if not (incoming_url or "").strip():
        return False
    if not (current_url or "").strip():
        return True
    return audio_source_priority(incoming_source, incoming_url) > audio_source_priority(current_source, current_url)


def ai_tts_audio_source(text_mode: str) -> str:
    if text_mode == "phonetic":
        return "ai-tts:dashscope"
    provider = (settings.ai_tts_provider or "").strip().lower()
    return f"ai-tts:{provider or 'generated'}"


def selected_ai_tts_audio_source(text_mode: str, provider: str | None = None) -> str:
    if text_mode == "phonetic":
        return "ai-tts:dashscope"
    selected_provider = (provider or settings.ai_tts_provider or "").strip().lower()
    return f"ai-tts:{selected_provider or 'generated'}"


async def generate_ai_audio_with_settings(
    *,
    text_value: str,
    accent: str,
    voice_gender: str = "female",
    text_mode: str = "word",
    provider: str | None = None,
) -> str:
    return await generate_word_ai_audio(
        provider=provider or settings.ai_tts_provider,
        api_key=settings.openai_api_key,
        model=settings.openai_tts_model,
        word=text_value,
        accent=accent,
        voice_gender=voice_gender,
        text_mode=text_mode,
        audio_dir=AUDIO_DIR,
        voice_us=settings.openai_tts_voice_us,
        voice_gb=settings.openai_tts_voice_gb,
        dashscope_api_key=settings.dashscope_api_key,
        dashscope_tts_endpoint=settings.dashscope_tts_endpoint,
        dashscope_tts_model=settings.dashscope_tts_model,
        dashscope_tts_voice_female=settings.dashscope_tts_voice_female,
        dashscope_tts_voice_male=settings.dashscope_tts_voice_male,
        dashscope_tts_format=settings.dashscope_tts_format,
        dashscope_tts_sample_rate=settings.dashscope_tts_sample_rate,
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


def apply_imported_local_audio(word: Word, row: dict[str, Any]) -> bool:
    changed = False
    american_audio_url = local_import_audio_url(row.get("american_audio_url"))
    british_audio_url = local_import_audio_url(row.get("british_audio_url"))
    english_definition_audio_url = local_import_audio_url(row.get("english_definition_audio_url"))
    english_example_audio_url = local_import_audio_url(row.get("english_example_audio_url"))
    american_source = row.get("american_audio_url_source")
    british_source = row.get("british_audio_url_source")
    english_definition_source = row.get("english_definition_audio_url_source")
    english_example_source = row.get("english_example_audio_url_source")
    if should_force_spb_audio(american_source, american_audio_url) or should_replace_audio(
        word.american_audio_url,
        american_audio_url,
        incoming_source=american_source,
    ):
        word.american_audio_url = american_audio_url
        word.american_audio_locked = True
        changed = True
    if should_force_spb_audio(british_source, british_audio_url) or should_replace_audio(
        word.british_audio_url,
        british_audio_url,
        incoming_source=british_source,
    ):
        word.british_audio_url = british_audio_url
        word.british_audio_locked = True
        changed = True
    if should_force_spb_audio(english_definition_source, english_definition_audio_url) or should_replace_audio(
        word.english_definition_audio_url,
        english_definition_audio_url,
        incoming_source=english_definition_source,
    ):
        word.english_definition_audio_url = english_definition_audio_url
        changed = True
    if should_force_spb_audio(english_example_source, english_example_audio_url) or should_replace_audio(
        word.english_example_audio_url,
        english_example_audio_url,
        incoming_source=english_example_source,
    ) or (english_example_audio_url and legacy_word_audio_in_example_slot(word.english_example_audio_url)):
        word.english_example_audio_url = english_example_audio_url
        changed = True
    if english_example_audio_url and not british_audio_url and local_spb_word_audio_url_for_accent(word.british_audio_url, "gb"):
        word.british_audio_url = None
        word.british_audio_locked = False
        changed = True
    if repair_legacy_spb_example_audio_slot(word):
        changed = True
    return changed


def clear_misclassified_spb_audio_from_resource(db: Session, word: Word, row: dict[str, Any]) -> bool:
    english_example_audio_url = local_import_audio_url(row.get("english_example_audio_url"))
    if not english_example_audio_url:
        return False
    resource = get_word_resource(db, word.word)
    if not resource:
        return False

    changed = repair_legacy_spb_example_audio_resource(resource)
    if (
        not local_import_audio_url(row.get("british_audio_url"))
        and local_spb_word_audio_url_for_accent(resource.british_audio_url, "gb")
    ):
        resource.british_audio_url = None
        resource.british_audio_source = None
        changed = True
    if changed:
        db.add(resource)
    return changed


def word_needs_spb_detail_repair(word: Word) -> bool:
    if (
        not (word.phonetic or "").strip()
        or not (word.part_of_speech or "").strip()
        or not (word.english_definition or "").strip()
        or not (word.english_example or "").strip()
    ):
        return True
    if (word.english_example or "").strip() and (
        not is_local_audio_url(word.english_example_audio_url)
        or not is_spb_audio_source(audio_url=word.english_example_audio_url)
    ):
        return True
    if (word.english_definition or "").strip() and (
        not is_local_audio_url(word.english_definition_audio_url)
        or not is_spb_audio_source(audio_url=word.english_definition_audio_url)
    ):
        return True
    return local_spb_word_audio_url_for_accent(word.british_audio_url, "gb")


def word_needs_spb_word_audio_repair(word: Word, source_row: dict[str, Any] | None) -> bool:
    if not source_row:
        return False
    for field in ("american_audio_url", "british_audio_url"):
        incoming_url = str(source_row.get(field) or "").strip()
        if spb_looks_like_audio_url(incoming_url) and not is_spb_audio_source(audio_url=getattr(word, field, None)):
            return True
    return False


def safe_audio_source_fragment(source_key: str | None) -> str:
    return (re.sub(r"[^a-zA-Z0-9_-]+", "-", str(source_key or "").lower()).strip("-") or "source")[:80]


def local_spb_word_audio_matches_group(audio_url: str | None, group: dict[str, Any]) -> bool:
    if not is_spb_audio_source(audio_url=audio_url):
        return False
    expected_fragment = safe_audio_source_fragment(spb_word_audio_source_key(group))
    return expected_fragment in Path(str(audio_url or "")).name.lower()


def local_spb_detail_audio_matches_group(audio_url: str | None, group: dict[str, Any], kind: str) -> bool:
    if not is_spb_audio_source(audio_url=audio_url):
        return False
    expected_fragment = safe_audio_source_fragment(spb_detail_audio_source_key_prefix(group, kind))
    return expected_fragment in Path(str(audio_url or "")).name.lower()


def word_needs_spb_group_audio_repair(
    word: Word,
    group: dict[str, Any],
    source_row: dict[str, Any] | None,
) -> bool:
    if not source_row:
        return False
    if word_needs_spb_word_audio_repair(word, source_row):
        return True
    if source_row.get("spb_word_id"):
        for field in ("american_audio_url", "british_audio_url"):
            current_url = getattr(word, field, None)
            if current_url and not local_spb_word_audio_matches_group(current_url, group):
                return True
        for kind, field in (
            ("definition", "english_definition_audio_url"),
            ("example", "english_example_audio_url"),
        ):
            current_url = getattr(word, field, None)
            if current_url and is_spb_audio_source(audio_url=current_url) and not local_spb_detail_audio_matches_group(
                current_url,
                group,
                kind,
            ):
                return True
    return False


def merge_spellings(existing: str | None, incoming: str | None, *, primary: str | None = None) -> str | None:
    values: list[str] = []
    seen: set[str] = set()
    primary_normalized = unicodedata.normalize("NFC", (primary or "").strip()).casefold()
    for text in (existing, incoming):
        if not text:
            continue
        for item in re.split(r"[,;/；，、\n\r]+", text):
            spelling = item.strip()
            normalized = unicodedata.normalize("NFC", spelling).casefold()
            if spelling and normalized != primary_normalized and normalized not in seen:
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


def start_enrichment_thread(word_ids: list[int], *, include_images: bool = True) -> None:
    worker = Thread(target=lambda: asyncio.run(enrich_word_ids(word_ids, include_images=include_images)), daemon=True)
    worker.start()


async def apply_spb_detail_backfill_word_ids(
    word_ids: list[int],
    *,
    job_id: str | None = None,
    collection_key: str | None = None,
    group_key: str | None = None,
    force_audio_download: bool = False,
) -> None:
    db = SessionLocal()
    total = len(word_ids)
    changed_count = 0
    spb_audio_count = 0
    failed_count = 0
    preferred_group = None
    if collection_key and group_key:
        try:
            _collection, preferred_group = spb_collection_group_by_keys(collection_key, group_key)
        except HTTPException:
            preferred_group = None
    try:
        if job_id:
            update_spb_sync_job(
                job_id,
                status="running",
                stage="detail_backfill",
                total=total,
                processed=0,
                current_word="",
                message=(
                    f"正在强制下载 SPB 小程序详情音频：0 / {total}"
                    if force_audio_download
                    else f"正在检查 SPB 详情和音频来源：0 / {total}"
                ),
                collection=collection_key,
                key=group_key,
                force_audio_download=force_audio_download,
            )
        for index, word_id in enumerate(word_ids, start=1):
            word = db.get(Word, word_id)
            if not word:
                if job_id:
                    update_spb_sync_job(
                        job_id,
                        processed=index,
                        message=(
                            f"正在强制下载 SPB 小程序详情音频：{index} / {total}"
                            if force_audio_download
                            else f"正在检查 SPB 详情和音频来源：{index} / {total}"
                        ),
                    )
                continue
            try:
                if job_id:
                    update_spb_sync_job(
                        job_id,
                        processed=index - 1,
                        current_word=word.word,
                        message=(
                            f"正在强制下载 SPB 小程序详情音频：{index - 1} / {total}"
                            if force_audio_download
                            else f"正在检查 SPB 详情和音频来源：{index - 1} / {total}"
                        ),
                    )
                resource_changed = apply_word_resource(db, word, commit=False, include_image=False)
                spb_changed = await apply_spb_details_to_word(
                    db,
                    word,
                    preferred_group=preferred_group,
                    force_audio_download=force_audio_download,
                )
                db.add(word)
                db.commit()
                db.refresh(word)
                resource_remembered = remember_word_resource(db, word, commit=True)
                if resource_changed or spb_changed or resource_remembered:
                    changed_count += 1
                spb_audio_count += sum(
                    1
                    for audio_url in (
                        word.american_audio_url,
                        word.british_audio_url,
                        word.english_definition_audio_url,
                        word.english_example_audio_url,
                    )
                    if is_spb_audio_source(audio_url=audio_url)
                )
            except Exception:
                db.rollback()
                failed_count += 1
            finally:
                if job_id:
                    update_spb_sync_job(
                        job_id,
                        processed=index,
                        current_word=word.word,
                        text_detail_count=changed_count,
                        local_audio_count=spb_audio_count,
                        message=(
                            f"正在强制下载 SPB 小程序详情音频：{index} / {total}"
                            if force_audio_download
                            else f"正在检查 SPB 详情和音频来源：{index} / {total}"
                        ),
                    )
        if job_id:
            if force_audio_download:
                message = f"SPB 小程序音频强制下载完成：检查 {total} 个，替换/确认 {changed_count} 个。"
            else:
                message = f"SPB 详情和音频来源更新完成：检查 {total} 个，修复 {changed_count} 个。"
            if spb_audio_count:
                message += f" 本地 SPB 音频 {spb_audio_count} 个。"
            if failed_count:
                message += f" {failed_count} 个暂时失败，可稍后再点更新详情。"
            update_spb_sync_job(
                job_id,
                status="complete",
                stage="complete",
                processed=total,
                current_word="",
                text_detail_count=changed_count,
                local_audio_count=spb_audio_count,
                message=message,
                collection=collection_key,
                key=group_key,
            )
    except Exception as exc:
        db.rollback()
        if job_id:
            update_spb_sync_job(
                job_id,
                status="failed",
                stage="failed",
                current_word="",
                message=f"SPB 详情更新失败：{str(exc)[:240]}",
            )
    finally:
        db.close()


def start_spb_detail_backfill_thread(
    word_ids: list[int],
    *,
    job_id: str | None = None,
    collection_key: str | None = None,
    group_key: str | None = None,
    force_audio_download: bool = False,
) -> None:
    worker = Thread(
        target=lambda: asyncio.run(
            apply_spb_detail_backfill_word_ids(
                word_ids,
                job_id=job_id,
                collection_key=collection_key,
                group_key=group_key,
                force_audio_download=force_audio_download,
            )
        ),
        daemon=True,
    )
    worker.start()


def clean_list_name(name: str) -> str:
    text = " ".join((name or "").split())
    return text[:255] or "新单词表"


def clean_manual_word_text(value: str | None) -> str:
    text = " ".join(str(value or "").strip().split())
    if not text:
        raise HTTPException(status_code=400, detail="请输入英文单词。")
    if len(text) > 128:
        raise HTTPException(status_code=400, detail="单词不能超过 128 个字符。")
    if not re.search(r"[A-Za-z]", text):
        raise HTTPException(status_code=400, detail="请输入包含英文字母的单词或词组。")
    if re.search(r"[^A-Za-z0-9\s'’`.\-‐‑–—/&+(),]", text):
        raise HTTPException(status_code=400, detail="单词只能包含英文、数字、空格和常见英文符号。")
    return text


def manual_word_lookup_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def serialize_manual_word_candidate(db: Session, word: Word, word_list_id: int) -> dict[str, Any]:
    payload = serialize_word(word)
    payload["in_current_list"] = bool(
        db.scalar(
            select(WordListItem.id)
            .where(WordListItem.word_list_id == word_list_id)
            .where(WordListItem.word_id == word.id)
            .limit(1)
        )
    )
    return payload


def manual_word_candidates(db: Session, word_text: str, word_list_id: int, limit: int = 8) -> list[dict[str, Any]]:
    exact_key = word_text.casefold()
    compact_key = manual_word_lookup_key(word_text)
    candidates_by_id: dict[int, Word] = {}

    exact_words = db.scalars(
        select(Word)
        .where(func.lower(Word.word) == word_text.lower())
        .order_by(Word.id.asc())
        .limit(limit)
    ).all()
    for word in exact_words:
        candidates_by_id[word.id] = word

    if compact_key and len(candidates_by_id) < limit:
        first = compact_key[0]
        possible_words = db.scalars(
            select(Word)
            .where(func.lower(Word.word).like(f"{first}%"))
            .order_by(func.length(Word.word).asc(), Word.word.asc())
            .limit(2000)
        ).all()
        for word in possible_words:
            if len(candidates_by_id) >= limit:
                break
            if word.id in candidates_by_id:
                continue
            if manual_word_lookup_key(word.word) == compact_key:
                candidates_by_id[word.id] = word

    def sort_key(word: Word) -> tuple[int, int, str]:
        word_value = word.word or ""
        word_exact = word_value.casefold() == exact_key
        word_compact = manual_word_lookup_key(word_value) == compact_key
        return (
            0 if word_exact else 1 if word_compact else 2,
            len(word_value),
            word_value.casefold(),
        )

    candidates = sorted(candidates_by_id.values(), key=sort_key)[:limit]
    return [serialize_manual_word_candidate(db, word, word_list_id) for word in candidates]


def optional_manual_word_text(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def normalize_resource_word(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())[:128]


def get_word_resource(db: Session, word_text: str | None) -> WordResourcePool | None:
    normalized = normalize_resource_word(word_text)
    if not normalized:
        return None
    return db.scalar(select(WordResourcePool).where(WordResourcePool.normalized_word == normalized))


def reusable_local_audio_for_word(
    db: Session | None,
    word_text: str | None,
    accent: str,
    incoming_source: str | None = None,
) -> tuple[str, str | None] | None:
    if db is None:
        return None
    resource = get_word_resource(db, word_text)
    if not resource:
        return None
    if accent == "gb":
        audio_url = (resource.british_audio_url or "").strip()
        source = resource.british_audio_source
    else:
        audio_url = (resource.american_audio_url or "").strip()
        source = resource.american_audio_source
    if not is_local_audio_url(audio_url):
        return None
    if audio_source_priority(source, audio_url) < audio_source_priority(incoming_source, audio_url):
        return None
    return audio_url, source


def word_has_shareable_resource(word: Word) -> bool:
    return any(
        (getattr(word, field, None) or "").strip()
        for field in (
            "phonetic",
            "part_of_speech",
            "english_definition",
            "english_definition_audio_url",
            "chinese_definition",
            "english_example",
            "english_example_audio_url",
            "image_url",
            "american_audio_url",
            "british_audio_url",
        )
    )


def remember_word_resource(
    db: Session,
    word: Word,
    *,
    image_source: str | None = None,
    american_audio_source: str | None = None,
    british_audio_source: str | None = None,
    english_definition_audio_source: str | None = None,
    english_example_audio_source: str | None = None,
    override_text: bool = False,
    override_media: bool = False,
    commit: bool = False,
) -> bool:
    word_changed = repair_legacy_spb_example_audio_slot(word)
    normalized = normalize_resource_word(word.word)
    if not normalized or not word_has_shareable_resource(word):
        if word_changed:
            db.add(word)
            if commit:
                db.commit()
        return False

    resource = get_word_resource(db, word.word)
    changed = word_changed
    if not resource:
        resource = WordResourcePool(normalized_word=normalized)
        db.add(resource)
        changed = True

    if resource.display_word != word.word:
        resource.display_word = word.word
        changed = True
    if resource.source_word_id != word.id:
        resource.source_word_id = word.id
        changed = True

    for field in ("phonetic", "part_of_speech", "english_definition", "chinese_definition", "english_example"):
        value = (getattr(word, field, None) or "").strip()
        if value and (override_text or not getattr(resource, field)):
            if field == "english_example" and getattr(resource, field, None) != value and not (word.english_example_audio_url or "").strip():
                resource.english_example_audio_url = None
                resource.english_example_audio_source = None
            setattr(resource, field, value)
            changed = True

    if (word.image_url or "").strip() and (override_media or not resource.image_url):
        resource.image_url = word.image_url
        resource.image_source = image_source or resource.image_source or "word"
        changed = True
    if (word.american_audio_url or "").strip() and (
        not resource.american_audio_url
        or should_replace_audio(
            resource.american_audio_url,
            word.american_audio_url,
            current_source=resource.american_audio_source,
            incoming_source=american_audio_source,
        )
        or (
            override_media
            and audio_source_priority(american_audio_source, word.american_audio_url)
            >= audio_source_priority(resource.american_audio_source, resource.american_audio_url)
        )
    ):
        resource.american_audio_url = word.american_audio_url
        resource.american_audio_source = american_audio_source or resource.american_audio_source or "word"
        changed = True
    if (word.british_audio_url or "").strip() and (
        not resource.british_audio_url
        or should_replace_audio(
            resource.british_audio_url,
            word.british_audio_url,
            current_source=resource.british_audio_source,
            incoming_source=british_audio_source,
        )
        or (
            override_media
            and audio_source_priority(british_audio_source, word.british_audio_url)
            >= audio_source_priority(resource.british_audio_source, resource.british_audio_url)
        )
    ):
        resource.british_audio_url = word.british_audio_url
        resource.british_audio_source = british_audio_source or resource.british_audio_source or "word"
        changed = True
    if (word.english_definition_audio_url or "").strip() and (
        not resource.english_definition_audio_url
        or should_replace_audio(
            resource.english_definition_audio_url,
            word.english_definition_audio_url,
            current_source=resource.english_definition_audio_source,
            incoming_source=english_definition_audio_source,
        )
        or (
            override_media
            and audio_source_priority(english_definition_audio_source, word.english_definition_audio_url)
            >= audio_source_priority(resource.english_definition_audio_source, resource.english_definition_audio_url)
        )
    ):
        resource.english_definition_audio_url = word.english_definition_audio_url
        resource.english_definition_audio_source = (
            english_definition_audio_source
            or resource.english_definition_audio_source
            or "definition-audio"
        )
        changed = True
    if (word.english_example_audio_url or "").strip() and (
        not resource.english_example_audio_url
        or should_replace_audio(
            resource.english_example_audio_url,
            word.english_example_audio_url,
            current_source=resource.english_example_audio_source,
            incoming_source=english_example_audio_source,
        )
        or (
            override_media
            and audio_source_priority(english_example_audio_source, word.english_example_audio_url)
            >= audio_source_priority(resource.english_example_audio_source, resource.english_example_audio_url)
        )
    ):
        resource.english_example_audio_url = word.english_example_audio_url
        resource.english_example_audio_source = (
            english_example_audio_source
            or resource.english_example_audio_source
            or "example-audio"
        )
        changed = True

    if changed:
        if word_changed:
            db.add(word)
        db.add(resource)
        if commit:
            db.commit()
    return changed


def apply_word_resource(db: Session, word: Word, *, commit: bool = False, include_image: bool = True) -> bool:
    resource = get_word_resource(db, word.word)
    if not resource:
        changed = repair_legacy_spb_example_audio_slot(word)
        if changed:
            word.enrichment_error = None
            db.add(word)
            if commit:
                db.commit()
                db.refresh(word)
        return changed

    changed = repair_legacy_spb_example_audio_resource(resource)
    if repair_legacy_spb_example_audio_slot(word):
        changed = True
    resource_has_spb_detail = any(
        is_spb_audio_source(source, url)
        for source, url in (
            (resource.english_definition_audio_source, resource.english_definition_audio_url),
            (resource.english_example_audio_source, resource.english_example_audio_url),
        )
    )
    for field in ("phonetic", "part_of_speech"):
        value = (getattr(resource, field, None) or "").strip()
        if value and not (getattr(word, field, None) or "").strip():
            setattr(word, field, value)
            changed = True

    locked_text_fields = (
        ("english_definition", "english_definition_locked"),
        ("chinese_definition", "chinese_definition_locked"),
        ("english_example", "english_example_locked"),
    )
    for field, lock_field in locked_text_fields:
        value = (getattr(resource, field, None) or "").strip()
        if value and (resource_has_spb_detail or not (getattr(word, field, None) or "").strip()):
            if getattr(word, field, None) == value and getattr(word, lock_field, False):
                continue
            setattr(word, field, value)
            setattr(word, lock_field, True)
            changed = True

    if include_image and (resource.image_url or "").strip() and not (word.image_url or "").strip():
        word.image_url = resource.image_url
        word.image_locked = True
        word.image_issue = False
        changed = True
    if (resource.american_audio_url or "").strip() and (
        should_force_spb_audio(resource.american_audio_source, resource.american_audio_url)
        or should_replace_audio(
            word.american_audio_url,
            resource.american_audio_url,
            incoming_source=resource.american_audio_source,
        )
    ):
        word.american_audio_url = resource.american_audio_url
        word.american_audio_locked = True
        changed = True
    if (resource.british_audio_url or "").strip() and (
        should_force_spb_audio(resource.british_audio_source, resource.british_audio_url)
        or should_replace_audio(
            word.british_audio_url,
            resource.british_audio_url,
            incoming_source=resource.british_audio_source,
        )
    ):
        word.british_audio_url = resource.british_audio_url
        word.british_audio_locked = True
        changed = True
    if (resource.english_definition_audio_url or "").strip() and (
        should_force_spb_audio(resource.english_definition_audio_source, resource.english_definition_audio_url)
        or should_replace_audio(
            word.english_definition_audio_url,
            resource.english_definition_audio_url,
            incoming_source=resource.english_definition_audio_source,
        )
    ):
        word.english_definition_audio_url = resource.english_definition_audio_url
        changed = True
    if (resource.english_example_audio_url or "").strip() and (
        should_force_spb_audio(resource.english_example_audio_source, resource.english_example_audio_url)
        or should_replace_audio(
            word.english_example_audio_url,
            resource.english_example_audio_url,
            incoming_source=resource.english_example_audio_source,
        )
    ):
        word.english_example_audio_url = resource.english_example_audio_url
        changed = True

    if changed:
        word.enrichment_error = None
        resource.use_count = (resource.use_count or 0) + 1
        db.add(word)
        db.add(resource)
        if commit:
            db.commit()
            db.refresh(word)
    return changed


def apply_word_resources(db: Session, words: list[Word], *, commit: bool = True, include_image: bool = True) -> int:
    applied = 0
    for word in words:
        if apply_word_resource(db, word, commit=False, include_image=include_image):
            applied += 1
    if applied and commit:
        db.commit()
        for word in words:
            db.refresh(word)
    return applied


def seed_word_resource_pool(db: Session) -> None:
    words = db.scalars(select(Word).order_by(Word.id.asc())).all()
    changed = 0
    for word in words:
        if remember_word_resource(db, word, commit=False):
            changed += 1
    if changed:
        db.commit()


def percent_value(value: int, target: int) -> int:
    if target <= 0:
        return 0
    return max(0, min(100, round((value / target) * 100)))


def default_learning_growth_summary() -> dict[str, Any]:
    trophy_image = growth_trophy_image_url()
    return {
        "title": "成长成就",
        "subtitle": "像闯关一样完成每天学习",
        "level": 1,
        "points": 0,
        "nextLevelPoints": 500,
        "pointsToNextLevel": 500,
        "levelProgressPercent": 0,
        "scoreRules": growth_score_rules(),
        "trophyImageUrl": trophy_image,
        "metrics": [
            {
                **item,
                "badgeLabel": item["badge_label"],
                "value": 0,
                "percent": 0,
                "unlocked": False,
                "iconUrl": trophy_image,
            }
            for item in GROWTH_BADGE_CONFIG
        ],
        "dailyMissions": [],
    }


def growth_metric_value(db: Session, metric_key: str) -> int:
    metric = db.scalar(select(LearningGrowthMetric).where(LearningGrowthMetric.metric_key == metric_key))
    return metric.metric_value if metric else 0


def sync_learning_growth_metric(
    db: Session,
    metric_key: str,
    label: str,
    value: int,
    target: int,
    badge_label: str,
) -> None:
    metric = db.scalar(select(LearningGrowthMetric).where(LearningGrowthMetric.metric_key == metric_key))
    if metric:
        metric.metric_label = label
        metric.metric_value = value
        metric.metric_target = target
        metric.badge_label = badge_label
    else:
        metric = LearningGrowthMetric(
            metric_key=metric_key,
            metric_label=label,
            metric_value=value,
            metric_target=target,
            badge_label=badge_label,
        )
    db.add(metric)


def good_quote_growth_count() -> int:
    try:
        return len(list_featured_good_words_quotes(limit=1000))
    except Exception:
        return 0


def science_growth_count() -> int:
    try:
        return len(build_science_discovery_pool())
    except Exception:
        return 0


def growth_score_rules() -> list[dict[str, Any]]:
    return [
        {"key": "spelling_words", "label": "拼写题", "points": 2},
        {"key": "challenge_rounds", "label": "完整轮", "points": 50},
        {"key": "good_quotes", "label": "好句", "points": 3},
    ]


def learning_growth_summary(db: Session) -> dict[str, Any]:
    try:
        trophy_image = growth_trophy_image_url()
        spelling_words = db.scalar(select(func.count(ChallengeSpellingAttempt.id))) or 0
        challenge_rounds = db.scalar(select(func.coalesce(func.sum(ChallengeProgress.completed_rounds), 0))) or 0
        good_quotes = max(good_quote_growth_count(), growth_metric_value(db, "good_quotes"))
        values = {
            "spelling_words": int(spelling_words),
            "challenge_rounds": int(challenge_rounds),
            "good_quotes": int(good_quotes),
        }
        metrics = []
        for config in GROWTH_BADGE_CONFIG:
            value = values.get(config["key"], 0)
            sync_learning_growth_metric(
                db,
                config["key"],
                config["label"],
                value,
                config["target"],
                config["badge_label"],
            )
            metrics.append(
                {
                    **config,
                    "badgeLabel": config["badge_label"],
                    "value": value,
                    "percent": percent_value(value, config["target"]),
                    "unlocked": value >= config["target"],
                    "iconUrl": trophy_image,
                }
            )
        db.commit()

        today = date.today()
        today_stat = db.scalar(select(ChallengeDailyStat).where(ChallengeDailyStat.stat_date == today))
        today_correct = today_stat.correct_count if today_stat else 0
        today_wrong = today_stat.wrong_count if today_stat else 0
        today_total = today_correct + today_wrong
        points = values["spelling_words"] * 2 + values["challenge_rounds"] * 50 + values["good_quotes"] * 3
        level = max(1, points // 500 + 1)
        current_level_floor = (level - 1) * 500
        next_level_points = level * 500
        return {
            "title": "成长成就",
            "subtitle": "每天完成挑战，点亮自己的奖杯墙",
            "level": level,
            "points": points,
            "nextLevelPoints": next_level_points,
            "pointsToNextLevel": max(next_level_points - points, 0),
            "levelProgressPercent": percent_value(points - current_level_floor, 500),
            "scoreRules": growth_score_rules(),
            "trophyImageUrl": trophy_image,
            "metrics": metrics,
            "dailyMissions": [
                {
                    "key": "today_spelling",
                    "label": "今日拼写",
                    "value": today_total,
                    "target": 20,
                    "percent": percent_value(today_total, 20),
                },
                {
                    "key": "today_correct",
                    "label": "今日答对",
                    "value": today_correct,
                    "target": 10,
                    "percent": percent_value(today_correct, 10),
                },
            ],
        }
    except Exception:
        db.rollback()
        return default_learning_growth_summary()


def cat_world_growth_source_rows(growth: dict[str, Any]) -> list[dict[str, Any]]:
    rules = {item["key"]: item for item in growth.get("scoreRules", []) if isinstance(item, dict)}
    rows = []
    for metric in growth.get("metrics", []):
        if not isinstance(metric, dict):
            continue
        key = str(metric.get("key") or "")
        rule = rules.get(key, {})
        value = int(metric.get("value") or 0)
        energy_per_unit = int(rule.get("points") or 0)
        rows.append(
            {
                "key": key,
                "label": metric.get("label") or rule.get("label") or key,
                "value": value,
                "unit": metric.get("unit") or "",
                "energyPerUnit": energy_per_unit,
                "energy": value * energy_per_unit,
            }
        )
    return rows


def cat_world_essay_energy_source(db: Session, phone: str) -> dict[str, Any]:
    raw_rows = db.execute(
        select(
            EssayEntry.best_writing_points,
            EssayEntry.writing_score,
            EssayEntry.writing_score_breakdown,
        ).where(EssayEntry.phone == phone)
    ).all()
    essay_points: list[int] = []
    for best_writing_points, writing_score, raw_breakdown in raw_rows:
        stored_best = min(max(int(best_writing_points or 0), 0), 500)
        effective_points = stored_best or essay_writing_points_from_values(writing_score, raw_breakdown)
        if effective_points > 0:
            essay_points.append(effective_points)
    total_points = sum(essay_points)
    return {
        "key": "essay_scores",
        "label": "作文五项积分",
        "value": total_points,
        "unit": "积分",
        "energyPerUnit": 1,
        "energy": total_points,
        "essayCount": len(essay_points),
    }


def cat_world_operating_energy_source(db: Session, phone: str) -> dict[str, Any]:
    grants = db.scalars(
        select(CatWorldEnergyGrant)
        .where(CatWorldEnergyGrant.phone == phone)
        .order_by(CatWorldEnergyGrant.created_at.desc(), CatWorldEnergyGrant.id.desc())
    ).all()
    total_energy = sum(max(int(grant.amount or 0), 0) for grant in grants)
    today = date.today()
    today_energy = sum(
        max(int(grant.amount or 0), 0)
        for grant in grants
        if grant.created_at and grant.created_at.date() == today
    )
    latest = grants[0] if grants else None
    return {
        "key": "operating_activity",
        "label": "运营活动",
        "value": total_energy,
        "unit": "能量",
        "energyPerUnit": 1,
        "energy": total_energy,
        "grantCount": len(grants),
        "todayEnergy": today_energy,
        "detail": f"最近：{latest.reason}" if latest else "暂无运营活动发放",
    }


def cat_world_earned_energy(db: Session, phone: str, growth: dict[str, Any] | None = None) -> int:
    growth = growth or learning_growth_summary(db)
    essay_source = cat_world_essay_energy_source(db, phone)
    operating_source = cat_world_operating_energy_source(db, phone)
    return (
        max(int(growth.get("points") or 0), 0)
        + int(essay_source["energy"])
        + int(operating_source["energy"])
    )


def cat_world_today_energy(growth: dict[str, Any]) -> int:
    rules = {item["key"]: item for item in growth.get("scoreRules", []) if isinstance(item, dict)}
    missions = {item["key"]: item for item in growth.get("dailyMissions", []) if isinstance(item, dict)}
    spelling_count = int(missions.get("today_spelling", {}).get("value") or 0)
    spelling_points = int(rules.get("spelling_words", {}).get("points") or 0)
    return max(spelling_count * spelling_points, 0)


def cat_world_today_spelling_count(db: Session, today: date | None = None) -> int:
    stat = db.scalar(select(ChallengeDailyStat).where(ChallengeDailyStat.stat_date == (today or date.today())))
    if not stat:
        return 0
    return max(int(stat.correct_count or 0), 0) + max(int(stat.wrong_count or 0), 0)


def cat_world_play_time_reward_source(
    db: Session,
    phone: str,
    today: date | None = None,
) -> dict[str, Any]:
    reward_date = today or date.today()
    grants = db.scalars(
        select(CatWorldPlayTimeGrant)
        .where(CatWorldPlayTimeGrant.phone == phone)
        .where(CatWorldPlayTimeGrant.reward_date == reward_date)
        .order_by(CatWorldPlayTimeGrant.created_at.desc(), CatWorldPlayTimeGrant.id.desc())
    ).all()
    total_minutes = sum(max(int(grant.minutes or 0), 0) for grant in grants)
    latest = grants[0] if grants else None
    return {
        "date": reward_date.isoformat(),
        "minutes": total_minutes,
        "seconds": total_minutes * 60,
        "grantCount": len(grants),
        "latestReason": latest.reason if latest else "",
        "latestMinutes": max(int(latest.minutes or 0), 0) if latest else 0,
    }


def cat_world_play_time_earned_seconds(spelling_count: int, reward_seconds: int = 0) -> int:
    count = max(int(spelling_count or 0), 0)
    base_seconds = 0
    for target, seconds in CAT_WORLD_PLAY_TIME_TIERS:
        if count >= target:
            base_seconds = seconds
            break
    return base_seconds + max(int(reward_seconds or 0), 0)


def normalize_cat_world_play_time_day(state: CatWorldState, today: date) -> bool:
    if state.play_time_date == today:
        return False
    state.play_time_date = today
    state.play_time_used_seconds = 0
    state.play_time_last_seen_at = None
    return True


def cat_world_play_time_payload(
    state: CatWorldState,
    spelling_count: int,
    *,
    reward_seconds: int = 0,
    now: datetime | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    current_time = now or datetime.utcnow()
    current_day = today or date.today()
    normalize_cat_world_play_time_day(state, current_day)
    count = max(int(spelling_count or 0), 0)
    base_earned_seconds = cat_world_play_time_earned_seconds(count)
    normalized_reward_seconds = max(int(reward_seconds or 0), 0)
    earned_seconds = cat_world_play_time_earned_seconds(count, normalized_reward_seconds)
    stored_used_seconds = max(int(state.play_time_used_seconds or 0), 0)
    live_seconds = 0
    if state.play_time_last_seen_at and earned_seconds > stored_used_seconds:
        elapsed_seconds = max(int((current_time - state.play_time_last_seen_at).total_seconds()), 0)
        if elapsed_seconds <= CAT_WORLD_PLAY_TIME_HEARTBEAT_GRACE_SECONDS:
            live_seconds = min(elapsed_seconds, earned_seconds - stored_used_seconds)
    used_seconds = min(stored_used_seconds + live_seconds, earned_seconds)
    remaining_seconds = max(earned_seconds - used_seconds, 0)
    if count < 100:
        next_target = 100
        next_reward_minutes = 10
    elif count < 200:
        next_target = 200
        next_reward_minutes = 20
    else:
        next_target = 0
        next_reward_minutes = 0
    return {
        "date": current_day.isoformat(),
        "spellingCount": count,
        "baseEarnedSeconds": base_earned_seconds,
        "rewardSeconds": normalized_reward_seconds,
        "rewardMinutes": normalized_reward_seconds // 60,
        "earnedSeconds": earned_seconds,
        "earnedMinutes": earned_seconds // 60,
        "usedSeconds": used_seconds,
        "remainingSeconds": remaining_seconds,
        "nextTarget": next_target,
        "nextRewardMinutes": next_reward_minutes,
        "sessionActive": bool(state.play_time_last_seen_at and remaining_seconds > 0),
    }


def cat_world_update_play_time_session(
    state: CatWorldState,
    spelling_count: int,
    *,
    active: bool,
    reward_seconds: int = 0,
    now: datetime | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    current_time = now or datetime.utcnow()
    current_day = today or date.today()
    normalize_cat_world_play_time_day(state, current_day)
    earned_seconds = cat_world_play_time_earned_seconds(spelling_count, reward_seconds)
    used_seconds = max(int(state.play_time_used_seconds or 0), 0)
    if state.play_time_last_seen_at and earned_seconds > used_seconds:
        elapsed_seconds = max(int((current_time - state.play_time_last_seen_at).total_seconds()), 0)
        if elapsed_seconds <= CAT_WORLD_PLAY_TIME_HEARTBEAT_GRACE_SECONDS:
            used_seconds += min(elapsed_seconds, earned_seconds - used_seconds)
    state.play_time_used_seconds = min(used_seconds, max(earned_seconds, 20 * 60))
    remaining_seconds = max(earned_seconds - state.play_time_used_seconds, 0)
    state.play_time_last_seen_at = current_time if active and remaining_seconds > 0 else None
    return cat_world_play_time_payload(
        state,
        spelling_count,
        reward_seconds=reward_seconds,
        now=current_time,
        today=current_day,
    )


def parse_cat_world_inventory(raw: str | None) -> dict[str, int]:
    try:
        loaded = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    if not isinstance(loaded, dict):
        return {}
    inventory = {}
    for key, value in loaded.items():
        item_id = str(key)
        if item_id not in CAT_WORLD_SHOP_BY_ID:
            continue
        try:
            count = max(int(value or 0), 0)
        except (TypeError, ValueError):
            count = 0
        if count:
            inventory[item_id] = count
    return inventory


def parse_cat_world_damaged_items(raw: str | None) -> dict[str, dict[str, Any]]:
    try:
        loaded = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    if not isinstance(loaded, dict):
        return {}
    damaged: dict[str, dict[str, Any]] = {}
    for item_id, value in loaded.items():
        item_key = str(item_id)
        item = CAT_WORLD_SHOP_BY_ID.get(item_key)
        if not item or item.get("category") not in {"decor", "toy"}:
            continue
        source = value if isinstance(value, dict) else {}
        repair_cost = source.get("repairCost")
        try:
            repair_cost = max(int(repair_cost or round(int(item.get("cost") or 0) * 0.35)), 10)
        except (TypeError, ValueError):
            repair_cost = max(round(int(item.get("cost") or 0) * 0.35), 10)
        cat_id = cat_world_individual_state_key(source.get("catId"))
        cat = CAT_WORLD_CAT_BY_ID.get(cat_id)
        damaged[item_key] = {
            "itemId": item_key,
            "label": item.get("label") or item_key,
            "category": item.get("category") or "",
            "catId": cat_id,
            "catLabel": cat.get("label") if cat else str(source.get("catLabel") or ""),
            "repairCost": repair_cost,
            "reason": str(source.get("reason") or "猫咪捣蛋弄坏了它。"),
            "damagedAt": str(source.get("damagedAt") or ""),
        }
    return damaged


def encode_cat_world_damaged_items(damaged_items: dict[str, dict[str, Any]]) -> str:
    clean: dict[str, dict[str, Any]] = {}
    for item_id, value in damaged_items.items():
        item_key = str(item_id)
        item = CAT_WORLD_SHOP_BY_ID.get(item_key)
        if not item or item.get("category") not in {"decor", "toy"}:
            continue
        source = value if isinstance(value, dict) else {}
        try:
            repair_cost = max(int(source.get("repairCost") or round(int(item.get("cost") or 0) * 0.35)), 10)
        except (TypeError, ValueError):
            repair_cost = max(round(int(item.get("cost") or 0) * 0.35), 10)
        clean[item_key] = {
            "catId": str(source.get("catId") or ""),
            "catLabel": str(source.get("catLabel") or ""),
            "repairCost": repair_cost,
            "reason": str(source.get("reason") or "猫咪捣蛋弄坏了它。"),
            "damagedAt": str(source.get("damagedAt") or ""),
        }
    return json.dumps(clean, ensure_ascii=False, sort_keys=True)


def parse_cat_world_cats(raw: str | None) -> list[str]:
    raw_text = str(raw or "").strip()
    if not raw_text:
        return [CAT_WORLD_DEFAULT_CAT_ID]
    try:
        loaded = json.loads(raw_text)
    except json.JSONDecodeError:
        return [CAT_WORLD_DEFAULT_CAT_ID]
    if not isinstance(loaded, list):
        return [CAT_WORLD_DEFAULT_CAT_ID]
    cats = [str(item) for item in loaded if str(item) in CAT_WORLD_CAT_BY_ID]
    return list(dict.fromkeys(cats))


def encode_cat_world_inventory(inventory: dict[str, int]) -> str:
    clean = {}
    for item_id, count in inventory.items():
        if item_id not in CAT_WORLD_SHOP_BY_ID:
            continue
        try:
            normalized_count = max(int(count or 0), 0)
        except (TypeError, ValueError):
            normalized_count = 0
        if normalized_count:
            clean[item_id] = normalized_count
    return json.dumps(clean, ensure_ascii=False, sort_keys=True)


def encode_cat_world_cats(cats: list[str]) -> str:
    clean = [item for item in list(dict.fromkeys(cats)) if item in CAT_WORLD_CAT_BY_ID]
    return json.dumps(clean, ensure_ascii=False)


def cat_world_individual_state_key(value: Any) -> str:
    key = str(value or "").strip()
    if not key or len(key) > 80 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", key):
        return ""
    return key


def parse_cat_world_care(raw: str | None) -> dict[str, dict[str, Any]]:
    try:
        loaded = json.loads(raw or "{}")
    except json.JSONDecodeError:
        loaded = {}
    if not isinstance(loaded, dict):
        return {}
    care: dict[str, dict[str, Any]] = {}
    for cat_id, source in loaded.items():
        cat_key = cat_world_individual_state_key(cat_id)
        if not cat_key or not isinstance(source, dict):
            continue
        try:
            bath_count = max(int(source.get("bathCount") or 0), 0)
        except (TypeError, ValueError):
            bath_count = 0
        try:
            adoption_count = max(int(source.get("adoptionCount") or 0), 0)
        except (TypeError, ValueError):
            adoption_count = 0
        care[cat_key] = {
            "lastBathAt": str(source.get("lastBathAt") or ""),
            "bathCount": bath_count,
            "hungerSince": str(source.get("hungerSince") or ""),
            "lowMoodSince": str(source.get("lowMoodSince") or ""),
            "escapedAt": str(source.get("escapedAt") or ""),
            "escapeReason": str(source.get("escapeReason") or ""),
            "escapeLabel": str(source.get("escapeLabel") or ""),
            "adoptionCount": adoption_count,
        }
    return care


def encode_cat_world_care(care: dict[str, dict[str, Any]]) -> str:
    clean: dict[str, dict[str, Any]] = {}
    for cat_id, source in care.items():
        cat_key = cat_world_individual_state_key(cat_id)
        if not cat_key or not isinstance(source, dict):
            continue
        try:
            bath_count = max(int(source.get("bathCount") or 0), 0)
        except (TypeError, ValueError):
            bath_count = 0
        try:
            adoption_count = max(int(source.get("adoptionCount") or 0), 0)
        except (TypeError, ValueError):
            adoption_count = 0
        clean[cat_key] = {
            "lastBathAt": str(source.get("lastBathAt") or "").strip(),
            "bathCount": bath_count,
            "hungerSince": str(source.get("hungerSince") or "").strip(),
            "lowMoodSince": str(source.get("lowMoodSince") or "").strip(),
            "escapedAt": str(source.get("escapedAt") or "").strip(),
            "escapeReason": str(source.get("escapeReason") or "").strip(),
            "escapeLabel": str(source.get("escapeLabel") or "").strip(),
            "adoptionCount": adoption_count,
        }
    return json.dumps(clean, ensure_ascii=False, sort_keys=True)


def cat_world_clamp_bond_score(value: int | float) -> int:
    return int(min(max(round(float(value or 0)), 0), 100))


def cat_world_bond_level_label(score: int) -> str:
    if score >= 86:
        return "完全信任"
    if score >= 66:
        return "很亲近"
    if score >= 42:
        return "熟悉你"
    return "刚开始熟悉"


def cat_world_default_bond(cat_id: str) -> dict[str, Any]:
    return {
        "catId": cat_id,
        "score": 18,
        "totalGain": 0,
        "lastSource": "",
        "lastLabel": "",
        "lastGain": 0,
        "updatedAt": "",
        "sources": {},
    }


def parse_cat_world_bonds(raw: str | None) -> dict[str, dict[str, Any]]:
    try:
        loaded = json.loads(raw or "{}")
    except json.JSONDecodeError:
        loaded = {}
    if not isinstance(loaded, dict):
        loaded = {}
    bonds: dict[str, dict[str, Any]] = {}
    for cat_id, source in loaded.items():
        cat_key = cat_world_individual_state_key(cat_id)
        if not cat_key or not isinstance(source, dict):
            continue
        row = cat_world_default_bond(cat_key)
        source_counts = source.get("sources")
        clean_sources: dict[str, int] = {}
        if isinstance(source_counts, dict):
            for key, count in source_counts.items():
                try:
                    clean_sources[str(key)] = max(int(count or 0), 0)
                except (TypeError, ValueError):
                    continue
        try:
            total_gain = max(int(source.get("totalGain") or 0), 0)
        except (TypeError, ValueError):
            total_gain = 0
        try:
            last_gain = max(int(source.get("lastGain") or 0), 0)
        except (TypeError, ValueError):
            last_gain = 0
        row.update(
            {
                "score": cat_world_clamp_bond_score(source.get("score", row["score"])),
                "totalGain": total_gain,
                "lastSource": str(source.get("lastSource") or ""),
                "lastLabel": str(source.get("lastLabel") or ""),
                "lastGain": last_gain,
                "updatedAt": str(source.get("updatedAt") or ""),
                "sources": clean_sources,
            }
        )
        bonds[cat_key] = row
    return bonds


def encode_cat_world_bonds(bonds: dict[str, dict[str, Any]]) -> str:
    clean: dict[str, dict[str, Any]] = {}
    for cat_id, source in bonds.items():
        cat_key = cat_world_individual_state_key(cat_id)
        if not cat_key or not isinstance(source, dict):
            continue
        score = cat_world_clamp_bond_score(source.get("score", 18))
        try:
            total_gain = max(int(source.get("totalGain") or 0), 0)
        except (TypeError, ValueError):
            total_gain = 0
        source_counts = source.get("sources")
        clean_sources: dict[str, int] = {}
        if isinstance(source_counts, dict):
            for key, count in source_counts.items():
                try:
                    normalized_count = max(int(count or 0), 0)
                except (TypeError, ValueError):
                    continue
                if normalized_count:
                    clean_sources[str(key)] = normalized_count
        if total_gain <= 0 and score <= 18 and not clean_sources:
            continue
        try:
            last_gain = max(int(source.get("lastGain") or 0), 0)
        except (TypeError, ValueError):
            last_gain = 0
        clean[cat_key] = {
            "score": score,
            "totalGain": total_gain,
            "lastSource": str(source.get("lastSource") or ""),
            "lastLabel": str(source.get("lastLabel") or ""),
            "lastGain": last_gain,
            "updatedAt": str(source.get("updatedAt") or ""),
            "sources": clean_sources,
        }
    return json.dumps(clean, ensure_ascii=False, sort_keys=True)


def cat_world_bond_payload(raw_bonds: dict[str, dict[str, Any]], cat_ids: list[str] | None = None) -> dict[str, dict[str, Any]]:
    cat_ids = cat_ids or [cat["id"] for cat in CAT_WORLD_CATS]
    payload: dict[str, dict[str, Any]] = {}
    for cat_id in cat_ids:
        cat_id = cat_world_individual_state_key(cat_id)
        if not cat_id:
            continue
        row = {**cat_world_default_bond(cat_id), **raw_bonds.get(cat_id, {})}
        score = cat_world_clamp_bond_score(row.get("score", 18))
        last_gain = max(int(row.get("lastGain") or 0), 0)
        last_label = str(row.get("lastLabel") or "")
        payload[cat_id] = {
            **row,
            "score": score,
            "levelLabel": cat_world_bond_level_label(score),
            "detailLabel": f"最近 {last_label} +{last_gain}" if last_label and last_gain else "还没有照顾记录",
        }
    return payload


def cat_world_apply_cat_bond(
    state: CatWorldState,
    cat_id: str,
    amount: int,
    source: str,
    label: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    cat_id = cat_world_individual_state_key(cat_id)
    if not cat_id:
        cat_id = CAT_WORLD_DEFAULT_CAT_ID
    gain = max(int(amount or 0), 0)
    bonds = parse_cat_world_bonds(state.cat_bonds)
    row = {**cat_world_default_bond(cat_id), **bonds.get(cat_id, {})}
    old_score = cat_world_clamp_bond_score(row.get("score", 18))
    next_score = cat_world_clamp_bond_score(old_score + gain)
    source_key = str(source or "care")
    source_counts = row.get("sources") if isinstance(row.get("sources"), dict) else {}
    source_counts[source_key] = max(int(source_counts.get(source_key) or 0), 0) + gain
    row.update(
        {
            "score": next_score,
            "totalGain": max(int(row.get("totalGain") or 0), 0) + gain,
            "lastSource": source_key,
            "lastLabel": str(label or "照顾"),
            "lastGain": max(next_score - old_score, 0),
            "updatedAt": (now or datetime.utcnow()).replace(microsecond=0).isoformat() + "Z",
            "sources": source_counts,
        }
    )
    bonds[cat_id] = row
    state.cat_bonds = encode_cat_world_bonds(bonds)
    return cat_world_bond_payload(bonds, [cat_id])[cat_id]


def cat_world_shop_settings_map(db: Session) -> dict[str, int]:
    settings_rows = db.scalars(select(CatWorldShopSetting)).all()
    costs: dict[str, int] = {}
    for row in settings_rows:
        if row.item_id not in CAT_WORLD_SHOP_BY_ID:
            continue
        try:
            costs[row.item_id] = max(int(row.cost or 0), 0)
        except (TypeError, ValueError):
            continue
    return costs


def cat_world_clamp_movement_speed(value: Any) -> float:
    try:
        speed = float(value)
    except (TypeError, ValueError):
        speed = CAT_WORLD_DEFAULT_MOVEMENT_SPEED
    if not math.isfinite(speed):
        speed = CAT_WORLD_DEFAULT_MOVEMENT_SPEED
    speed = min(max(speed, CAT_WORLD_MIN_MOVEMENT_SPEED), CAT_WORLD_MAX_MOVEMENT_SPEED)
    return round(speed, 2)


def cat_world_movement_speed(db: Session) -> float:
    row = db.scalar(
        select(CatWorldGameSetting).where(
            CatWorldGameSetting.setting_key == CAT_WORLD_MOVEMENT_SPEED_SETTING_KEY
        )
    )
    return cat_world_clamp_movement_speed(row.setting_value if row else CAT_WORLD_DEFAULT_MOVEMENT_SPEED)


def save_cat_world_movement_speed(db: Session, value: Any) -> float:
    speed = cat_world_clamp_movement_speed(value)
    row = db.scalar(
        select(CatWorldGameSetting).where(
            CatWorldGameSetting.setting_key == CAT_WORLD_MOVEMENT_SPEED_SETTING_KEY
        )
    )
    if not row:
        row = CatWorldGameSetting(setting_key=CAT_WORLD_MOVEMENT_SPEED_SETTING_KEY, setting_value=f"{speed:.2f}")
        db.add(row)
    else:
        row.setting_value = f"{speed:.2f}"
    return speed


def cat_world_clamp_gender_weight(value: Any, fallback: int = CAT_WORLD_DEFAULT_GENDER_WEIGHT) -> int:
    try:
        weight = int(value)
    except (TypeError, ValueError):
        weight = fallback
    return min(max(weight, CAT_WORLD_MIN_GENDER_WEIGHT), CAT_WORLD_MAX_GENDER_WEIGHT)


def cat_world_game_setting_value(db: Session, setting_key: str, fallback: str) -> str:
    row = db.scalar(
        select(CatWorldGameSetting).where(CatWorldGameSetting.setting_key == setting_key)
    )
    return str(row.setting_value if row else fallback)


def save_cat_world_game_setting(db: Session, setting_key: str, value: str) -> None:
    row = db.scalar(
        select(CatWorldGameSetting).where(CatWorldGameSetting.setting_key == setting_key)
    )
    if not row:
        db.add(CatWorldGameSetting(setting_key=setting_key, setting_value=value))
    else:
        row.setting_value = value


def cat_world_gender_draw_weights(db: Session) -> dict[str, Any]:
    male = cat_world_clamp_gender_weight(
        cat_world_game_setting_value(
            db,
            CAT_WORLD_MALE_WEIGHT_SETTING_KEY,
            str(CAT_WORLD_DEFAULT_GENDER_WEIGHT),
        )
    )
    female = cat_world_clamp_gender_weight(
        cat_world_game_setting_value(
            db,
            CAT_WORLD_FEMALE_WEIGHT_SETTING_KEY,
            str(CAT_WORLD_DEFAULT_GENDER_WEIGHT),
        )
    )
    if male + female <= 0:
        male = CAT_WORLD_DEFAULT_GENDER_WEIGHT
        female = CAT_WORLD_DEFAULT_GENDER_WEIGHT
    total = male + female
    return {
        "male": male,
        "female": female,
        "malePercent": round(male / total * 100, 1),
        "femalePercent": round(female / total * 100, 1),
    }


def save_cat_world_gender_draw_weights(db: Session, male_value: Any, female_value: Any) -> dict[str, Any]:
    male = cat_world_clamp_gender_weight(male_value)
    female = cat_world_clamp_gender_weight(female_value)
    if male + female <= 0:
        raise HTTPException(status_code=400, detail="公猫和母猫的抽取系数不能同时为 0。")
    save_cat_world_game_setting(db, CAT_WORLD_MALE_WEIGHT_SETTING_KEY, str(male))
    save_cat_world_game_setting(db, CAT_WORLD_FEMALE_WEIGHT_SETTING_KEY, str(female))
    total = male + female
    return {
        "male": male,
        "female": female,
        "malePercent": round(male / total * 100, 1),
        "femalePercent": round(female / total * 100, 1),
    }


def cat_world_game_settings_payload(db: Session) -> dict[str, Any]:
    return {
        "movementSpeed": cat_world_movement_speed(db),
        "genderDrawWeights": cat_world_gender_draw_weights(db),
        "defaults": {
            "movementSpeed": CAT_WORLD_DEFAULT_MOVEMENT_SPEED,
            "genderDrawWeights": {
                "male": CAT_WORLD_DEFAULT_GENDER_WEIGHT,
                "female": CAT_WORLD_DEFAULT_GENDER_WEIGHT,
            },
        },
        "limits": {
            "movementSpeed": {
                "min": CAT_WORLD_MIN_MOVEMENT_SPEED,
                "max": CAT_WORLD_MAX_MOVEMENT_SPEED,
                "step": CAT_WORLD_MOVEMENT_SPEED_STEP,
            },
            "genderDrawWeight": {
                "min": CAT_WORLD_MIN_GENDER_WEIGHT,
                "max": CAT_WORLD_MAX_GENDER_WEIGHT,
                "step": CAT_WORLD_GENDER_WEIGHT_STEP,
            },
        },
    }


def cat_world_effective_shop(db: Session) -> list[dict[str, Any]]:
    override_costs = cat_world_shop_settings_map(db)
    items = []
    for item in CAT_WORLD_SHOP:
        effective = {**item, "defaultCost": int(item["cost"])}
        if item["id"] in override_costs:
            effective["cost"] = override_costs[item["id"]]
            effective["hasCustomCost"] = effective["cost"] != effective["defaultCost"]
        else:
            effective["hasCustomCost"] = False
        if effective.get("targetDecor"):
            effective["targetDecorLabel"] = CAT_WORLD_DECOR_LABELS.get(str(effective["targetDecor"]), "")
        favorite_cat_id = cat_world_item_favorite_cat_id(effective["id"])
        if favorite_cat_id:
            effective["favoriteCatId"] = favorite_cat_id
            effective["favoriteCatLabel"] = CAT_WORLD_CAT_BY_ID.get(favorite_cat_id, {}).get("label", favorite_cat_id)
        items.append(effective)
    return items


def cat_world_effective_shop_by_id(db: Session) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in cat_world_effective_shop(db)}


def parse_cat_world_room_styles(raw: str | None, inventory: dict[str, int] | None = None) -> dict[str, str]:
    try:
        loaded = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    if not isinstance(loaded, dict):
        return {}
    inventory = inventory or {}
    styles: dict[str, str] = {}
    for decor_id, tone in loaded.items():
        decor_key = str(decor_id)
        tone_key = str(tone)
        if decor_key not in CAT_WORLD_DECOR_LABELS:
            continue
        if tone_key == "default":
            styles[decor_key] = tone_key
            continue
        if any(
            item.get("category") == "color"
            and item.get("targetDecor") == decor_key
            and item.get("tone") == tone_key
            and inventory.get(item["id"], 0) > 0
            for item in CAT_WORLD_SHOP
        ):
            styles[decor_key] = tone_key
    return styles


def encode_cat_world_room_styles(styles: dict[str, str]) -> str:
    clean = {
        decor_id: tone
        for decor_id, tone in styles.items()
        if decor_id in CAT_WORLD_DECOR_LABELS and str(tone).strip()
    }
    return json.dumps(clean, ensure_ascii=False, sort_keys=True)


def normalize_cat_world_room_position(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    try:
        x = float(value.get("x"))
        y = float(value.get("y"))
    except (TypeError, ValueError):
        return None
    return {
        "x": round(min(max(x, 0.0), 92.0), 2),
        "y": round(min(max(y, 0.0), 86.0), 2),
    }


def cat_world_layout_item_allowed(item_id: str, item_rules: dict[str, Any] | None = None) -> bool:
    item = CAT_WORLD_SHOP_BY_ID.get(item_id, {})
    category = str(item.get("category") or "")
    rules = item_rules if isinstance(item_rules, dict) else {}
    allowed_categories = {str(value) for value in rules.get("allowedCategories", []) if str(value).strip()}
    allowed_item_ids = {str(value) for value in rules.get("allowedItemIds", []) if str(value).strip()}
    excluded_item_ids = {str(value) for value in rules.get("excludedItemIds", []) if str(value).strip()}
    if item_id in excluded_item_ids:
        return False
    if allowed_item_ids and item_id not in allowed_item_ids:
        return False
    return not allowed_categories or category in allowed_categories


def parse_cat_world_room_layout(
    raw: str | None,
    inventory: dict[str, int] | None = None,
    default_layout: dict[str, Any] | None = None,
    item_rules: dict[str, Any] | None = None,
) -> dict[str, dict[str, float]]:
    try:
        loaded = json.loads(raw or "{}")
    except json.JSONDecodeError:
        loaded = {}
    if not isinstance(loaded, dict):
        loaded = {}
    inventory = inventory or {}
    owned_layout_item_ids = [
        item_id
        for item_id, count in inventory.items()
        if count > 0 and CAT_WORLD_SHOP_BY_ID.get(item_id, {}).get("category") in {"decor", "toy"}
        and cat_world_layout_item_allowed(item_id, item_rules)
    ]
    layout: dict[str, dict[str, float]] = {}
    scene_default_layout = default_layout if isinstance(default_layout, dict) else CAT_WORLD_ROOM_DEFAULT_LAYOUT
    for item_id in owned_layout_item_ids:
        default_position = scene_default_layout.get(item_id, CAT_WORLD_ROOM_DEFAULT_LAYOUT.get(item_id, {"x": 8, "y": 58}))
        layout[item_id] = {
            "x": float(default_position["x"]),
            "y": float(default_position["y"]),
        }
        custom_position = normalize_cat_world_room_position(loaded.get(item_id))
        if custom_position:
            layout[item_id] = custom_position
    return layout


def encode_cat_world_room_layout(layout: dict[str, Any]) -> str:
    clean: dict[str, dict[str, float]] = {}
    for item_id, position in layout.items():
        if item_id not in CAT_WORLD_LAYOUT_ITEM_LABELS:
            continue
        normalized = normalize_cat_world_room_position(position)
        if normalized:
            clean[item_id] = normalized
    return json.dumps(clean, ensure_ascii=False, sort_keys=True)


def parse_cat_world_scene_json(raw: str | None, fallback: Any) -> Any:
    try:
        loaded = json.loads(raw or "")
    except (json.JSONDecodeError, TypeError):
        return fallback
    return loaded if isinstance(loaded, type(fallback)) else fallback


def seed_cat_world_scenes(db: Session) -> None:
    existing_rows = {row.scene_key: row for row in db.scalars(select(CatWorldScene)).all()}
    changed = False
    for seed in CAT_WORLD_SCENE_SEEDS:
        scene_key = str(seed["sceneKey"])
        existing_row = existing_rows.get(scene_key)
        if existing_row:
            existing_config = parse_cat_world_scene_json(existing_row.config, {})
            config_changed = False
            if seed.get("camera") and not isinstance(existing_config.get("camera"), dict):
                existing_config["camera"] = seed["camera"]
                config_changed = True
            if "purchasable" not in existing_config:
                existing_config.update(
                    {
                        "description": str(seed.get("description") or ""),
                        "purchasable": bool(seed.get("purchasable")),
                        "purchaseCost": max(int(seed.get("purchaseCost") or 0), 0),
                        "unlockByDefault": bool(seed.get("unlockByDefault", scene_key == CAT_WORLD_DEFAULT_SCENE_KEY)),
                    }
                )
                if seed.get("purchasable"):
                    existing_row.is_enabled = bool(seed.get("isEnabled"))
                config_changed = True
            if config_changed:
                existing_row.config = json.dumps(existing_config, ensure_ascii=False, sort_keys=True)
                changed = True
            target_width = int(seed["world"]["width"])
            if int(existing_row.world_width or 0) < target_width:
                existing_row.world_width = target_width
                changed = True
            continue
        world = seed["world"]
        config = {
            "palette": seed.get("palette") or {},
            "features": seed.get("features") or {},
            "itemRules": seed.get("itemRules") or {},
            "spawnPoints": seed.get("spawnPoints") or {},
            "portals": seed.get("portals") or [],
            "camera": seed.get("camera") or {},
            "description": str(seed.get("description") or ""),
            "purchasable": bool(seed.get("purchasable")),
            "purchaseCost": max(int(seed.get("purchaseCost") or 0), 0),
            "unlockByDefault": bool(seed.get("unlockByDefault", True)),
        }
        db.add(
            CatWorldScene(
                scene_key=scene_key,
                label=str(seed["label"]),
                english_name=str(seed["englishName"]),
                scene_type=str(seed.get("sceneType") or "indoor"),
                world_width=int(world["width"]),
                world_height=int(world["height"]),
                viewport_width=int(world["viewportWidth"]),
                viewport_height=int(world["viewportHeight"]),
                floor_top=int(world["floorTop"]),
                floor_bottom=int(world["floorBottom"]),
                config=json.dumps(config, ensure_ascii=False, sort_keys=True),
                default_layout=encode_cat_world_room_layout(seed.get("defaultLayout") or {}),
                is_enabled=bool(seed.get("isEnabled")),
                sort_order=int(seed.get("sortOrder") or 0),
            )
        )
        changed = True
    if changed:
        db.commit()


def seed_cat_world_limited_cat_stock(db: Session) -> None:
    existing = {
        (row.series_key, row.cat_id): row
        for row in db.scalars(select(CatWorldLimitedCatStock)).all()
    }
    changed = False
    for seed in CAT_WORLD_LIMITED_CAT_SEEDS:
        series_key = str(seed["seriesKey"])
        cat_id = str(seed["cat"]["id"])
        if (series_key, cat_id) in existing:
            continue
        db.add(
            CatWorldLimitedCatStock(
                series_key=series_key,
                cat_id=cat_id,
                total_stock=max(int(seed.get("totalStock") or 0), 0),
                claimed_count=0,
                is_active=True,
            )
        )
        changed = True
    if changed:
        db.commit()


def cat_world_scene_row(db: Session, scene_key: str | None = None, enabled_only: bool = False) -> CatWorldScene | None:
    normalized = str(scene_key or CAT_WORLD_DEFAULT_SCENE_KEY).strip() or CAT_WORLD_DEFAULT_SCENE_KEY
    statement = select(CatWorldScene).where(CatWorldScene.scene_key == normalized)
    if enabled_only:
        statement = statement.where(CatWorldScene.is_enabled.is_(True))
    row = db.scalar(statement)
    if row or normalized == CAT_WORLD_DEFAULT_SCENE_KEY:
        return row
    fallback = select(CatWorldScene).where(CatWorldScene.scene_key == CAT_WORLD_DEFAULT_SCENE_KEY)
    if enabled_only:
        fallback = fallback.where(CatWorldScene.is_enabled.is_(True))
    return db.scalar(fallback)


def cat_world_scene_config(scene: CatWorldScene) -> dict[str, Any]:
    extra = parse_cat_world_scene_json(scene.config, {})
    default_layout = parse_cat_world_scene_json(scene.default_layout, {})
    return {
        "id": scene.scene_key,
        "label": scene.label,
        "englishName": scene.english_name,
        "type": scene.scene_type,
        "enabled": bool(scene.is_enabled),
        "sortOrder": int(scene.sort_order or 0),
        "world": {
            "width": max(int(scene.world_width or 1600), 960),
            "height": max(int(scene.world_height or 560), 420),
            "viewportWidth": max(int(scene.viewport_width or 1280), 720),
            "viewportHeight": max(int(scene.viewport_height or 560), 420),
            "floorTop": max(int(scene.floor_top or 260), 120),
            "floorBottom": max(int(scene.floor_bottom or 522), 240),
        },
        "palette": extra.get("palette") if isinstance(extra.get("palette"), dict) else {},
        "features": extra.get("features") if isinstance(extra.get("features"), dict) else {},
        "itemRules": extra.get("itemRules") if isinstance(extra.get("itemRules"), dict) else {},
        "spawnPoints": extra.get("spawnPoints") if isinstance(extra.get("spawnPoints"), dict) else {},
        "portals": extra.get("portals") if isinstance(extra.get("portals"), list) else [],
        "camera": extra.get("camera") if isinstance(extra.get("camera"), dict) else {},
        "description": str(extra.get("description") or ""),
        "purchasable": bool(extra.get("purchasable")),
        "purchaseCost": max(int(extra.get("purchaseCost") or 0), 0),
        "unlockByDefault": bool(extra.get("unlockByDefault", True)),
        "defaultLayout": default_layout,
    }


def get_or_create_cat_world_user_scene(
    db: Session,
    state: CatWorldState,
    scene: CatWorldScene,
) -> tuple[CatWorldUserScene, bool]:
    row = db.scalar(
        select(CatWorldUserScene).where(
            CatWorldUserScene.phone == state.phone,
            CatWorldUserScene.scene_key == scene.scene_key,
        )
    )
    if row:
        return row, False
    is_default_scene = scene.scene_key == CAT_WORLD_DEFAULT_SCENE_KEY
    config = cat_world_scene_config(scene)
    row = CatWorldUserScene(
        phone=state.phone,
        scene_key=scene.scene_key,
        layout=state.room_layout if is_default_scene else encode_cat_world_room_layout({}),
        room_styles=state.room_styles if is_default_scene else encode_cat_world_room_styles({}),
        is_unlocked=is_default_scene or bool(config.get("unlockByDefault")),
        unlocked_at=datetime.utcnow() if is_default_scene or bool(config.get("unlockByDefault")) else None,
        last_visited_at=datetime.utcnow() if is_default_scene else None,
    )
    db.add(row)
    db.flush()
    return row, True


def cat_world_active_scene_context(
    db: Session,
    state: CatWorldState,
) -> tuple[CatWorldScene, CatWorldUserScene, dict[str, Any]]:
    scene = cat_world_scene_row(db, state.current_scene_key, enabled_only=True)
    if not scene:
        raise HTTPException(status_code=500, detail="猫咪世界还没有可用场景配置。")
    if state.current_scene_key != scene.scene_key:
        state.current_scene_key = scene.scene_key
        db.add(state)
    user_scene, _ = get_or_create_cat_world_user_scene(db, state, scene)
    return scene, user_scene, cat_world_scene_config(scene)


def cat_world_active_scene_layout(
    db: Session,
    state: CatWorldState,
    inventory: dict[str, int],
) -> dict[str, dict[str, float]]:
    _, user_scene, config = cat_world_active_scene_context(db, state)
    return parse_cat_world_room_layout(
        user_scene.layout,
        inventory,
        config.get("defaultLayout"),
        config.get("itemRules"),
    )


def cat_world_active_scene_styles(
    db: Session,
    state: CatWorldState,
    inventory: dict[str, int],
) -> dict[str, str]:
    _, user_scene, _ = cat_world_active_scene_context(db, state)
    return parse_cat_world_room_styles(user_scene.room_styles, inventory)


def save_cat_world_active_scene_layout(
    state: CatWorldState,
    user_scene: CatWorldUserScene,
    layout: dict[str, Any],
) -> None:
    encoded = encode_cat_world_room_layout(layout)
    user_scene.layout = encoded
    user_scene.last_visited_at = datetime.utcnow()
    if user_scene.scene_key == CAT_WORLD_DEFAULT_SCENE_KEY:
        state.room_layout = encoded


def save_cat_world_active_scene_styles(
    state: CatWorldState,
    user_scene: CatWorldUserScene,
    styles: dict[str, str],
) -> None:
    encoded = encode_cat_world_room_styles(styles)
    user_scene.room_styles = encoded
    user_scene.last_visited_at = datetime.utcnow()
    if user_scene.scene_key == CAT_WORLD_DEFAULT_SCENE_KEY:
        state.room_styles = encoded


def cat_world_scene_catalog_payload(db: Session, state: CatWorldState) -> list[dict[str, Any]]:
    rows = db.scalars(select(CatWorldScene).order_by(CatWorldScene.sort_order, CatWorldScene.id)).all()
    user_rows = {
        row.scene_key: row
        for row in db.scalars(select(CatWorldUserScene).where(CatWorldUserScene.phone == state.phone)).all()
    }
    payload: list[dict[str, Any]] = []
    for row in rows:
        config = cat_world_scene_config(row)
        user_row = user_rows.get(row.scene_key)
        unlocked = bool(user_row.is_unlocked) if user_row else bool(config.get("unlockByDefault"))
        payload.append({**config, "unlocked": unlocked, "available": bool(row.is_enabled and unlocked)})
    return payload


def cat_world_blind_box_catalog_payload(
    db: Session,
    state: CatWorldState,
    owned_cat_ids: list[str] | None = None,
) -> dict[str, Any]:
    owned = set(owned_cat_ids or [])
    stock_rows = {
        (row.series_key, row.cat_id): row
        for row in db.scalars(select(CatWorldLimitedCatStock)).all()
    }
    draws = {
        row.series_key: row
        for row in db.scalars(
            select(CatWorldBlindBoxDraw).where(CatWorldBlindBoxDraw.phone == state.phone)
        ).all()
    }
    series_payload = []
    for series in CAT_WORLD_BLIND_BOX_SERIES:
        cat_rows = []
        for seed in series["cats"]:
            cat = seed["cat"]
            stock = stock_rows.get((series["key"], cat["id"]))
            total = max(int(stock.total_stock if stock else seed.get("totalStock") or 0), 0)
            claimed = min(max(int(stock.claimed_count if stock else 0), 0), total)
            remaining = max(total - claimed, 0) if stock is None or stock.is_active else 0
            cat_rows.append(
                {
                    **cat_world_cat_payload(cat),
                    "total": total,
                    "claimed": claimed,
                    "remaining": remaining,
                    "owned": cat["id"] in owned,
                    "oddsPercent": round((int(seed.get("totalStock") or 0) / max(sum(int(item.get("totalStock") or 0) for item in series["cats"]), 1)) * 100, 1),
                }
            )
        draw = draws.get(series["key"])
        series_payload.append(
            {
                "key": series["key"],
                "label": series["label"],
                "region": series["region"],
                "issue": series["issue"],
                "description": series["description"],
                "shopItemId": series["shopItemId"],
                "drawn": bool(draw),
                "drawnCatId": draw.cat_id if draw else "",
                "drawnAt": draw.created_at.isoformat() if draw and draw.created_at else "",
                "totalStock": sum(row["total"] for row in cat_rows),
                "remainingStock": sum(row["remaining"] for row in cat_rows),
                "cats": cat_rows,
            }
        )
    return {
        "currentSeriesKey": CAT_WORLD_CURRENT_BLIND_BOX_SERIES_KEY,
        "series": series_payload,
    }


def cat_world_collection_catalog_payload(
    blind_box_catalog: dict[str, Any],
    owned_cat_ids: list[str] | None = None,
) -> dict[str, Any]:
    owned = set(owned_cat_ids or [])
    resident_cats = [
        {
            **cat_world_cat_payload(cat),
            "owned": cat["id"] in owned,
            "collectionTag": "初始伙伴" if cat["id"] == CAT_WORLD_DEFAULT_CAT_ID else "常驻名猫",
            "acquisitionHint": "进入猫咪世界即可获得"
            if cat["id"] == CAT_WORLD_DEFAULT_CAT_ID
            else "可在名猫商店领养",
        }
        for cat in CAT_WORLD_CATS
        if not cat.get("limited")
    ]
    sections: list[dict[str, Any]] = [
        {
            "key": "resident-cats",
            "label": "猫咪世界常驻伙伴",
            "region": "猫咪世界",
            "description": "初始伙伴和可以在名猫商店长期领养的猫咪。",
            "ownedCount": sum(1 for cat in resident_cats if cat["owned"]),
            "totalCount": len(resident_cats),
            "completed": bool(resident_cats) and all(cat["owned"] for cat in resident_cats),
            "badge": None,
            "cats": resident_cats,
        }
    ]
    region_sections: dict[str, dict[str, Any]] = {}
    region_cat_ids: dict[str, set[str]] = {}
    for series in blind_box_catalog.get("series") or []:
        region = str(series.get("region") or "地区限定")
        region_key = region.lower().replace(" ", "-")
        section = region_sections.setdefault(
            region,
            {
                "key": f"region-{region_key}",
                "label": f"{region}限定猫咪",
                "region": region,
                "description": f"收集来自{region}各期盲盒的限定猫咪，集齐后点亮地区徽章。",
                "cats": [],
            },
        )
        seen_cat_ids = region_cat_ids.setdefault(region, set())
        for cat in series.get("cats") or []:
            cat_id = str(cat.get("id") or "")
            if not cat_id or cat_id in seen_cat_ids:
                continue
            seen_cat_ids.add(cat_id)
            section["cats"].append(
                {
                    **cat,
                    "collectionTag": f"{region}限定",
                    "acquisitionHint": f"{series.get('issue') or '限定期'}盲盒",
                }
            )
    for section in region_sections.values():
        section_cats = section["cats"]
        completed = bool(section_cats) and all(bool(cat.get("owned")) for cat in section_cats)
        section.update(
            {
                "ownedCount": sum(1 for cat in section_cats if cat.get("owned")),
                "totalCount": len(section_cats),
                "completed": completed,
                "badge": {
                    "label": f"{section['region']}猫咪收藏家",
                    "unlocked": completed,
                },
            }
        )
        sections.append(section)
    all_cat_ids = {str(cat["id"]) for cat in CAT_WORLD_CATS}
    return {
        "ownedCount": len(all_cat_ids.intersection(owned)),
        "totalCount": len(all_cat_ids),
        "sections": sections,
    }


def cat_world_owned_style_options(inventory: dict[str, int], decor_id: str) -> list[dict[str, str]]:
    options = [{"itemId": "default", "tone": "default", "label": "默认色"}]
    for item in CAT_WORLD_SHOP:
        if item.get("category") != "color" or item.get("targetDecor") != decor_id:
            continue
        if inventory.get(item["id"], 0) > 0:
            options.append({"itemId": item["id"], "tone": str(item.get("tone") or ""), "label": item["label"]})
    return options


def cat_world_selected_cat(state: CatWorldState) -> dict[str, Any]:
    return CAT_WORLD_CAT_BY_ID.get(state.selected_cat) or CAT_WORLD_CAT_BY_ID[CAT_WORLD_DEFAULT_CAT_ID]


def cat_world_cat_traits(cat: dict[str, Any] | None) -> dict[str, Any]:
    raw_traits = (cat or {}).get("traits") if isinstance(cat, dict) else {}
    raw_traits = raw_traits if isinstance(raw_traits, dict) else {}
    defaults = {
        "activity": "balanced",
        "movement": 1.0,
        "energyDrain": 1.0,
        "moodDrain": 1.0,
        "playMoodGain": 1.0,
        "foodEnergyGain": 1.0,
        "restThreshold": 34,
        "sleepStart": 23,
        "sleepEnd": 7,
        "nightOwl": False,
        "routine": "观察房间里的学习节奏",
        "temperament": "balanced",
        "label": "均衡型猫咪，心情和体力消耗都比较稳定。",
    }
    traits = {**defaults, **raw_traits}
    for key in ("movement", "energyDrain", "moodDrain", "playMoodGain", "foodEnergyGain"):
        try:
            traits[key] = round(min(max(float(traits[key]), 0.35), 1.8), 2)
        except (TypeError, ValueError):
            traits[key] = defaults[key]
    try:
        traits["restThreshold"] = int(min(max(int(traits["restThreshold"]), 18), 60))
    except (TypeError, ValueError):
        traits["restThreshold"] = defaults["restThreshold"]
    for key in ("sleepStart", "sleepEnd"):
        try:
            traits[key] = int(min(max(int(traits[key]), 0), 23))
        except (TypeError, ValueError):
            traits[key] = defaults[key]
    traits["nightOwl"] = bool(traits.get("nightOwl"))
    traits["activity"] = str(traits["activity"] or defaults["activity"])
    traits["routine"] = str(traits["routine"] or defaults["routine"])
    traits["temperament"] = str(traits["temperament"] or defaults["temperament"])
    traits["label"] = str(traits["label"] or defaults["label"])
    return traits


def cat_world_cat_favorite_decor_ids(cat_id: str) -> list[str]:
    favorites = [
        decor_id
        for decor_id, favorite_cat_id in CAT_WORLD_DECOR_FAVORITE_CAT.items()
        if favorite_cat_id == cat_id
    ]
    favorites.extend(CAT_WORLD_EXTRA_DECOR_FAVORITES.get(str(cat_id or ""), []))
    return list(dict.fromkeys(favorites))


def cat_world_item_favorite_cat_id(item_id: str) -> str:
    favorite_cat_id = CAT_WORLD_ITEM_FAVORITE_CAT.get(str(item_id) or "")
    return favorite_cat_id if favorite_cat_id in CAT_WORLD_CAT_BY_ID else ""


def cat_world_food_favorite_multiplier(item: dict[str, Any], cat_id: str) -> float:
    if item.get("category") != "food" or cat_world_item_favorite_cat_id(item.get("id") or "") != str(cat_id or ""):
        return 1.0
    try:
        multiplier = float(item.get("favoriteEnergyMultiplier") or 1.18)
    except (TypeError, ValueError):
        multiplier = 1.18
    return min(max(multiplier, 1.0), 2.0)


def cat_world_cat_favorite_item_ids(cat_id: str, categories: set[str] | None = None) -> list[str]:
    clean_cat_id = str(cat_id or "")
    favorite_ids = []
    for item_id, favorite_cat_id in CAT_WORLD_ITEM_FAVORITE_CAT.items():
        if favorite_cat_id != clean_cat_id:
            continue
        item = CAT_WORLD_SHOP_BY_ID.get(item_id)
        if not item:
            continue
        if categories and item.get("category") not in categories:
            continue
        favorite_ids.append(item_id)
    return favorite_ids


def cat_world_active_favorite_decor_ids(
    cat_id: str,
    inventory: dict[str, int],
    room_layout: dict[str, dict[str, float]],
) -> list[str]:
    favorites = cat_world_cat_favorite_decor_ids(cat_id)
    return [
        decor_id
        for decor_id in favorites
        if inventory.get(decor_id, 0) > 0 and decor_id in room_layout
    ]


def cat_world_decay_rates(
    traits: dict[str, Any],
    inventory: dict[str, int],
    favorite_count: int,
) -> tuple[int, int, int]:
    owned_toys = sum(
        1
        for item_id, count in inventory.items()
        if count > 0 and CAT_WORLD_SHOP_BY_ID.get(item_id, {}).get("category") == "toy"
    )
    owned_decor = sum(
        1
        for item_id, count in inventory.items()
        if count > 0 and CAT_WORLD_SHOP_BY_ID.get(item_id, {}).get("category") == "decor"
    )
    relief = min(owned_toys, 2) + min(owned_decor // 2, 2) + min(favorite_count * 2, 4)
    mood_decay = max(1, round(4 * float(traits["movement"]) * float(traits["moodDrain"])) - relief)
    energy_decay = max(1, round(5 * float(traits["movement"]) * float(traits["energyDrain"])) - relief)
    return mood_decay, energy_decay, relief


def clamp_cat_world_score(value: int | float, minimum: int = 5, maximum: int = 100) -> int:
    return int(min(max(round(float(value)), minimum), maximum))


def cat_world_local_now(now: datetime | None = None) -> datetime:
    base_now = now or datetime.utcnow()
    return base_now + timedelta(hours=8)


def cat_world_local_time_label(now: datetime | None = None) -> str:
    return cat_world_local_now(now).strftime("%H:%M")


def cat_world_routine_period(now: datetime | None = None) -> tuple[str, str]:
    hour = cat_world_local_now(now).hour
    if 5 <= hour < 11:
        return "morning", "早晨"
    if 11 <= hour < 17:
        return "afternoon", "午后"
    if 17 <= hour < 22:
        return "evening", "傍晚"
    return "night", "夜间"


def cat_world_is_sleep_hour(hour: int, sleep_start: int, sleep_end: int) -> bool:
    if sleep_start == sleep_end:
        return False
    if sleep_start < sleep_end:
        return sleep_start <= hour < sleep_end
    return hour >= sleep_start or hour < sleep_end


def cat_world_is_wake_transition(now: datetime, traits: dict[str, Any]) -> bool:
    if bool(traits.get("nightOwl")):
        return False
    sleep_start = int(traits.get("sleepStart") or 23)
    sleep_end = int(traits.get("sleepEnd") or 7)
    local_now = cat_world_local_now(now)
    return (
        cat_world_is_sleep_hour((local_now - timedelta(hours=1)).hour, sleep_start, sleep_end)
        and not cat_world_is_sleep_hour(local_now.hour, sleep_start, sleep_end)
    )


def cat_world_stable_ratio(seed: str) -> float:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(0xFFFFFFFFFFFF)


def cat_world_agent_event(kind: str, label: str, message: str, now: datetime | None = None) -> dict[str, str]:
    return {
        "kind": str(kind or "note"),
        "time": cat_world_local_time_label(now),
        "label": str(label or "状态记录"),
        "message": str(message or ""),
    }


def cat_world_trim_agent_events(events: Any) -> list[dict[str, str]]:
    if not isinstance(events, list):
        return []
    clean: list[dict[str, str]] = []
    for event in events[-10:]:
        if not isinstance(event, dict):
            continue
        message = str(event.get("message") or "").strip()
        if not message:
            continue
        clean.append(
            {
                "kind": str(event.get("kind") or "note"),
                "time": str(event.get("time") or ""),
                "label": str(event.get("label") or "状态记录"),
                "message": message,
            }
        )
    return clean[-8:]


def cat_world_trim_hourly_history(history: Any) -> list[dict[str, Any]]:
    if not isinstance(history, list):
        return []
    clean: list[dict[str, Any]] = []
    for row in history[-36:]:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or "").strip()
        if not label:
            continue
        clean.append(
            {
                "time": str(row.get("time") or ""),
                "label": label,
                "reason": str(row.get("reason") or ""),
                "energyDelta": int(row.get("energyDelta") or 0),
                "moodDelta": int(row.get("moodDelta") or 0),
                "energyScore": clamp_cat_world_score(int(row.get("energyScore") or 0)),
                "moodScore": clamp_cat_world_score(int(row.get("moodScore") or 0)),
                "hours": max(int(row.get("hours") or 1), 1),
            }
        )
    return clean[-24:]


def cat_world_hourly_history_entry(
    hour_at: datetime,
    hourly_change: dict[str, Any],
    energy_delta: int,
    mood_delta: int,
    energy_score: int,
    mood_score: int,
    hours: int = 1,
) -> dict[str, Any]:
    return {
        "time": cat_world_local_now(hour_at).strftime("%m-%d %H:00"),
        "label": str(hourly_change.get("label") or "小时变化"),
        "reason": str(hourly_change.get("reason") or ""),
        "energyDelta": int(energy_delta),
        "moodDelta": int(mood_delta),
        "energyScore": clamp_cat_world_score(energy_score),
        "moodScore": clamp_cat_world_score(mood_score),
        "hours": max(int(hours or 1), 1),
    }


def parse_cat_world_agent_state(raw: str | None) -> dict[str, Any]:
    try:
        loaded = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def encode_cat_world_agent_state(state: dict[str, Any]) -> str:
    state["events"] = cat_world_trim_agent_events(state.get("events"))
    state["hourlyHistory"] = cat_world_trim_hourly_history(state.get("hourlyHistory"))
    return json.dumps(state, ensure_ascii=False, sort_keys=True)


CAT_WORLD_DAILY_MOODS = [
    {"key": "bright", "label": "今天很高兴", "moodOffset": 8, "energyOffset": 4},
    {"key": "curious", "label": "今天想探索", "moodOffset": 4, "energyOffset": 7},
    {"key": "clingy", "label": "今天有点黏人", "moodOffset": 5, "energyOffset": -1},
    {"key": "lazy", "label": "今天想慢慢来", "moodOffset": 0, "energyOffset": -6},
    {"key": "quiet", "label": "今天想独处", "moodOffset": -4, "energyOffset": 0},
    {"key": "grumpy", "label": "今天不太高兴", "moodOffset": -10, "energyOffset": -3},
]


def cat_world_daily_agent_seed(log_date: date, cat_id: str, phone: str | None = "") -> str:
    normalized_phone = normalize_login_phone(phone)
    owner_key = hashlib.sha256(normalized_phone.encode("utf-8")).hexdigest()[:12] if normalized_phone else "global"
    return f"{log_date.isoformat()}:{cat_id}:{owner_key}:agent"


def cat_world_daily_agent_seed_key(log_date: date, cat_id: str, phone: str | None = "") -> str:
    seed = cat_world_daily_agent_seed(log_date, cat_id, phone)
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


def cat_world_agent_score(value: int | float) -> int:
    return int(min(max(round(float(value)), 8), 96))


def cat_world_agent_level_label(value: int, low: str, middle: str, high: str) -> str:
    if value >= 72:
        return high
    if value <= 38:
        return low
    return middle


def cat_world_cleanliness_profile(
    phone: str,
    cat_id: str,
    traits: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_phone = normalize_login_phone(phone)
    owner_key = hashlib.sha256(normalized_phone.encode("utf-8")).hexdigest()[:12] if normalized_phone else "global"
    seed = f"{owner_key}:{cat_id}:cleanliness"
    cleanliness = int(24 + cat_world_stable_ratio(seed) * 68)
    temperament = str((traits or {}).get("temperament") or "balanced")
    cleanliness += {
        "calm": 10,
        "gentle": 8,
        "chatty": -6,
        "guardian": 3,
        "clingy": 5,
    }.get(temperament, 0)
    cleanliness = cat_world_agent_score(cleanliness)
    if cleanliness >= 80:
        interval_days = 2
        label = "洁癖小猫"
    elif cleanliness >= 60:
        interval_days = 3
        label = "很爱干净"
    elif cleanliness >= 40:
        interval_days = 4
        label = "普通讲究"
    else:
        interval_days = 5
        label = "不太在意"
    return {
        "cleanliness": cleanliness,
        "cleanlinessLabel": label,
        "bathIntervalDays": interval_days,
    }


def cat_world_pick_stable_text(seed: str, options: list[str]) -> str:
    clean_options = [str(option).strip() for option in options if str(option or "").strip()]
    if not clean_options:
        return ""
    option_index = min(int(cat_world_stable_ratio(seed) * len(clean_options)), len(clean_options) - 1)
    return clean_options[option_index]


def cat_world_daily_persona_profile(
    cat: dict[str, Any],
    traits: dict[str, Any],
    daily_mood: dict[str, Any],
    attention: int,
    curiosity: int,
    mischief: int,
    stamina: int,
    activity_bias: int,
    social_need: int,
    seed: str,
) -> dict[str, Any]:
    temperament = str(traits.get("temperament") or "balanced")
    persona_labels = {
        "calm": "冷静观察型",
        "gentle": "温柔陪读型",
        "chatty": "话多探索型",
        "guardian": "巡逻守护型",
        "clingy": "黏人陪伴型",
    }
    care_labels = {
        "calm": "喜欢安静角落和整齐书架",
        "gentle": "喜欢柔软家具和慢节奏陪读",
        "chatty": "喜欢被回应，玩具越多越开心",
        "guardian": "喜欢巡视房间，坏掉的道具会让它在意",
        "clingy": "喜欢摸摸和靠近主人的布置",
    }
    mood_key = str(daily_mood.get("key") or "stable")
    wish_pool = {
        "bright": ["想把今天的单词都变成亮晶晶能量", "想多跑几圈，再等你摸摸头"],
        "curious": ["想探索房间里没有去过的角落", "想试试今天哪个玩具最好玩"],
        "clingy": ["想靠近你听英文朗读", "想成为今天的主陪读猫"],
        "lazy": ["想找一个舒服地方慢慢趴着", "想少跑一点，但陪你学久一点"],
        "quiet": ["想独处一会儿，再安静陪读", "想待在喜欢的家具旁边观察你"],
        "grumpy": ["想被食物和玩具哄一哄", "今天有点烦，需要你温柔一点"],
    }
    voice_pool = list(cat.get("thoughts") or []) + [
        f"我的今日模式是{persona_labels.get(temperament, '均衡陪伴型')}。",
        f"我会按{traits.get('routine') or '自己的节奏'}行动。",
        f"如果能量低了，我会先找地方休息。",
    ]
    play_style = cat_world_agent_level_label(
        max(curiosity, activity_bias),
        "今天更适合短互动",
        "今天玩耍节奏稳定",
        "今天会主动找玩具",
    )
    social_style = cat_world_agent_level_label(
        social_need,
        "今天需要一点独处",
        "今天陪伴需求稳定",
        "今天很想被关注",
    )
    stamina_style = cat_world_agent_level_label(
        stamina,
        "体力容易掉",
        "耐力稳定",
        "体力储备很好",
    )
    mischief_style = cat_world_agent_level_label(
        mischief,
        "捣蛋心很低",
        "偶尔会调皮",
        "今天要多留意道具",
    )
    return {
        "personaLabel": persona_labels.get(temperament, "均衡陪伴型"),
        "carePreferenceLabel": care_labels.get(temperament, "喜欢稳定、干净和能陪读的房间"),
        "dailyWish": cat_world_pick_stable_text(f"{seed}:wish", wish_pool.get(mood_key, ["想安静陪你学习"])),
        "voiceLine": cat_world_pick_stable_text(f"{seed}:voice", voice_pool),
        "playStyleLabel": play_style,
        "socialStyleLabel": social_style,
        "profileTags": [
            persona_labels.get(temperament, "均衡陪伴型"),
            stamina_style,
            social_style,
            mischief_style,
        ],
    }


def cat_world_apply_temperament_daily_bias(
    temperament: str,
    attention: int,
    curiosity: int,
    mischief: int,
    stamina: int,
    activity_bias: int,
    social_need: int,
) -> tuple[int, int, int, int, int, int]:
    if temperament == "calm":
        attention += 8
        curiosity -= 4
        mischief -= 18
        stamina += 10
        activity_bias -= 12
        social_need -= 10
    elif temperament == "gentle":
        attention += 4
        curiosity -= 2
        mischief -= 18
        stamina += 6
        activity_bias -= 16
        social_need += 8
    elif temperament == "chatty":
        attention -= 3
        curiosity += 10
        mischief += 12
        stamina -= 7
        activity_bias += 16
        social_need += 16
    elif temperament == "guardian":
        attention += 6
        curiosity += 4
        mischief += 12
        stamina += 4
        activity_bias += 10
        social_need -= 4
    elif temperament == "clingy":
        attention += 2
        mischief -= 8
        stamina += 2
        activity_bias -= 4
        social_need += 14
    return (
        cat_world_agent_score(attention),
        cat_world_agent_score(curiosity),
        cat_world_agent_score(mischief),
        cat_world_agent_score(stamina),
        cat_world_agent_score(activity_bias),
        cat_world_agent_score(social_need),
    )


def cat_world_default_agent_state(
    log_date: date,
    cat: dict[str, Any],
    traits: dict[str, Any],
    phone: str | None = "",
) -> dict[str, Any]:
    seed = cat_world_daily_agent_seed(log_date, cat["id"], phone)
    mood_index = min(int(cat_world_stable_ratio(f"{seed}:mood") * len(CAT_WORLD_DAILY_MOODS)), len(CAT_WORLD_DAILY_MOODS) - 1)
    daily_mood = CAT_WORLD_DAILY_MOODS[mood_index]
    attention = int(35 + cat_world_stable_ratio(f"{seed}:attention") * 55)
    curiosity = int(35 + cat_world_stable_ratio(f"{seed}:curiosity") * 55)
    mischief = int(18 + cat_world_stable_ratio(f"{seed}:mischief") * 64)
    stamina = int(32 + cat_world_stable_ratio(f"{seed}:stamina") * 58)
    activity_bias = int(32 + cat_world_stable_ratio(f"{seed}:activity") * 58)
    social_need = int(30 + cat_world_stable_ratio(f"{seed}:social") * 60)
    temperament = str(traits.get("temperament") or "balanced")
    attention, curiosity, mischief, stamina, activity_bias, social_need = cat_world_apply_temperament_daily_bias(
        temperament,
        attention,
        curiosity,
        mischief,
        stamina,
        activity_bias,
        social_need,
    )
    persona_profile = cat_world_daily_persona_profile(
        cat,
        traits,
        daily_mood,
        attention,
        curiosity,
        mischief,
        stamina,
        activity_bias,
        social_need,
        seed,
    )
    cleanliness_profile = cat_world_cleanliness_profile(phone or "", cat["id"], traits)
    profile_tags = list(persona_profile.get("profileTags") or [])
    persona_profile["profileTags"] = profile_tags[:3] + [cleanliness_profile["cleanlinessLabel"]]
    return {
        "date": log_date.isoformat(),
        "seedKey": cat_world_daily_agent_seed_key(log_date, cat["id"], phone),
        "dailyMoodKey": daily_mood["key"],
        "dailyMoodLabel": daily_mood["label"],
        "moodOffset": daily_mood["moodOffset"],
        "energyOffset": daily_mood["energyOffset"],
        "attention": attention,
        "curiosity": curiosity,
        "mischief": mischief,
        "stamina": stamina,
        "activityBias": activity_bias,
        "socialNeed": social_need,
        **cleanliness_profile,
        "staminaLabel": cat_world_agent_level_label(stamina, "今天容易累", "耐力稳定", "今天耐力很好"),
        "activityLabel": cat_world_agent_level_label(activity_bias, "今天慢悠悠", "活动量稳定", "今天很爱动"),
        "socialNeedLabel": cat_world_agent_level_label(social_need, "今天想独处", "陪伴需求稳定", "今天想黏人"),
        **persona_profile,
        "routine": traits.get("routine") or "观察房间里的学习节奏",
        "temperament": temperament,
        "mischiefChecked": False,
        "hourlyHistory": [],
        "events": [
            {
                "kind": "daily-mood",
                "time": "今日",
                "label": daily_mood["label"],
                "message": f"{cat['label']} {daily_mood['label']}，{traits.get('routine') or '正在观察房间里的学习节奏'}。",
            }
        ],
    }


CAT_WORLD_AGENT_STATE_CARRY_KEYS = {
    "activeFoodConsumedEnergy",
    "activeFoodConsumedMood",
    "activeFoodLabel",
    "activeFoodRemainingEnergy",
    "activeFoodRemainingMood",
    "activeFoodRemainingSeconds",
    "activeFoodStartedAt",
    "activeFoodToken",
    "activeFoodManualBites",
    "activeFoodNibbleAt",
    "ambientEffectCount",
    "ambientEventAt",
    "favoriteDecorRewarded",
    "hourlyHistory",
    "lastPetAt",
    "mischiefAttemptedAt",
    "mischiefAttemptMood",
    "mischiefAttemptReason",
    "mischiefChecked",
    "mischiefItemId",
    "mischiefLabel",
    "mischiefRepairedAt",
    "mischiefRepairedItemId",
    "mischiefRepairedLabel",
    "mischiefRepairCost",
    "petCount",
    "routinePeriodEvents",
}


def merge_cat_world_agent_state(new_state: dict[str, Any], previous_state: dict[str, Any]) -> dict[str, Any]:
    for key in CAT_WORLD_AGENT_STATE_CARRY_KEYS:
        if key in previous_state:
            new_state[key] = previous_state[key]
    previous_events = [
        event
        for event in cat_world_trim_agent_events(previous_state.get("events"))
        if event.get("kind") != "daily-mood"
    ]
    new_state["events"] = cat_world_trim_agent_events(cat_world_trim_agent_events(new_state.get("events")) + previous_events)
    return new_state


def ensure_cat_world_agent_state(log: CatWorldDailyLog, cat: dict[str, Any], traits: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    state = parse_cat_world_agent_state(log.agent_state)
    expected_seed_key = cat_world_daily_agent_seed_key(log.log_date, cat["id"], log.phone)
    if state.get("date") == log.log_date.isoformat() and state.get("dailyMoodKey") and state.get("seedKey") == expected_seed_key:
        state["events"] = cat_world_trim_agent_events(state.get("events"))
        changed = False
        default_state = cat_world_default_agent_state(log.log_date, cat, traits, log.phone)
        for key in (
            "stamina",
            "activityBias",
            "socialNeed",
            "staminaLabel",
            "activityLabel",
            "socialNeedLabel",
            "cleanliness",
            "cleanlinessLabel",
            "bathIntervalDays",
            "personaLabel",
            "carePreferenceLabel",
            "dailyWish",
            "voiceLine",
            "playStyleLabel",
            "socialStyleLabel",
            "profileTags",
        ):
            if key not in state:
                state[key] = default_state.get(key)
                changed = True
        if changed:
            log.agent_state = encode_cat_world_agent_state(state)
        return state, changed
    previous_state = state if state.get("date") == log.log_date.isoformat() else {}
    state = cat_world_default_agent_state(log.log_date, cat, traits, log.phone)
    if previous_state:
        state = merge_cat_world_agent_state(state, previous_state)
    log.agent_state = encode_cat_world_agent_state(state)
    return state, True


def append_cat_world_agent_event(
    log: CatWorldDailyLog,
    cat: dict[str, Any],
    traits: dict[str, Any],
    kind: str,
    label: str,
    message: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    agent_state, _ = ensure_cat_world_agent_state(log, cat, traits)
    events = cat_world_trim_agent_events(agent_state.get("events"))
    next_event = cat_world_agent_event(kind, label, message, now)
    if not events or events[-1] != next_event:
        events.append(next_event)
    agent_state["events"] = cat_world_trim_agent_events(events)
    log.agent_state = encode_cat_world_agent_state(agent_state)
    return agent_state


def cat_world_current_behavior(
    agent_state: dict[str, Any],
    traits: dict[str, Any],
    mood_score: int,
    energy_score: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    local_now = cat_world_local_now(now)
    hour = local_now.hour
    activity_bias = min(max(int(agent_state.get("activityBias") or 50), 0), 100)
    social_need = min(max(int(agent_state.get("socialNeed") or 50), 0), 100)
    sleeping = (
        cat_world_is_sleep_hour(hour, int(traits.get("sleepStart") or 23), int(traits.get("sleepEnd") or 7))
        and not bool(traits.get("nightOwl"))
    )
    if sleeping:
        key = "sleeping"
        label = "晚上睡觉中"
    elif energy_score < int(traits.get("restThreshold") or 34):
        key = "resting"
        label = "体力低，原地休息"
    elif mood_score < 38:
        key = "sulking"
        label = "心情差，可能会捣蛋"
    elif social_need >= 76 and mood_score < 68:
        key = "seeking-touch"
        label = "想要陪玩"
    elif bool(traits.get("nightOwl")) and (hour >= 22 or hour < 5):
        key = "night-watch"
        label = "夜间巡逻"
    elif agent_state.get("dailyMoodKey") == "curious" or activity_bias >= 78:
        key = "exploring"
        label = "到处探索"
    elif agent_state.get("dailyMoodKey") == "lazy" or activity_bias <= 34:
        key = "slow"
        label = "慢慢散步"
    else:
        key = "active"
        label = "自由活动"
    return {
        "key": key,
        "label": label,
        "hour": hour,
        "sleeping": sleeping,
        "nightOwl": bool(traits.get("nightOwl")),
    }


def cat_world_signed_change(value: int | float) -> str:
    numeric = int(round(float(value or 0)))
    if numeric > 0:
        return f"+{numeric}"
    return str(numeric)


def cat_world_litter_mood_penalty(litter_count: int | float) -> int:
    try:
        count = max(int(litter_count or 0), 0)
    except (TypeError, ValueError):
        count = 0
    return min(count * CAT_WORLD_LITTER_MOOD_PENALTY_PER_PILE, CAT_WORLD_LITTER_MOOD_PENALTY_MAX)


def cat_world_behavior_hourly_change(
    log: CatWorldDailyLog,
    traits: dict[str, Any],
    inventory: dict[str, int],
    favorite_count: int,
    now: datetime,
    litter_count: int = 0,
    bath_mood_penalty: int = 0,
    cat: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mood_decay, energy_decay, relief = cat_world_decay_rates(traits, inventory, favorite_count)
    cat = cat or CAT_WORLD_CAT_BY_ID.get(log.cat_id, CAT_WORLD_CAT_BY_ID[CAT_WORLD_DEFAULT_CAT_ID])
    agent_state, _ = ensure_cat_world_agent_state(log, cat, traits)
    mood_score = clamp_cat_world_score(int(log.mood_score or 0) + int(agent_state.get("moodOffset") or 0))
    energy_score = clamp_cat_world_score(int(log.energy_score or 0) + int(agent_state.get("energyOffset") or 0))
    attention = min(max(int(agent_state.get("attention") or 50), 0), 100)
    stamina = min(max(int(agent_state.get("stamina") or 50), 0), 100)
    activity_bias = min(max(int(agent_state.get("activityBias") or 50), 0), 100)
    social_need = min(max(int(agent_state.get("socialNeed") or 50), 0), 100)
    daily_energy_bias = int(min(max(round((activity_bias - stamina) / 28), -3), 3))
    daily_mood_bias = int(min(max(round((social_need - attention) / 34), -2), 2))
    mood_decay = max(1, mood_decay + daily_mood_bias)
    energy_decay = max(1, energy_decay + daily_energy_bias)
    behavior = cat_world_current_behavior(agent_state, traits, mood_score, energy_score, now)
    mood_key = str(agent_state.get("dailyMoodKey") or "")
    sleeping = behavior["key"] == "sleeping"
    waking = cat_world_is_wake_transition(now, traits)
    recovering = sleeping or waking

    mood_delta = -mood_decay
    energy_delta = -energy_decay
    label = "自然消耗"
    reason = "自由活动"
    daily_notes = []
    if daily_energy_bias > 0:
        daily_notes.append("今天更爱动")
    elif daily_energy_bias < 0:
        daily_notes.append("今天耐力更稳")
    if daily_mood_bias > 0:
        daily_notes.append("今天更需要陪伴")
    elif daily_mood_bias < 0:
        daily_notes.append("今天比较专注")

    if sleeping:
        energy_delta = max(1, round(3 / max(float(traits["energyDrain"]), 0.5)))
        mood_delta = 3
        label = "睡觉恢复"
        reason = "按自己的作息睡觉"
    elif waking:
        energy_delta = max(1, round(2 / max(float(traits["energyDrain"]), 0.5)))
        mood_delta = 6
        label = "睡醒舒展"
        reason = "睡足后醒来，坏情绪得到缓解"
    elif behavior["key"] == "resting":
        energy_delta = -max(1, round(energy_decay * 0.35))
        mood_delta = -max(1, round(mood_decay * 0.45))
        label = "原地休息"
        reason = "体力低，减少走动"
    elif behavior["key"] == "night-watch":
        energy_delta -= max(1, round(float(traits["movement"])))
        mood_delta = min(mood_delta + 1, 0)
        label = "夜间巡逻"
        reason = "夜猫按性格巡房间"
    elif behavior["key"] == "exploring":
        energy_delta -= 1
        label = "探索消耗"
        reason = "今天想探索"
    elif behavior["key"] == "slow":
        energy_delta = -max(1, round(energy_decay * 0.65))
        mood_delta = -max(1, round(mood_decay * 0.7))
        label = "慢慢散步"
        reason = "今天想慢慢来"
    elif behavior["key"] == "sulking":
        mood_delta -= 2
        label = "心情低落"
        reason = "心情差，消耗更明显"
    elif behavior["key"] == "seeking-touch":
        mood_delta -= 1
        energy_delta = min(energy_delta + 1, -1)
        label = "想要陪玩"
        reason = "陪伴需求高，想等你摸摸或玩玩具"

    if mood_key == "bright" and mood_delta < 2:
        mood_delta += 1
    elif mood_key == "grumpy" and not recovering:
        mood_delta -= 1

    if favorite_count > 0 and mood_delta < 0:
        mood_delta = min(0, mood_delta + min(favorite_count, 2))

    litter_penalty = cat_world_litter_mood_penalty(litter_count)
    if recovering:
        litter_penalty = min(litter_penalty, 1)
    if litter_penalty:
        mood_delta -= litter_penalty
        reason = f"{reason}，房间有 {max(int(litter_count or 0), 0)} 堆猫屎"

    bath_penalty = max(int(bath_mood_penalty or 0), 0)
    if recovering:
        bath_penalty = min(bath_penalty, 1)
    if bath_penalty:
        mood_delta -= bath_penalty
        reason = f"{reason}，太久没洗澡正在炸毛"

    if sleeping:
        mood_delta = max(mood_delta, 2)
    elif waking:
        mood_delta = max(mood_delta, 4)

    if daily_notes:
        reason = f"{reason}，{'、'.join(daily_notes)}"

    return {
        "moodDelta": int(mood_delta),
        "energyDelta": int(energy_delta),
        "hourlyMood": int(mood_delta),
        "hourlyEnergy": int(energy_delta),
        "baseMoodDecay": int(mood_decay),
        "baseEnergyDecay": int(energy_decay),
        "relief": int(relief),
        "dailyEnergyBias": int(daily_energy_bias),
        "dailyMoodBias": int(daily_mood_bias),
        "litterPenalty": int(litter_penalty),
        "bathPenalty": int(bath_penalty),
        "label": label,
        "reason": reason,
        "behavior": behavior,
    }


def cat_world_pick_stable_item(seed: str, item_ids: list[str]) -> str:
    if not item_ids:
        return ""
    item_index = min(int(cat_world_stable_ratio(seed) * len(item_ids)), len(item_ids) - 1)
    return item_ids[item_index]


def cat_world_damage_risk_label(probability: float) -> str:
    if probability >= 0.24:
        return "偏高"
    if probability >= 0.12:
        return "中等"
    if probability >= 0.055:
        return "偏低"
    return "很低"


def cat_world_damage_risk_reason(agent_state: dict[str, Any], traits: dict[str, Any], mood_score: int) -> str:
    ready, reason = cat_world_damage_attempt_ready(agent_state, traits, mood_score)
    if not ready:
        return reason
    mood_key = str(agent_state.get("dailyMoodKey") or "")
    if mood_key == "grumpy" or mood_score < 38:
        return "心情差时更容易捣蛋"
    if mood_score < 50:
        return "心情有点低，偶尔会碰倒道具"
    if mood_key == "curious":
        return "今天想探索，会轻微增加碰坏概率"
    return "心情稳定时破坏概率很低"


def cat_world_damage_event_motive(agent_state: dict[str, Any], mood_score: int) -> str:
    mood_key = str(agent_state.get("dailyMoodKey") or "")
    if mood_key == "grumpy" or mood_score < 38:
        return "心情差"
    if mood_score < 50:
        return "有点烦躁"
    if mood_key == "curious":
        return "探索时太兴奋"
    return "偶尔调皮"


def cat_world_damage_attempt_ready(agent_state: dict[str, Any], traits: dict[str, Any], mood_score: int) -> tuple[bool, str]:
    mood_key = str(agent_state.get("dailyMoodKey") or "")
    temperament = str(traits.get("temperament") or "balanced")
    mischief = min(max(int(agent_state.get("mischief") or 35), 0), 100)
    if mood_key == "grumpy":
        return True, "今天不太高兴，进入捣蛋观察"
    if mood_score < 44:
        return True, "心情已经偏低，可能会弄坏道具"
    if mood_score < 54 and mischief >= 62:
        return True, "心情偏低且捣蛋值高"
    if mood_score < 60 and mischief >= 78 and temperament in {"chatty", "guardian"}:
        return True, "活跃猫咪心情不稳时更容易闯祸"
    return False, "心情稳定，今天先不破坏道具"


def cat_world_agent_daily_goal(
    log: CatWorldDailyLog,
    cat: dict[str, Any],
    traits: dict[str, Any],
    agent_state: dict[str, Any],
    behavior: dict[str, Any],
    mood_score: int,
    energy_score: int,
    inventory: dict[str, int],
    room_layout: dict[str, dict[str, float]],
    favorite_active_ids: list[str],
) -> dict[str, Any]:
    seed = f"{cat_world_daily_agent_seed(log.log_date, cat['id'], log.phone)}:goal"
    mood_key = str(agent_state.get("dailyMoodKey") or "")
    temperament = str(traits.get("temperament") or "balanced")
    social_need = min(max(int(agent_state.get("socialNeed") or 50), 0), 100)
    owned_toys = sorted(
        item_id
        for item_id, count in inventory.items()
        if count > 0 and CAT_WORLD_SHOP_BY_ID.get(item_id, {}).get("category") == "toy"
    )
    owned_decor = sorted(
        item_id
        for item_id, count in inventory.items()
        if count > 0 and item_id in room_layout and CAT_WORLD_SHOP_BY_ID.get(item_id, {}).get("category") == "decor"
    )
    active_favorites = [item_id for item_id in favorite_active_ids if item_id in owned_decor]
    breed_id = str(cat.get("breedId") or cat.get("id") or CAT_WORLD_DEFAULT_CAT_ID)
    favorite_owned_toys = [item_id for item_id in owned_toys if cat_world_item_favorite_cat_id(item_id) == breed_id]
    damage_candidates = sorted(set(owned_toys + owned_decor))
    damage_ready, damage_ready_reason = cat_world_damage_attempt_ready(agent_state, traits, mood_score)
    damage_probability = cat_world_damage_probability(agent_state, traits, mood_score)
    risk_label = cat_world_damage_risk_label(damage_probability)
    risk_reason = cat_world_damage_risk_reason(agent_state, traits, mood_score)

    def goal(
        key: str,
        label: str,
        message: str,
        target_type: str = "walk",
        target_item_id: str = "",
        priority: int = 62,
    ) -> dict[str, Any]:
        item = CAT_WORLD_SHOP_BY_ID.get(target_item_id, {})
        return {
            "key": key,
            "label": label,
            "message": message,
            "targetType": target_type,
            "targetItemId": target_item_id,
            "targetLabel": item.get("label") or "",
            "priority": int(min(max(priority, 0), 100)),
            "damageRisk": round(damage_probability, 3),
            "damageRiskLabel": risk_label,
            "damageRiskReason": risk_reason,
        }

    if behavior.get("key") == "sleeping":
        return goal(
            "sleep",
            "睡觉补能",
            f"{cat['label']}现在按自己的作息睡觉，醒来后会继续巡房间。",
            "rest",
            "",
            8,
        )
    if energy_score < int(traits.get("restThreshold") or 34):
        return goal(
            "rest",
            "原地休息",
            f"{cat['label']}体力偏低，今天会少走动，优先等食物补能。",
            "rest",
            "",
            12,
        )

    if damage_ready and damage_candidates:
        target_item_id = cat_world_pick_stable_item(f"{seed}:mischief", damage_candidates)
        return goal(
            "mischief-watch",
            "盯着道具",
            f"{cat['label']}{damage_ready_reason}，正在盯着{CAT_WORLD_SHOP_BY_ID[target_item_id]['label']}，最好陪玩或喂食安抚一下。",
            CAT_WORLD_SHOP_BY_ID[target_item_id].get("category") or "decor",
            target_item_id,
            86,
        )

    if social_need >= 76 and mood_score < 68:
        return goal(
            "seek-attention",
            "想要陪伴",
            f"{cat['label']}今天特别想被关注，摸摸或喜欢的玩具会让它更安心。",
            "walk",
            "",
            72,
        )

    wants_toy = (
        mood_key in {"bright", "curious"}
        or temperament in {"chatty", "guardian"}
        or behavior.get("key") in {"exploring", "night-watch"}
    )
    if wants_toy and (favorite_owned_toys or owned_toys):
        target_item_id = cat_world_pick_stable_item(f"{seed}:toy", favorite_owned_toys or owned_toys)
        favorite_text = "最喜欢的" if target_item_id in favorite_owned_toys else ""
        return goal(
            "toy-play",
            "想玩玩具",
            f"{cat['label']}今天想玩{favorite_text}{CAT_WORLD_SHOP_BY_ID[target_item_id]['label']}，靠近后会在旁边转一会儿。",
            "toy",
            target_item_id,
            88 if favorite_owned_toys else 82,
        )

    if active_favorites:
        target_item_id = cat_world_pick_stable_item(f"{seed}:favorite", active_favorites)
        return goal(
            "favorite-decor",
            "去喜欢的家具",
            f"{cat['label']}今天会优先跑到喜欢的{CAT_WORLD_SHOP_BY_ID[target_item_id]['label']}附近待着。",
            "decor",
            target_item_id,
            78,
        )

    if owned_decor:
        target_item_id = cat_world_pick_stable_item(f"{seed}:decor", owned_decor)
        return goal(
            "room-patrol",
            "巡逻房间",
            f"{cat['label']}今天会在{CAT_WORLD_SHOP_BY_ID[target_item_id]['label']}附近巡逻。",
            "decor",
            target_item_id,
            66,
        )

    return goal(
        "free-walk",
        "自由散步",
        f"{cat['label']}今天没有特别目标，会在活动室里慢慢走动。",
        "walk",
        "",
        48,
    )


def cat_world_agent_care_tip(
    cat: dict[str, Any],
    traits: dict[str, Any],
    agent_state: dict[str, Any],
    behavior: dict[str, Any],
    daily_goal: dict[str, Any],
    mood_score: int,
    energy_score: int,
    favorite_active_ids: list[str],
) -> str:
    cat_label = cat.get("label") or "猫咪"
    temperament = str(traits.get("temperament") or agent_state.get("temperament") or "balanced")
    rest_threshold = int(traits.get("restThreshold") or 34)
    social_need = min(max(int(agent_state.get("socialNeed") or 50), 0), 100)
    active_favorite_labels = [
        CAT_WORLD_SHOP_BY_ID.get(item_id, {}).get("label") or item_id
        for item_id in favorite_active_ids[:2]
    ]
    if behavior.get("sleeping"):
        return f"{cat_label}现在按作息睡觉，醒来后再喂食或陪玩更有效。"
    if energy_score < rest_threshold:
        return f"{cat_label}体力不足，优先摆放食物；吃完前会尽量原地休息。"
    if daily_goal.get("key") == "mischief-watch":
        return f"{cat_label}有捣蛋风险，先用食物、摸摸或喜欢的玩具安抚，能降低破坏概率。"
    if mood_score < 42:
        return f"{cat_label}心情偏低，优先安排喜欢的玩具或家具，不要让它独处太久。"
    if social_need >= 78:
        return f"{cat_label}今天很想被关注，多点几次摸摸或切换成主猫会更安心。"
    if active_favorite_labels:
        return f"{cat_label}喜欢的{active_favorite_labels[0]}已经摆出，今天会更愿意靠过去休息。"
    if temperament == "calm":
        return f"{cat_label}偏安静，适合书架、窗台这类稳定布局。"
    if temperament == "gentle":
        return f"{cat_label}偏温柔，喜欢陪读角落和柔软家具。"
    if temperament == "chatty":
        return f"{cat_label}爱热闹，玩具越丰富越容易保持好心情。"
    if temperament == "guardian":
        return f"{cat_label}爱巡逻，家具和玩具坏了会特别在意。"
    if temperament == "clingy":
        return f"{cat_label}比较黏人，摸摸和喜欢的食物会更快安抚它。"
    return f"{cat_label}状态稳定，可以按今天目标布置活动室。"


def cat_world_agent_care_need(
    cat: dict[str, Any],
    traits: dict[str, Any],
    agent_state: dict[str, Any],
    behavior: dict[str, Any],
    daily_goal: dict[str, Any],
    mood_score: int,
    energy_score: int,
    favorite_active_ids: list[str],
    inventory: dict[str, int],
    room_layout: dict[str, dict[str, float]],
    damaged_item_id: str = "",
) -> dict[str, Any]:
    cat_id = str(cat.get("id") or CAT_WORLD_DEFAULT_CAT_ID)
    breed_id = str(cat.get("breedId") or cat_id)
    cat_label = str(cat.get("label") or "猫咪")
    rest_threshold = int(traits.get("restThreshold") or 34)
    social_need = min(max(int(agent_state.get("socialNeed") or 50), 0), 100)

    def status_for(priority: int) -> str:
        if priority >= 86:
            return "urgent"
        if priority >= 70:
            return "high"
        if priority >= 48:
            return "normal"
        return "calm"

    def need(
        key: str,
        label: str,
        action_label: str,
        message: str,
        priority: int,
        target_type: str = "",
        target_item_id: str = "",
    ) -> dict[str, Any]:
        item = CAT_WORLD_SHOP_BY_ID.get(str(target_item_id or ""), {})
        return {
            "key": key,
            "label": label,
            "actionLabel": action_label,
            "message": message,
            "priority": int(min(max(priority, 0), 100)),
            "status": status_for(priority),
            "targetType": target_type or str(item.get("category") or ""),
            "targetItemId": str(target_item_id or ""),
            "targetLabel": str(item.get("label") or ""),
        }

    if behavior.get("sleeping"):
        return need(
            "sleep",
            "睡觉中",
            "醒后照顾",
            f"{cat_label}现在按自己的作息睡觉，先让它休息。",
            18,
            "rest",
        )

    if damaged_item_id:
        damaged_label = CAT_WORLD_SHOP_BY_ID.get(damaged_item_id, {}).get("label") or damaged_item_id
        return need(
            "repair",
            "需要维修",
            "维修道具",
            f"{cat_label}在意坏掉的{damaged_label}，修好后会更安心。",
            92,
            CAT_WORLD_SHOP_BY_ID.get(damaged_item_id, {}).get("category") or "decor",
            damaged_item_id,
        )

    owned_food_ids = [
        item_id
        for item_id, count in inventory.items()
        if count > 0 and CAT_WORLD_SHOP_BY_ID.get(item_id, {}).get("category") == "food"
    ]
    favorite_food_ids = [item_id for item_id in owned_food_ids if cat_world_item_favorite_cat_id(item_id) == breed_id]
    if energy_score < rest_threshold:
        target_item_id = favorite_food_ids[0] if favorite_food_ids else (owned_food_ids[0] if owned_food_ids else "")
        action_label = "摆放食物" if target_item_id else "购买猫粮"
        return need(
            "food",
            "体力不足",
            action_label,
            f"{cat_label}体力低，优先给它食物；吃完前会少走动。",
            90,
            "food",
            target_item_id,
        )

    if daily_goal.get("key") == "mischief-watch":
        return need(
            "comfort",
            "需要安抚",
            "摸摸或喂食",
            f"{cat_label}有一点捣蛋冲动，先安抚会更稳。",
            88,
            daily_goal.get("targetType") or "",
            daily_goal.get("targetItemId") or "",
        )

    owned_toys = [
        item_id
        for item_id, count in inventory.items()
        if count > 0 and CAT_WORLD_SHOP_BY_ID.get(item_id, {}).get("category") == "toy"
    ]
    favorite_toy_ids = [item_id for item_id in owned_toys if cat_world_item_favorite_cat_id(item_id) == breed_id]
    if mood_score < 42:
        target_item_id = favorite_toy_ids[0] if favorite_toy_ids else (owned_toys[0] if owned_toys else "")
        action_label = "玩喜欢的玩具" if target_item_id else "摸摸安抚"
        return need(
            "mood",
            "心情偏低",
            action_label,
            f"{cat_label}心情不太好，喜欢的玩具或摸摸会更有效。",
            82,
            "toy" if target_item_id else "touch",
            target_item_id,
        )

    if social_need >= 78:
        return need(
            "attention",
            "想要陪伴",
            "摸摸",
            f"{cat_label}今天更黏人，点它几次会更安心。",
            76,
            "touch",
        )

    favorite_decor_ids = cat_world_cat_favorite_decor_ids(breed_id)
    owned_favorite_decor = [
        decor_id
        for decor_id in favorite_decor_ids
        if inventory.get(decor_id, 0) > 0 and decor_id not in favorite_active_ids
    ]
    if owned_favorite_decor:
        target_item_id = owned_favorite_decor[0]
        return need(
            "place-favorite",
            "想要布置",
            "摆出喜欢家具",
            f"{cat_label}喜欢{CAT_WORLD_SHOP_BY_ID[target_item_id]['label']}，摆出来会更开心。",
            66,
            "decor",
            target_item_id,
        )

    if favorite_active_ids:
        target_item_id = favorite_active_ids[0]
        return need(
            "settled",
            "状态满足",
            "保持布局",
            f"{cat_label}喜欢的{CAT_WORLD_SHOP_BY_ID.get(target_item_id, {}).get('label') or '家具'}已经在房间里。",
            42,
            "decor",
            target_item_id,
        )

    if daily_goal.get("targetItemId"):
        return need(
            "daily-goal",
            "有今日目标",
            daily_goal.get("label") or "陪它过去",
            daily_goal.get("message") or f"{cat_label}有自己的今日目标。",
            int(daily_goal.get("priority") or 56),
            daily_goal.get("targetType") or "",
            daily_goal.get("targetItemId") or "",
        )

    return need(
        "stable",
        "状态稳定",
        "自由活动",
        f"{cat_label}现在状态稳定，可以让它自由活动。",
        34,
        "walk",
    )


def cat_world_agent_payload(
    log: CatWorldDailyLog,
    cat: dict[str, Any],
    traits: dict[str, Any],
    inventory: dict[str, int] | None = None,
    room_layout: dict[str, dict[str, float]] | None = None,
    favorite_active_ids: list[str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    agent_state, changed = ensure_cat_world_agent_state(log, cat, traits)
    if changed:
        log.agent_state = encode_cat_world_agent_state(agent_state)
    inventory = inventory or {}
    room_layout = room_layout or {}
    favorite_active_ids = favorite_active_ids or []
    mood_score = clamp_cat_world_score(int(log.mood_score or 0) + int(agent_state.get("moodOffset") or 0))
    energy_score = clamp_cat_world_score(int(log.energy_score or 0) + int(agent_state.get("energyOffset") or 0))
    behavior = cat_world_current_behavior(agent_state, traits, mood_score, energy_score, now)
    hourly_change = cat_world_behavior_hourly_change(
        log,
        traits,
        inventory,
        len(favorite_active_ids),
        now or datetime.utcnow(),
        cat=cat,
    )
    comfort_relief = int(hourly_change.get("relief") or 0)
    comfort_parts = []
    if comfort_relief > 0:
        comfort_parts.append(f"道具减耗 {comfort_relief}/h")
    if favorite_active_ids:
        comfort_parts.append(f"喜欢家具 {len(favorite_active_ids)} 件")
    daily_goal = cat_world_agent_daily_goal(
        log,
        cat,
        traits,
        agent_state,
        behavior,
        mood_score,
        energy_score,
        inventory,
        room_layout,
        favorite_active_ids,
    )
    care_tip = cat_world_agent_care_tip(
        cat,
        traits,
        agent_state,
        behavior,
        daily_goal,
        mood_score,
        energy_score,
        favorite_active_ids,
    )
    care_need = cat_world_agent_care_need(
        cat,
        traits,
        agent_state,
        behavior,
        daily_goal,
        mood_score,
        energy_score,
        favorite_active_ids,
        inventory,
        room_layout,
        log.damaged_item_id or agent_state.get("mischiefItemId") or "",
    )
    public_agent_state = {key: value for key, value in agent_state.items() if key != "seedKey"}
    return {
        **public_agent_state,
        "currentBehavior": behavior,
        "dailyGoal": daily_goal,
        "careTip": care_tip,
        "careNeed": care_need,
        "adjustedMoodScore": mood_score,
        "adjustedEnergyScore": energy_score,
        "hourlyLabel": hourly_change.get("label") or "",
        "hourlyReason": hourly_change.get("reason") or "",
        "hourlyEnergyBias": int(hourly_change.get("dailyEnergyBias") or 0),
        "hourlyMoodBias": int(hourly_change.get("dailyMoodBias") or 0),
        "comfortRelief": comfort_relief,
        "comfortLabel": " · ".join(comfort_parts) if comfort_parts else "暂无道具减耗",
        "damagedItemId": log.damaged_item_id or agent_state.get("mischiefItemId") or "",
    }


def get_or_create_cat_world_daily_log(
    db: Session,
    phone: str,
    cat_id: str,
    log_date: date,
    now: datetime,
    cat: dict[str, Any] | None = None,
) -> CatWorldDailyLog:
    normalized = normalize_login_phone(phone)
    for pending in db.new:
        if (
            isinstance(pending, CatWorldDailyLog)
            and pending.phone == normalized
            and pending.log_date == log_date
            and pending.cat_id == cat_id
        ):
            return pending
    log = db.scalar(
        select(CatWorldDailyLog).where(
            CatWorldDailyLog.phone == normalized,
            CatWorldDailyLog.log_date == log_date,
            CatWorldDailyLog.cat_id == cat_id,
        )
    )
    if log:
        return log
    cat = cat or CAT_WORLD_CAT_BY_ID.get(cat_id, CAT_WORLD_CAT_BY_ID[CAT_WORLD_DEFAULT_CAT_ID])
    breed_id = str(cat.get("breedId") or cat.get("id") or CAT_WORLD_DEFAULT_CAT_ID)
    traits = cat_world_cat_traits(cat)
    legacy_log = None
    if cat_id != breed_id:
        legacy_log = db.scalar(
            select(CatWorldDailyLog).where(
                CatWorldDailyLog.phone == normalized,
                CatWorldDailyLog.log_date == log_date,
                CatWorldDailyLog.cat_id == breed_id,
            )
        )
    log = CatWorldDailyLog(
        phone=normalized,
        log_date=log_date,
        cat_id=cat_id,
        favorite_decor_ids=",".join(cat_world_cat_favorite_decor_ids(breed_id)),
        mood_score=(
            int(legacy_log.mood_score or 0)
            if legacy_log
            else clamp_cat_world_score(64 - round(4 * float(traits["moodDrain"])))
        ),
        energy_score=(
            int(legacy_log.energy_score or 0)
            if legacy_log
            else clamp_cat_world_score(62 - round(4 * float(traits["energyDrain"])))
        ),
        food_count=int(legacy_log.food_count or 0) if legacy_log else 0,
        toy_count=int(legacy_log.toy_count or 0) if legacy_log else 0,
        last_food_item=legacy_log.last_food_item if legacy_log else None,
        last_play_item=legacy_log.last_play_item if legacy_log else None,
        last_decay_at=now,
    )
    db.add(log)
    return log


def apply_cat_world_hourly_decay(
    log: CatWorldDailyLog,
    traits: dict[str, Any],
    inventory: dict[str, int],
    favorite_count: int,
    now: datetime,
    litter_count: int = 0,
    bath_mood_penalty: int = 0,
    cat: dict[str, Any] | None = None,
) -> bool:
    last_decay_at = log.last_decay_at or datetime.combine(log.log_date, datetime.min.time())
    elapsed_hours = int(max((now - last_decay_at).total_seconds(), 0) // 3600)
    hourly_change = cat_world_behavior_hourly_change(
        log, traits, inventory, favorite_count, now, litter_count, bath_mood_penalty, cat
    )
    cat = cat or CAT_WORLD_CAT_BY_ID.get(log.cat_id, CAT_WORLD_CAT_BY_ID[CAT_WORLD_DEFAULT_CAT_ID])
    breed_id = str(cat.get("breedId") or cat.get("id") or CAT_WORLD_DEFAULT_CAT_ID)
    log.favorite_decor_ids = ",".join(cat_world_cat_favorite_decor_ids(breed_id))
    favorite_bonus = favorite_count * 8
    relief_bonus = int(hourly_change["relief"])
    log.decor_bonus = max(favorite_bonus, relief_bonus)
    if elapsed_hours <= 0:
        log.hourly_mood_decay = int(hourly_change["hourlyMood"])
        log.hourly_energy_decay = int(hourly_change["hourlyEnergy"])
        return False
    agent_state, _ = ensure_cat_world_agent_state(log, cat, traits)
    history = cat_world_trim_hourly_history(agent_state.get("hourlyHistory"))
    total_mood_delta = 0
    total_energy_delta = 0
    applied_hours = 0
    detailed_hours = min(elapsed_hours, 24)
    for index in range(detailed_hours):
        hour_at = last_decay_at + timedelta(hours=index + 1)
        hourly_change = cat_world_behavior_hourly_change(
            log, traits, inventory, favorite_count, hour_at, litter_count, bath_mood_penalty, cat
        )
        mood_delta = int(hourly_change["moodDelta"])
        energy_delta = int(hourly_change["energyDelta"])
        log.mood_score = clamp_cat_world_score(int(log.mood_score or 0) + mood_delta)
        log.energy_score = clamp_cat_world_score(int(log.energy_score or 0) + energy_delta)
        total_mood_delta += mood_delta
        total_energy_delta += energy_delta
        applied_hours += 1
        history.append(
            cat_world_hourly_history_entry(
                hour_at,
                hourly_change,
                energy_delta,
                mood_delta,
                int(log.energy_score or 0),
                int(log.mood_score or 0),
            )
        )
    if applied_hours < elapsed_hours:
        remaining_hours = elapsed_hours - applied_hours
        hour_at = last_decay_at + timedelta(hours=elapsed_hours)
        hourly_change = cat_world_behavior_hourly_change(
            log, traits, inventory, favorite_count, hour_at, litter_count, bath_mood_penalty, cat
        )
        mood_delta = int(hourly_change["moodDelta"]) * remaining_hours
        energy_delta = int(hourly_change["energyDelta"]) * remaining_hours
        log.mood_score = clamp_cat_world_score(int(log.mood_score or 0) + mood_delta)
        log.energy_score = clamp_cat_world_score(int(log.energy_score or 0) + energy_delta)
        total_mood_delta += mood_delta
        total_energy_delta += energy_delta
        history.append(
            cat_world_hourly_history_entry(
                hour_at,
                hourly_change,
                energy_delta,
                mood_delta,
                int(log.energy_score or 0),
                int(log.mood_score or 0),
                remaining_hours,
            )
        )
    hourly_change = cat_world_behavior_hourly_change(
        log, traits, inventory, favorite_count, now, litter_count, bath_mood_penalty, cat
    )
    log.hourly_mood_decay = int(hourly_change["hourlyMood"])
    log.hourly_energy_decay = int(hourly_change["hourlyEnergy"])
    log.last_decay_at = last_decay_at + timedelta(hours=elapsed_hours)
    agent_state["hourlyHistory"] = cat_world_trim_hourly_history(history)
    log.agent_state = encode_cat_world_agent_state(agent_state)
    append_cat_world_agent_event(
        log,
        cat,
        traits,
        "hourly-change",
        str(hourly_change["label"]),
        f"{cat['label']}过了 {elapsed_hours} 小时，{hourly_change['reason']}，体力 {cat_world_signed_change(total_energy_delta)}，心情 {cat_world_signed_change(total_mood_delta)}。",
        now,
    )
    return True


def cat_world_daily_log_payload(
    log: CatWorldDailyLog,
    favorite_active_ids: list[str],
    inventory: dict[str, int] | None = None,
    room_layout: dict[str, dict[str, float]] | None = None,
    cat: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cat = cat or CAT_WORLD_CAT_BY_ID.get(log.cat_id, CAT_WORLD_CAT_BY_ID[CAT_WORLD_DEFAULT_CAT_ID])
    breed_id = str(cat.get("breedId") or cat.get("id") or CAT_WORLD_DEFAULT_CAT_ID)
    traits = cat_world_cat_traits(cat)
    agent_state = cat_world_agent_payload(log, cat, traits, inventory, room_layout, favorite_active_ids)
    return {
        "date": log.log_date.isoformat(),
        "catId": log.cat_id,
        "favoriteDecorIds": cat_world_cat_favorite_decor_ids(breed_id),
        "favoriteActiveDecorIds": favorite_active_ids,
        "moodScore": int(agent_state.get("adjustedMoodScore") or log.mood_score or 0),
        "baseMoodScore": int(log.mood_score or 0),
        "energyScore": int(agent_state.get("adjustedEnergyScore") or log.energy_score or 0),
        "baseEnergyScore": int(log.energy_score or 0),
        "hourlyMoodDecay": int(log.hourly_mood_decay or 0),
        "hourlyEnergyDecay": int(log.hourly_energy_decay or 0),
        "foodCount": int(log.food_count or 0),
        "toyCount": int(log.toy_count or 0),
        "decorBonus": int(log.decor_bonus or 0),
        "agentState": agent_state,
        "damagedItemId": log.damaged_item_id or "",
        "lastFoodItem": log.last_food_item or "",
        "lastPlayItem": log.last_play_item or "",
        "lastDecayAt": log.last_decay_at.isoformat() if log.last_decay_at else "",
    }


def cat_world_cat_payload(cat: dict[str, Any]) -> dict[str, Any]:
    favorite_decor_ids = cat_world_cat_favorite_decor_ids(cat["id"])
    favorite_food_ids = cat_world_cat_favorite_item_ids(cat["id"], {"food"})
    favorite_toy_ids = cat_world_cat_favorite_item_ids(cat["id"], {"toy"})
    favorite_item_ids = cat_world_cat_favorite_item_ids(cat["id"])
    return {
        **cat,
        "favoriteDecorIds": favorite_decor_ids,
        "favoriteDecorLabels": [CAT_WORLD_DECOR_LABELS.get(decor_id, decor_id) for decor_id in favorite_decor_ids],
        "favoriteFoodIds": favorite_food_ids,
        "favoriteToyIds": favorite_toy_ids,
        "favoriteItemIds": favorite_item_ids,
        "favoriteItemLabels": [
            CAT_WORLD_SHOP_BY_ID.get(item_id, {}).get("label", item_id)
            for item_id in favorite_item_ids
        ],
    }


def cat_world_random_gender(db: Session) -> str:
    weights = cat_world_gender_draw_weights(db)
    ticket = secrets.randbelow(int(weights["male"]) + int(weights["female"]))
    return "male" if ticket < int(weights["male"]) else "female"


def cat_world_personality_choice(db: Session, phone: str) -> dict[str, Any]:
    used_keys = {
        str(key)
        for key in db.scalars(
            select(CatWorldCatProfile.personality_key).where(
                CatWorldCatProfile.phone == phone,
                CatWorldCatProfile.is_active.is_(True),
                CatWorldCatProfile.personality_key.is_not(None),
            )
        ).all()
        if key
    }
    available = [item for item in CAT_WORLD_CAT_PERSONALITIES if item["key"] not in used_keys]
    return secrets.choice(available or CAT_WORLD_CAT_PERSONALITIES)


def cat_world_build_personality_traits(
    personality: dict[str, Any],
) -> dict[str, Any]:
    base_traits = cat_world_cat_traits(None)
    multipliers = personality.get("multipliers") if isinstance(personality.get("multipliers"), dict) else {}

    def varied(key: str) -> float:
        jitter = (secrets.randbelow(13) - 6) / 100
        return float(base_traits[key]) * float(multipliers.get(key) or 1) * (1 + jitter)

    sleep_jitter = secrets.randbelow(3) - 1
    wake_jitter = secrets.randbelow(3) - 1
    rest_jitter = secrets.randbelow(5) - 2
    raw_traits = {
        "activity": personality.get("activity") or "balanced",
        "movement": varied("movement"),
        "energyDrain": varied("energyDrain"),
        "moodDrain": varied("moodDrain"),
        "playMoodGain": varied("playMoodGain"),
        "foodEnergyGain": varied("foodEnergyGain"),
        "restThreshold": int(base_traits["restThreshold"])
        + int(personality.get("restOffset") or 0)
        + rest_jitter,
        "sleepStart": int(
            personality.get(
                "sleepStart",
                int(base_traits["sleepStart"]) + int(personality.get("sleepOffset") or 0) + sleep_jitter,
            )
        ),
        "sleepEnd": int(
            personality.get(
                "sleepEnd",
                int(base_traits["sleepEnd"]) + int(personality.get("wakeOffset") or 0) + wake_jitter,
            )
        ),
        "nightOwl": bool(personality.get("nightOwl", False)),
        "routine": personality.get("routine") or "按自己的节奏观察房间",
        "temperament": personality.get("temperament") or "balanced",
        "label": personality.get("traitLabel") or "有自己的生活节奏和互动偏好。",
        "personalityKey": personality.get("key") or "individual",
        "personalityModel": 2,
    }
    return cat_world_cat_traits({"traits": raw_traits})


def cat_world_assign_profile_personality(
    db: Session,
    profile: CatWorldCatProfile,
) -> bool:
    breed = CAT_WORLD_CAT_BY_ID.get(profile.breed_id, CAT_WORLD_CAT_BY_ID[CAT_WORLD_DEFAULT_CAT_ID])
    personality = CAT_WORLD_CAT_PERSONALITY_BY_KEY.get(str(profile.personality_key or ""))
    changed = False
    if not personality:
        personality = cat_world_personality_choice(db, profile.phone)
        profile.personality_key = str(personality["key"])
        changed = True
    personality_label = str(personality.get("label") or breed.get("personality") or "独立个性猫咪")
    if profile.personality_label != personality_label:
        profile.personality_label = personality_label
        changed = True
    try:
        stored_traits = json.loads(profile.personality_traits or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        stored_traits = {}
    if (
        not isinstance(stored_traits, dict)
        or str(stored_traits.get("personalityKey") or "") != personality["key"]
        or int(stored_traits.get("personalityModel") or 0) < 2
    ):
        profile.personality_traits = json.dumps(
            cat_world_build_personality_traits(personality),
            ensure_ascii=False,
            sort_keys=True,
        )
        changed = True
    if changed:
        db.add(profile)
    return changed


def cat_world_profile_traits(
    profile: CatWorldCatProfile,
    breed: dict[str, Any],
) -> dict[str, Any]:
    try:
        stored_traits = json.loads(profile.personality_traits or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        stored_traits = {}
    if not isinstance(stored_traits, dict) or not stored_traits:
        return cat_world_cat_traits(None)
    return cat_world_cat_traits({"traits": stored_traits})


def create_cat_world_cat_profile(
    db: Session,
    state: CatWorldState,
    breed_id: str,
    source: str = "shop",
) -> CatWorldCatProfile:
    if breed_id not in CAT_WORLD_CAT_BY_ID:
        raise HTTPException(status_code=404, detail="没有找到这个猫咪品种。")
    profile = CatWorldCatProfile(
        profile_id=f"{breed_id}-{uuid4().hex[:10]}",
        phone=state.phone,
        breed_id=breed_id,
        gender=cat_world_random_gender(db),
        pattern_key=secrets.choice(CAT_WORLD_CAT_PATTERNS)["key"],
        feature_key=secrets.choice(CAT_WORLD_CAT_FEATURES)["key"],
        source=source,
        is_active=True,
        adopted_at=datetime.utcnow(),
    )
    cat_world_assign_profile_personality(db, profile)
    db.add(profile)
    db.flush()
    return profile


def cat_world_active_cat_profiles(db: Session, phone: str) -> list[CatWorldCatProfile]:
    return db.scalars(
        select(CatWorldCatProfile)
        .where(
            CatWorldCatProfile.phone == phone,
            CatWorldCatProfile.is_active.is_(True),
        )
        .order_by(CatWorldCatProfile.adopted_at.asc(), CatWorldCatProfile.id.asc())
    ).all()


def cat_world_cat_profile_payload(profile: CatWorldCatProfile) -> dict[str, Any]:
    breed = CAT_WORLD_CAT_BY_ID.get(profile.breed_id, CAT_WORLD_CAT_BY_ID[CAT_WORLD_DEFAULT_CAT_ID])
    pattern = CAT_WORLD_CAT_PATTERN_BY_KEY.get(profile.pattern_key, CAT_WORLD_CAT_PATTERNS[0])
    feature = CAT_WORLD_CAT_FEATURE_BY_KEY.get(profile.feature_key, CAT_WORLD_CAT_FEATURES[0])
    personality = CAT_WORLD_CAT_PERSONALITY_BY_KEY.get(str(profile.personality_key or ""), {})
    personality_label = str(profile.personality_label or personality.get("label") or breed.get("personality") or "独立个性猫咪")
    personality_thoughts = personality.get("thoughts") if isinstance(personality.get("thoughts"), list) else []
    profile_code = str(profile.profile_id).rsplit("-", 1)[-1][:4].upper()
    return {
        **cat_world_cat_payload(breed),
        "id": profile.profile_id,
        "breedId": breed["id"],
        "profileId": profile.profile_id,
        "profileCode": profile_code,
        "displayLabel": f"{breed['label']} · {profile_code}",
        "gender": profile.gender,
        "genderLabel": "公猫" if profile.gender == "male" else "母猫",
        "patternKey": pattern["key"],
        "patternLabel": pattern["label"],
        "featureKey": feature["key"],
        "featureLabel": feature["label"],
        "personalityKey": str(profile.personality_key or ""),
        "personality": personality_label,
        "traits": cat_world_profile_traits(profile, breed),
        "thoughts": personality_thoughts,
        "source": profile.source,
        "adoptedAt": profile.adopted_at.replace(microsecond=0).isoformat() + "Z",
    }


def cat_world_profile_for_reference(
    db: Session,
    state: CatWorldState,
    cat_reference: str | None,
    profiles: list[CatWorldCatProfile] | None = None,
) -> CatWorldCatProfile | None:
    profiles = profiles if profiles is not None else cat_world_active_cat_profiles(db, state.phone)
    reference = str(cat_reference or "").strip()
    by_id = {profile.profile_id: profile for profile in profiles}
    if reference in by_id:
        return by_id[reference]
    selected = by_id.get(str(state.selected_cat_profile or ""))
    if selected and (not reference or selected.breed_id == reference):
        return selected
    return next(
        (profile for profile in reversed(profiles) if profile.breed_id == reference),
        profiles[0] if not reference and profiles else None,
    )


def cat_world_cat_for_reference(
    db: Session,
    state: CatWorldState,
    cat_reference: str | None,
    profiles: list[CatWorldCatProfile] | None = None,
) -> dict[str, Any] | None:
    profile = cat_world_profile_for_reference(db, state, cat_reference, profiles)
    if profile:
        return cat_world_cat_profile_payload(profile)
    breed = CAT_WORLD_CAT_BY_ID.get(str(cat_reference or ""))
    return cat_world_cat_payload(breed) if breed else None


def cat_world_migrate_profile_state(
    state: CatWorldState,
    profiles: list[CatWorldCatProfile],
) -> bool:
    bonds = parse_cat_world_bonds(state.cat_bonds)
    care = parse_cat_world_care(state.cat_care)
    changed = False
    for profile in profiles:
        profile_id = profile.profile_id
        breed_id = profile.breed_id
        if profile_id not in bonds and breed_id in bonds:
            bonds[profile_id] = {
                **cat_world_default_bond(profile_id),
                **bonds[breed_id],
                "catId": profile_id,
            }
            changed = True
        if profile_id not in care and breed_id in care:
            care[profile_id] = {**care[breed_id]}
            changed = True
    if changed:
        state.cat_bonds = encode_cat_world_bonds(bonds)
        state.cat_care = encode_cat_world_care(care)
    return changed


def ensure_cat_world_cat_profiles(
    db: Session,
    state: CatWorldState,
    owned_cats: list[str],
) -> tuple[list[CatWorldCatProfile], bool]:
    profiles = cat_world_active_cat_profiles(db, state.phone)
    profiled_breeds = {profile.breed_id for profile in profiles}
    changed = False
    used_personality_keys: set[str] = set()
    for profile in profiles:
        personality_key = str(profile.personality_key or "")
        if personality_key and personality_key in used_personality_keys:
            profile.personality_key = None
            profile.personality_label = None
            profile.personality_traits = None
            db.add(profile)
            changed = True
        changed = cat_world_assign_profile_personality(db, profile) or changed
        if profile.personality_key:
            used_personality_keys.add(str(profile.personality_key))
    for breed_id in owned_cats:
        if breed_id in profiled_breeds:
            continue
        profile = create_cat_world_cat_profile(db, state, breed_id, "legacy")
        profiles.append(profile)
        profiled_breeds.add(breed_id)
        changed = True
    changed = cat_world_migrate_profile_state(state, profiles) or changed
    profiles_by_id = {profile.profile_id: profile for profile in profiles}
    selected_profile = profiles_by_id.get(str(state.selected_cat_profile or ""))
    if not selected_profile or selected_profile.breed_id != state.selected_cat:
        selected = next(
            (profile for profile in reversed(profiles) if profile.breed_id == state.selected_cat),
            profiles[0] if profiles else None,
        )
        state.selected_cat_profile = selected.profile_id if selected else None
        db.add(state)
        changed = True
    return profiles, changed


def deactivate_cat_world_profiles(
    db: Session,
    phone: str,
    cat_references: list[str],
    escaped_at: datetime,
) -> None:
    if not cat_references:
        return
    references = set(cat_references)
    profiles = db.scalars(
        select(CatWorldCatProfile).where(
            CatWorldCatProfile.phone == phone,
            or_(
                CatWorldCatProfile.profile_id.in_(references),
                CatWorldCatProfile.breed_id.in_(references),
            ),
            CatWorldCatProfile.is_active.is_(True),
        )
    ).all()
    for profile in profiles:
        profile.is_active = False
        profile.escaped_at = escaped_at
        db.add(profile)


def cat_world_decor_favorite_payload() -> list[dict[str, str]]:
    return [
        {
            "decorId": decor_id,
            "decorLabel": CAT_WORLD_DECOR_LABELS.get(decor_id, decor_id),
            "catId": cat_id,
            "catLabel": CAT_WORLD_CAT_BY_ID.get(cat_id, {}).get("label", cat_id),
        }
        for decor_id, cat_id in CAT_WORLD_DECOR_FAVORITE_CAT.items()
    ]


def cat_world_usable_inventory(inventory: dict[str, int], damaged_items: dict[str, dict[str, Any]]) -> dict[str, int]:
    damaged_ids = set(damaged_items)
    return {item_id: count for item_id, count in inventory.items() if item_id not in damaged_ids}


def cat_world_damage_probability(agent_state: dict[str, Any], traits: dict[str, Any], mood_score: int) -> float:
    ready, _reason = cat_world_damage_attempt_ready(agent_state, traits, mood_score)
    if not ready:
        return 0.0
    if mood_score >= 72:
        base = 0.002
    elif mood_score >= 58:
        base = 0.006
    elif mood_score >= 44:
        base = 0.04
    elif mood_score >= 32:
        base = 0.13
    else:
        base = 0.26
    temperament = str(traits.get("temperament") or "balanced")
    temperament_multiplier = {
        "calm": 0.35,
        "gentle": 0.3,
        "clingy": 0.65,
        "chatty": 1.35,
        "guardian": 1.15,
    }.get(temperament, 1.0)
    if agent_state.get("dailyMoodKey") == "grumpy":
        base += 0.075
    if agent_state.get("dailyMoodKey") == "curious":
        base += 0.015
    if agent_state.get("dailyMoodKey") == "bright":
        base *= 0.55
    mischief = min(max(int(agent_state.get("mischief") or 35), 0), 100) / 100
    return min(base * temperament_multiplier * (0.65 + mischief), 0.42)


def cat_world_apply_agent_damage_events(
    db: Session,
    state: CatWorldState,
    inventory: dict[str, int],
    owned_cats: list[str],
    damaged_items: dict[str, dict[str, Any]],
    shop_by_id: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], bool]:
    active_layout = cat_world_active_scene_layout(
        db,
        state,
        cat_world_usable_inventory(inventory, damaged_items),
    )
    candidates = [
        item_id
        for item_id, count in inventory.items()
        if count > 0
        and item_id not in damaged_items
        and item_id in active_layout
        and CAT_WORLD_SHOP_BY_ID.get(item_id, {}).get("category") in {"decor", "toy"}
    ]
    if not candidates:
        return damaged_items, False
    now = datetime.utcnow()
    today = date.today()
    changed = False
    profiles = cat_world_active_cat_profiles(db, state.phone)
    for profile in profiles:
        cat = cat_world_cat_profile_payload(profile)
        cat_id = profile.profile_id
        breed_id = profile.breed_id
        traits = cat_world_cat_traits(cat)
        usable_inventory = cat_world_usable_inventory(inventory, damaged_items)
        favorite_active_ids = cat_world_active_favorite_decor_ids(
            breed_id,
            usable_inventory,
            active_layout,
        )
        log = get_or_create_cat_world_daily_log(db, state.phone, cat_id, today, now, cat)
        apply_cat_world_hourly_decay(
            log,
            traits,
            usable_inventory,
            len(favorite_active_ids),
            now,
            int(state.litter_count or 0),
            cat_world_cat_bath_mood_penalty(state, cat_id, now, cat),
            cat,
        )
        agent_state, agent_changed = ensure_cat_world_agent_state(log, cat, traits)
        if agent_state.get("mischiefChecked"):
            if agent_changed:
                db.add(log)
                changed = True
            continue
        adjusted_mood_score = clamp_cat_world_score(int(log.mood_score or 0) + int(agent_state.get("moodOffset") or 0))
        ready, ready_reason = cat_world_damage_attempt_ready(agent_state, traits, adjusted_mood_score)
        if not ready:
            if agent_changed:
                db.add(log)
                changed = True
            continue
        agent_state["mischiefChecked"] = True
        agent_state["mischiefAttemptedAt"] = now.replace(microsecond=0).isoformat() + "Z"
        agent_state["mischiefAttemptMood"] = adjusted_mood_score
        agent_state["mischiefAttemptReason"] = ready_reason
        probability = cat_world_damage_probability(agent_state, traits, adjusted_mood_score)
        seed = f"{cat_world_daily_agent_seed(today, cat_id, state.phone)}:damage"
        if cat_world_stable_ratio(seed) <= probability:
            candidate_index = min(int(cat_world_stable_ratio(f"{seed}:item") * len(candidates)), len(candidates) - 1)
            item_id = candidates.pop(candidate_index)
            item = shop_by_id.get(item_id) or CAT_WORLD_SHOP_BY_ID[item_id]
            repair_cost = max(round(int(item.get("cost") or 0) * 0.35), 10)
            motive = cat_world_damage_event_motive(agent_state, adjusted_mood_score)
            reason = f"{cat['label']}{motive}，弄坏了{item.get('label') or item_id}。"
            damaged_items[item_id] = {
                "itemId": item_id,
                "label": item.get("label") or item_id,
                "category": item.get("category") or "",
                "catId": cat_id,
                "catLabel": cat["label"],
                "repairCost": repair_cost,
                "reason": reason,
                "damagedAt": now.replace(microsecond=0).isoformat() + "Z",
            }
            agent_state["mischiefItemId"] = item_id
            agent_state["mischiefLabel"] = item.get("label") or item_id
            log.damaged_item_id = item_id
            append_cat_world_agent_event(
                log,
                cat,
                traits,
                "damage",
                "捣蛋损坏",
                reason,
                now,
            )
            changed = True
            if not candidates:
                agent_state["mischiefChecked"] = True
        else:
            append_cat_world_agent_event(
                log,
                cat,
                traits,
                "mischief-check",
                "忍住捣蛋",
                f"{cat['label']}{ready_reason}，但这次没有弄坏道具。",
                now,
            )
            changed = True
        current_state = parse_cat_world_agent_state(log.agent_state)
        agent_state["events"] = cat_world_trim_agent_events(current_state.get("events") or agent_state.get("events"))
        log.agent_state = encode_cat_world_agent_state(agent_state)
        db.add(log)
        changed = True
    return damaged_items, changed


def cat_world_apply_favorite_decor_rewards(
    db: Session,
    state: CatWorldState,
    inventory: dict[str, int],
    room_layout: dict[str, dict[str, float]],
    owned_cats: list[str],
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    now = now or datetime.utcnow()
    rewards: list[dict[str, Any]] = []
    profiles = cat_world_active_cat_profiles(db, state.phone)
    for profile in profiles:
        cat = cat_world_cat_profile_payload(profile)
        cat_id = profile.profile_id
        breed_id = profile.breed_id
        favorite_decor_ids = cat_world_active_favorite_decor_ids(breed_id, inventory, room_layout)
        if not favorite_decor_ids:
            continue
        traits = cat_world_cat_traits(cat)
        log = get_or_create_cat_world_daily_log(db, state.phone, cat_id, date.today(), now, cat)
        apply_cat_world_hourly_decay(
            log,
            traits,
            inventory,
            len(favorite_decor_ids),
            now,
            int(state.litter_count or 0),
            cat_world_cat_bath_mood_penalty(state, cat_id, now, cat),
            cat,
        )
        agent_state, _ = ensure_cat_world_agent_state(log, cat, traits)
        rewarded = agent_state.get("favoriteDecorRewarded")
        if not isinstance(rewarded, list):
            rewarded = []
        rewarded_set = {str(item) for item in rewarded}
        for decor_id in favorite_decor_ids:
            token = f"{log.log_date.isoformat()}:{decor_id}"
            if token in rewarded_set:
                continue
            item = CAT_WORLD_SHOP_BY_ID.get(decor_id, {})
            label = item.get("label") or decor_id
            bonus = 5 if str(traits.get("temperament") or "") in {"clingy", "gentle"} else 4
            log.mood_score = clamp_cat_world_score(int(log.mood_score or 0) + bonus)
            cat_world_apply_cat_bond(state, cat_id, 2, "favorite-decor", label, now)
            rewarded_set.add(token)
            rewards.append(
                {
                    "catId": cat_id,
                    "catLabel": cat["label"],
                    "decorId": decor_id,
                    "decorLabel": label,
                    "moodGain": bonus,
                }
            )
            agent_state = append_cat_world_agent_event(
                log,
                cat,
                traits,
                "favorite-decor-layout",
                "喜欢家具",
                f"你把{label}摆进房间，{cat['label']}很喜欢，心情 +{bonus}。",
                now,
            )
        agent_state["favoriteDecorRewarded"] = sorted(rewarded_set)
        log.agent_state = encode_cat_world_agent_state(agent_state)
        db.add(log)
    return rewards


def cat_world_routine_effect_message(
    cat: dict[str, Any],
    traits: dict[str, Any],
    period_label: str,
    behavior: dict[str, Any],
    mood_key: str,
    roll: float,
    favorite_count: int,
) -> tuple[str, str, int, int]:
    temperament = str(traits.get("temperament") or "balanced")
    cat_label = cat.get("label") or "猫咪"
    behavior_key = str(behavior.get("key") or "")
    if behavior.get("sleeping"):
        return (
            f"{period_label}睡觉",
            f"{cat_label}{period_label}按自己的作息睡了一会儿，体力慢慢回来了。",
            1 if mood_key not in {"grumpy", "quiet"} else 0,
            2,
        )
    if behavior_key == "resting":
        return (
            f"{period_label}休息",
            f"{cat_label}{period_label}体力偏低，自己找了个角落趴着省电。",
            0,
            1,
        )
    if period_label == "夜间" and bool(traits.get("nightOwl")):
        return (
            "夜间巡房",
            f"{cat_label}夜里不太想睡，沿着房间边界巡逻了一圈。",
            1,
            -2,
        )
    if mood_key == "grumpy":
        return (
            f"{period_label}闹情绪",
            f"{cat_label}{period_label}有点别扭，绕开了最热闹的地方。",
            -2,
            -1,
        )
    if temperament == "chatty":
        return (
            f"{period_label}喵语广播",
            f"{cat_label}{period_label}对着房间说了一串喵语，像在复盘刚学的英文。",
            3 if roll > 0.3 else 2,
            -1,
        )
    if temperament == "gentle":
        return (
            f"{period_label}陪读",
            f"{cat_label}{period_label}慢慢趴到柔软的位置旁边，安静陪读。",
            2 + (1 if favorite_count else 0),
            0,
        )
    if temperament == "calm":
        return (
            f"{period_label}整理",
            f"{cat_label}{period_label}检查了一下书架和窗台，确认房间很适合背单词。",
            1 + (1 if favorite_count else 0),
            0,
        )
    if temperament == "guardian":
        return (
            f"{period_label}巡逻",
            f"{cat_label}{period_label}守着房间入口巡逻，顺便看看有没有东西被碰歪。",
            1,
            -2 if roll > 0.45 else -1,
        )
    if mood_key in {"bright", "curious"}:
        return (
            f"{period_label}探索",
            f"{cat_label}{period_label}兴致很好，去房间里找了一个新路线。",
            2,
            -1,
        )
    return (
        f"{period_label}日常",
        f"{cat_label}{period_label}按自己的节奏在房间里待了一会儿。",
        1 + (1 if favorite_count and roll > 0.5 else 0),
        0,
    )


def cat_world_apply_agent_routine_event(
    log: CatWorldDailyLog,
    cat: dict[str, Any],
    traits: dict[str, Any],
    inventory: dict[str, int],
    favorite_active_ids: list[str],
    now: datetime,
) -> bool:
    agent_state, _ = ensure_cat_world_agent_state(log, cat, traits)
    period_key, period_label = cat_world_routine_period(now)
    routine_periods = agent_state.get("routinePeriodEvents")
    if not isinstance(routine_periods, dict):
        routine_periods = {}
    token = f"{log.log_date.isoformat()}:{period_key}"
    if routine_periods.get(period_key) == token:
        return False
    mood_score = clamp_cat_world_score(int(log.mood_score or 0) + int(agent_state.get("moodOffset") or 0))
    energy_score = clamp_cat_world_score(int(log.energy_score or 0) + int(agent_state.get("energyOffset") or 0))
    behavior = cat_world_current_behavior(agent_state, traits, mood_score, energy_score, now)
    seed = f"{cat_world_daily_agent_seed(log.log_date, cat['id'], log.phone)}:routine:{period_key}"
    roll = cat_world_stable_ratio(seed)
    label, message, mood_delta, energy_delta = cat_world_routine_effect_message(
        cat,
        traits,
        period_label,
        behavior,
        str(agent_state.get("dailyMoodKey") or ""),
        roll,
        len(favorite_active_ids),
    )
    mood_delta = int(min(max(mood_delta, -3), 5))
    energy_delta = int(min(max(energy_delta, -4), 4))
    if mood_delta:
        log.mood_score = clamp_cat_world_score(int(log.mood_score or 0) + mood_delta)
    if energy_delta:
        log.energy_score = clamp_cat_world_score(int(log.energy_score or 0) + energy_delta)
    effect_parts = []
    if energy_delta:
        effect_parts.append(f"体力 {cat_world_signed_change(energy_delta)}")
    if mood_delta:
        effect_parts.append(f"心情 {cat_world_signed_change(mood_delta)}")
    if effect_parts:
        effect_text = "，".join(effect_parts)
        message = f"{message}（{effect_text}）"
    agent_state = append_cat_world_agent_event(
        log,
        cat,
        traits,
        "routine-period",
        label,
        message,
        now,
    )
    routine_periods[period_key] = token
    agent_state["routinePeriodEvents"] = routine_periods
    log.agent_state = encode_cat_world_agent_state(agent_state)
    return True


def cat_world_litter_interval_seconds(owned_cat_count: int) -> int:
    count = max(int(owned_cat_count or 1), 1)
    return max(round((8 * 60 * 60) / count), 2 * 60 * 60)


def cat_world_parse_utc_datetime(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def cat_world_pet_reward_cooldown(
    last_pet_at: str | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.utcnow()
    parsed = cat_world_parse_utc_datetime(last_pet_at)
    if parsed is None:
        return {"active": False, "remainingSeconds": 0}
    elapsed_seconds = max((now - parsed).total_seconds(), 0)
    remaining_seconds = max(math.ceil(CAT_WORLD_PET_REWARD_COOLDOWN_SECONDS - elapsed_seconds), 0)
    return {
        "active": remaining_seconds > 0,
        "remainingSeconds": remaining_seconds,
    }


def cat_world_latest_pet_at(
    db: Session,
    phone: str,
    cat_id: str,
    current_agent_state: dict[str, Any],
) -> str:
    candidates = [str(current_agent_state.get("lastPetAt") or "")]
    recent_agent_states = db.scalars(
        select(CatWorldDailyLog.agent_state)
        .where(
            CatWorldDailyLog.phone == normalize_login_phone(phone),
            CatWorldDailyLog.cat_id == cat_id,
        )
        .order_by(CatWorldDailyLog.log_date.desc(), CatWorldDailyLog.id.desc())
        .limit(2)
    ).all()
    for raw_state in recent_agent_states:
        candidates.append(str(parse_cat_world_agent_state(raw_state).get("lastPetAt") or ""))
    parsed_candidates = [
        (parsed, raw)
        for raw in candidates
        if (parsed := cat_world_parse_utc_datetime(raw)) is not None
    ]
    if not parsed_candidates:
        return ""
    return max(parsed_candidates, key=lambda item: item[0])[1]


def cat_world_litter_age_hours(
    state: CatWorldState,
    now: datetime | None = None,
) -> int:
    if int(state.litter_count or 0) <= 0:
        return 0
    now = now or datetime.utcnow()
    started_at = state.litter_started_at or state.litter_updated_at
    if not started_at:
        return 0
    return max(int((now - started_at).total_seconds()) // (60 * 60), 0)


def cat_world_litter_bath_acceleration_hours(
    state: CatWorldState,
    now: datetime | None = None,
) -> int:
    litter_age_hours = cat_world_litter_age_hours(state, now)
    accelerated_hours = max(litter_age_hours - CAT_WORLD_LITTER_BATH_GRACE_HOURS, 0)
    return min(
        accelerated_hours * CAT_WORLD_LITTER_BATH_ACCELERATION_RATE,
        CAT_WORLD_LITTER_BATH_ACCELERATION_MAX_HOURS,
    )


def cat_world_ensure_care_records(
    state: CatWorldState,
    owned_cats: list[str],
    now: datetime | None = None,
) -> tuple[dict[str, dict[str, Any]], bool]:
    now = now or datetime.utcnow()
    care = parse_cat_world_care(state.cat_care)
    changed = False
    for cat_id in owned_cats:
        if cat_id in care and cat_world_parse_utc_datetime(care[cat_id].get("lastBathAt")):
            continue
        cat = CAT_WORLD_CAT_BY_ID.get(cat_id, CAT_WORLD_CAT_BY_ID[CAT_WORLD_DEFAULT_CAT_ID])
        profile = cat_world_cleanliness_profile(state.phone, cat_id, cat_world_cat_traits(cat))
        interval_days = max(int(profile.get("bathIntervalDays") or 4), 2)
        initial_age_seconds = int(
            cat_world_stable_ratio(f"{state.phone}:{cat_id}:initial-bath-age")
            * (interval_days + 1.5)
            * 24
            * 60
            * 60
        )
        care[cat_id] = {
            "lastBathAt": (now - timedelta(seconds=initial_age_seconds)).replace(microsecond=0).isoformat() + "Z",
            "bathCount": 0,
        }
        changed = True
    if changed:
        state.cat_care = encode_cat_world_care(care)
    return care, changed


def cat_world_ensure_profile_care_records(
    state: CatWorldState,
    profiles: list[CatWorldCatProfile],
    now: datetime | None = None,
) -> tuple[dict[str, dict[str, Any]], bool]:
    now = now or datetime.utcnow()
    care = parse_cat_world_care(state.cat_care)
    changed = False
    for profile_row in profiles:
        profile_id = profile_row.profile_id
        if profile_id in care and cat_world_parse_utc_datetime(care[profile_id].get("lastBathAt")):
            continue
        cat = cat_world_cat_profile_payload(profile_row)
        cleanliness = cat_world_cleanliness_profile(state.phone, profile_id, cat_world_cat_traits(cat))
        interval_days = max(int(cleanliness.get("bathIntervalDays") or 4), 2)
        initial_age_seconds = int(
            cat_world_stable_ratio(f"{state.phone}:{profile_id}:initial-bath-age")
            * (interval_days + 1.5)
            * 24
            * 60
            * 60
        )
        care[profile_id] = {
            **care.get(profile_row.breed_id, {}),
            "lastBathAt": (now - timedelta(seconds=initial_age_seconds)).replace(microsecond=0).isoformat() + "Z",
            "bathCount": max(int(care.get(profile_row.breed_id, {}).get("bathCount") or 0), 0),
        }
        changed = True
    if changed:
        state.cat_care = encode_cat_world_care(care)
    return care, changed


def cat_world_cat_hygiene_payload(
    state: CatWorldState,
    cat_id: str,
    care: dict[str, dict[str, Any]] | None = None,
    now: datetime | None = None,
    cat: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = now or datetime.utcnow()
    cat = cat or CAT_WORLD_CAT_BY_ID.get(cat_id, CAT_WORLD_CAT_BY_ID[CAT_WORLD_DEFAULT_CAT_ID])
    profile = cat_world_cleanliness_profile(state.phone, cat_id, cat_world_cat_traits(cat))
    care = care if care is not None else parse_cat_world_care(state.cat_care)
    row = care.get(cat_id, {})
    last_bath_at = cat_world_parse_utc_datetime(row.get("lastBathAt")) or now
    interval_days = max(int(profile.get("bathIntervalDays") or 4), 2)
    elapsed_seconds = max(int((now - last_bath_at).total_seconds()), 0)
    litter_age_hours = cat_world_litter_age_hours(state, now)
    bath_acceleration_hours = cat_world_litter_bath_acceleration_hours(state, now)
    effective_elapsed_seconds = elapsed_seconds + bath_acceleration_hours * 60 * 60
    due_seconds = interval_days * 24 * 60 * 60
    needs_bath = effective_elapsed_seconds >= due_seconds
    overdue_days = (
        max(int((effective_elapsed_seconds - due_seconds) // (24 * 60 * 60)) + 1, 0)
        if needs_bath
        else 0
    )
    mood_decay_bonus = min(1 + overdue_days, 4) if needs_bath else 0
    next_bath_at = last_bath_at + timedelta(days=interval_days, hours=-bath_acceleration_hours)
    return {
        **profile,
        "lastBathAt": last_bath_at.replace(microsecond=0).isoformat() + "Z",
        "lastBathDate": last_bath_at.date().isoformat(),
        "bathCount": max(int(row.get("bathCount") or 0), 0),
        "daysSinceBath": elapsed_seconds // (24 * 60 * 60),
        "nextBathAt": next_bath_at.replace(microsecond=0).isoformat() + "Z",
        "nextBathDate": next_bath_at.date().isoformat(),
        "daysUntilBath": max((due_seconds - effective_elapsed_seconds + 86399) // (24 * 60 * 60), 0),
        "litterAgeHours": litter_age_hours,
        "bathAccelerationHours": bath_acceleration_hours,
        "bathAccelerationActive": bath_acceleration_hours > 0,
        "bathAccelerationLabel": (
            f"猫屎已滞留 {litter_age_hours} 小时，洗澡进度额外 +{bath_acceleration_hours} 小时"
            if bath_acceleration_hours > 0
            else ""
        ),
        "needsBath": needs_bath,
        "overdueDays": overdue_days,
        "moodDecayBonus": mood_decay_bonus,
        "furState": "frazzled" if needs_bath else "clean",
        "statusLabel": (
            "炸毛待洗澡"
            if needs_bath
            else "猫屎久置 · 加速变脏"
            if bath_acceleration_hours > 0
            else "干净清爽"
        ),
    }


def cat_world_cat_bath_mood_penalty(
    state: CatWorldState,
    cat_id: str,
    now: datetime | None = None,
    cat: dict[str, Any] | None = None,
) -> int:
    return int(cat_world_cat_hygiene_payload(state, cat_id, now=now, cat=cat).get("moodDecayBonus") or 0)


def cat_world_elapsed_care_hours(value: str | None, now: datetime) -> int:
    started_at = cat_world_parse_utc_datetime(value)
    if not started_at:
        return 0
    return max(int((now - started_at).total_seconds() // 3600), 0)


def cat_world_update_neglect_status(
    cat_id: str,
    care: dict[str, dict[str, Any]],
    energy_score: int,
    mood_score: int,
    now: datetime,
    breed_id: str | None = None,
) -> tuple[dict[str, Any], bool]:
    row = {**care.get(cat_id, {})}
    changed = False
    now_text = now.replace(microsecond=0).isoformat() + "Z"
    energy_score = clamp_cat_world_score(energy_score)
    mood_score = clamp_cat_world_score(mood_score)

    if energy_score <= CAT_WORLD_HUNGER_WARNING_SCORE:
        if not cat_world_parse_utc_datetime(row.get("hungerSince")):
            row["hungerSince"] = now_text
            changed = True
    elif row.get("hungerSince"):
        row["hungerSince"] = ""
        changed = True

    if mood_score <= CAT_WORLD_LOW_MOOD_WARNING_SCORE:
        if not cat_world_parse_utc_datetime(row.get("lowMoodSince")):
            row["lowMoodSince"] = now_text
            changed = True
    elif row.get("lowMoodSince"):
        row["lowMoodSince"] = ""
        changed = True

    hunger_hours = cat_world_elapsed_care_hours(row.get("hungerSince"), now)
    low_mood_hours = cat_world_elapsed_care_hours(row.get("lowMoodSince"), now)
    hunger_critical = bool(row.get("hungerSince")) and hunger_hours >= CAT_WORLD_HUNGER_CRITICAL_HOURS
    low_mood_critical = bool(row.get("lowMoodSince")) and low_mood_hours >= CAT_WORLD_LOW_MOOD_CRITICAL_HOURS
    hunger_escape = bool(row.get("hungerSince")) and hunger_hours >= CAT_WORLD_HUNGER_ESCAPE_HOURS
    low_mood_escape = bool(row.get("lowMoodSince")) and low_mood_hours >= CAT_WORLD_LOW_MOOD_ESCAPE_HOURS
    limited_cat = bool(CAT_WORLD_CAT_BY_ID.get(str(breed_id or cat_id), {}).get("limited"))
    escaped = (hunger_escape or low_mood_escape) and not limited_cat
    escape_reason = "hunger" if hunger_escape else ("low-mood" if low_mood_escape else "")
    escape_label = "连续 3 天挨饿" if escape_reason == "hunger" else ("连续 5 天心情跌至谷底" if escape_reason else "")
    if escaped and not row.get("escapedAt"):
        row["escapedAt"] = now_text
        row["escapeReason"] = escape_reason
        row["escapeLabel"] = escape_label
        changed = True

    if hunger_critical:
        status_key = "near-death"
        status_label = "濒临死亡"
        message = f"已经连续 {hunger_hours} 小时严重挨饿，需要马上喂食。"
        remaining_hours = max(CAT_WORLD_HUNGER_ESCAPE_HOURS - hunger_hours, 0)
    elif low_mood_critical:
        status_key = "leaving"
        status_label = "想离家"
        message = f"已经连续 {low_mood_hours} 小时心情跌至谷底，需要陪伴、玩具或护理。"
        remaining_hours = max(CAT_WORLD_LOW_MOOD_ESCAPE_HOURS - low_mood_hours, 0)
    elif row.get("hungerSince"):
        status_key = "starving"
        status_label = "严重饥饿"
        message = f"体力已经见底 {hunger_hours} 小时，尽快喂食可停止危险计时。"
        remaining_hours = max(CAT_WORLD_HUNGER_ESCAPE_HOURS - hunger_hours, 0)
    elif row.get("lowMoodSince"):
        status_key = "despair"
        status_label = "情绪低谷"
        message = f"心情已经低落 {low_mood_hours} 小时，尽快互动可停止离家计时。"
        remaining_hours = max(CAT_WORLD_LOW_MOOD_ESCAPE_HOURS - low_mood_hours, 0)
    else:
        status_key = "safe"
        status_label = "照护安全"
        message = "体力和心情都在安全范围。"
        remaining_hours = 0

    care[cat_id] = row
    return {
        "statusKey": "escaped" if escaped else status_key,
        "statusLabel": "已经离家" if escaped else status_label,
        "message": f"{escape_label}，猫咪已经跑出活动室。" if escaped else message,
        "energyScore": energy_score,
        "moodScore": mood_score,
        "hungerSince": str(row.get("hungerSince") or ""),
        "lowMoodSince": str(row.get("lowMoodSince") or ""),
        "hungerHours": hunger_hours,
        "lowMoodHours": low_mood_hours,
        "remainingHours": remaining_hours,
        "isWarning": status_key != "safe",
        "isCritical": hunger_critical or low_mood_critical,
        "escaped": escaped,
        "escapedAt": str(row.get("escapedAt") or ""),
        "escapeReason": str(row.get("escapeReason") or ""),
        "escapeLabel": str(row.get("escapeLabel") or ""),
        "hungerCriticalHours": CAT_WORLD_HUNGER_CRITICAL_HOURS,
        "hungerEscapeHours": CAT_WORLD_HUNGER_ESCAPE_HOURS,
        "lowMoodCriticalHours": CAT_WORLD_LOW_MOOD_CRITICAL_HOURS,
        "lowMoodEscapeHours": CAT_WORLD_LOW_MOOD_ESCAPE_HOURS,
    }, changed


def cat_world_lost_cats_payload(
    db: Session,
    phone: str,
    care: dict[str, dict[str, Any]],
    owned_cats: list[str],
) -> dict[str, dict[str, Any]]:
    owned = set(owned_cats)
    profile_ids = [cat_id for cat_id in care if cat_id not in CAT_WORLD_CAT_BY_ID]
    profiles_by_id = {
        profile.profile_id: profile
        for profile in (
            db.scalars(
                select(CatWorldCatProfile).where(
                    CatWorldCatProfile.phone == normalize_login_phone(phone),
                    CatWorldCatProfile.profile_id.in_(profile_ids),
                )
            ).all()
            if profile_ids
            else []
        )
    }
    payload: dict[str, dict[str, Any]] = {}
    for cat_reference, row in care.items():
        profile = profiles_by_id.get(cat_reference)
        breed_id = profile.breed_id if profile else cat_reference
        if breed_id in owned or not row.get("escapedAt"):
            continue
        cat = CAT_WORLD_CAT_BY_ID.get(breed_id)
        if not cat:
            continue
        payload[breed_id] = {
            "catId": breed_id,
            "profileId": profile.profile_id if profile else "",
            "catLabel": cat.get("label") or breed_id,
            "escapedAt": str(row.get("escapedAt") or ""),
            "escapeReason": str(row.get("escapeReason") or ""),
            "escapeLabel": str(row.get("escapeLabel") or "长期缺少照护"),
            "message": f"{cat.get('label') or '猫咪'}因为{row.get('escapeLabel') or '长期缺少照护'}离家了，可以在商店重新领养。",
        }
    return payload


def cat_world_refresh_litter(
    state: CatWorldState,
    inventory: dict[str, int],
    owned_cats: list[str],
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.utcnow()
    interval_seconds = cat_world_litter_interval_seconds(len(owned_cats))
    changed = False
    count = min(max(int(state.litter_count or 0), 0), CAT_WORLD_LITTER_MAX)
    if count > 0 and not state.litter_started_at:
        state.litter_started_at = state.litter_updated_at or now
        changed = True
    elif count <= 0 and state.litter_started_at:
        state.litter_started_at = None
        changed = True
    if not owned_cats:
        litter_age_hours = cat_world_litter_age_hours(state, now)
        bath_acceleration_hours = cat_world_litter_bath_acceleration_hours(state, now)
        return {
            "count": count,
            "hasLitter": count > 0,
            "maxCount": CAT_WORLD_LITTER_MAX,
            "moodDecayBonus": 0,
            "intervalSeconds": interval_seconds,
            "nextAt": "",
            "scoopCount": max(int(inventory.get(CAT_WORLD_LITTER_SCOOP_ITEM_ID, 0) or 0), 0),
            "catLitterCount": max(int(inventory.get(CAT_WORLD_LITTER_ITEM_ID, 0) or 0), 0),
            "placedCatLitterCount": max(int(state.litter_ready_count or 0), 0),
            "hasPlacedCatLitter": int(state.litter_ready_count or 0) > 0,
            "autoUsed": 0,
            "addedCount": 0,
            "oldestAt": (
                state.litter_started_at.replace(microsecond=0).isoformat() + "Z"
                if state.litter_started_at
                else ""
            ),
            "litterAgeHours": litter_age_hours,
            "bathAccelerationHours": bath_acceleration_hours,
            "bathAccelerationActive": bath_acceleration_hours > 0,
            "bathGraceHours": CAT_WORLD_LITTER_BATH_GRACE_HOURS,
            "changed": changed,
        }
    if not state.litter_updated_at:
        state.litter_updated_at = now - timedelta(seconds=interval_seconds)
        changed = True
    elapsed_seconds = max(int((now - state.litter_updated_at).total_seconds()), 0)
    due_count = min(elapsed_seconds // interval_seconds, CAT_WORLD_LITTER_MAX)
    auto_used = 0
    added_count = 0
    if due_count > 0:
        ready_litter = max(int(state.litter_ready_count or 0), 0)
        auto_used = min(int(due_count), ready_litter)
        if auto_used:
            state.litter_ready_count = max(ready_litter - auto_used, 0)
        unprotected_count = int(due_count) - auto_used
        current_count = min(max(int(state.litter_count or 0), 0), CAT_WORLD_LITTER_MAX)
        next_count = min(current_count + unprotected_count, CAT_WORLD_LITTER_MAX)
        added_count = max(next_count - current_count, 0)
        state.litter_count = next_count
        if added_count > 0 and current_count <= 0:
            state.litter_started_at = now
        state.litter_updated_at = now
        changed = True
    count = min(max(int(state.litter_count or 0), 0), CAT_WORLD_LITTER_MAX)
    next_at = (state.litter_updated_at or now) + timedelta(seconds=interval_seconds)
    litter_age_hours = cat_world_litter_age_hours(state, now)
    bath_acceleration_hours = cat_world_litter_bath_acceleration_hours(state, now)
    return {
        "count": count,
        "hasLitter": count > 0,
        "maxCount": CAT_WORLD_LITTER_MAX,
        "moodDecayBonus": cat_world_litter_mood_penalty(count),
        "intervalSeconds": interval_seconds,
        "nextAt": next_at.replace(microsecond=0).isoformat() + "Z",
        "scoopCount": max(int(inventory.get(CAT_WORLD_LITTER_SCOOP_ITEM_ID, 0) or 0), 0),
        "catLitterCount": max(int(inventory.get(CAT_WORLD_LITTER_ITEM_ID, 0) or 0), 0),
        "placedCatLitterCount": max(int(state.litter_ready_count or 0), 0),
        "hasPlacedCatLitter": int(state.litter_ready_count or 0) > 0,
        "autoUsed": auto_used,
        "addedCount": added_count,
        "oldestAt": (
            state.litter_started_at.replace(microsecond=0).isoformat() + "Z"
            if state.litter_started_at
            else ""
        ),
        "litterAgeHours": litter_age_hours,
        "bathAccelerationHours": bath_acceleration_hours,
        "bathAccelerationActive": bath_acceleration_hours > 0,
        "bathGraceHours": CAT_WORLD_LITTER_BATH_GRACE_HOURS,
        "changed": changed,
    }


def cat_world_apply_daily_decay(
    db: Session,
    state: CatWorldState,
    inventory: dict[str, int],
    cat_profiles: list[CatWorldCatProfile],
    room_layout: dict[str, dict[str, float]],
) -> dict[str, dict[str, Any]]:
    now = datetime.utcnow()
    today = date.today()
    changed = False
    payload: dict[str, dict[str, Any]] = {}
    care, care_changed = cat_world_ensure_profile_care_records(state, cat_profiles, now)
    changed = care_changed or changed
    escaped_profile_ids: list[str] = []
    for profile in cat_profiles:
        cat = cat_world_cat_profile_payload(profile)
        cat_id = profile.profile_id
        breed_id = profile.breed_id
        traits = cat_world_cat_traits(cat)
        favorite_active_ids = cat_world_active_favorite_decor_ids(breed_id, inventory, room_layout)
        log = get_or_create_cat_world_daily_log(db, state.phone, cat_id, today, now, cat)
        hygiene = cat_world_cat_hygiene_payload(state, cat_id, care, now, cat)
        changed = apply_cat_world_hourly_decay(
            log,
            traits,
            inventory,
            len(favorite_active_ids),
            now,
            int(state.litter_count or 0),
            int(hygiene.get("moodDecayBonus") or 0),
            cat,
        ) or changed
        changed = cat_world_apply_agent_routine_event(log, cat, traits, inventory, favorite_active_ids, now) or changed
        db.add(log)
        row = cat_world_daily_log_payload(log, favorite_active_ids, inventory, room_layout, cat)
        row["hygiene"] = hygiene
        neglect, neglect_changed = cat_world_update_neglect_status(
            cat_id,
            care,
            int(row.get("energyScore") or 0),
            int(row.get("moodScore") or 0),
            now,
            breed_id,
        )
        changed = neglect_changed or changed
        row["neglect"] = neglect
        agent_state = row.get("agentState") if isinstance(row.get("agentState"), dict) else {}
        agent_state["hygiene"] = hygiene
        agent_state["neglect"] = neglect
        if hygiene.get("needsBath"):
            litter_bath_reason = (
                f"；猫屎久置让洗澡进度额外增加了 {hygiene.get('bathAccelerationHours') or 0} 小时"
                if hygiene.get("bathAccelerationActive")
                else ""
            )
            agent_state["careNeed"] = {
                "key": "bath",
                "label": "炸毛了",
                "actionLabel": "使用洗澡用品",
                "message": f"{cat['label']}已经 {hygiene.get('daysSinceBath') or 0} 天没洗澡，毛发炸开了{litter_bath_reason}，心情每小时额外 -{hygiene.get('moodDecayBonus') or 0}。",
                "status": "urgent",
                "priority": 92,
                "targetType": "consumable",
                "targetItemId": CAT_WORLD_BATH_ITEM_ID,
                "targetLabel": "泡泡浴套装",
            }
            agent_state["careTip"] = (
                f"使用猫咪泡泡浴套装，洗澡后恢复整洁；这只猫每 {hygiene.get('bathIntervalDays') or 4} 天需要洗一次。"
                + (" 铲净猫屎可以立刻停止变脏加速。" if hygiene.get("bathAccelerationActive") else "")
            )
        if neglect.get("isWarning"):
            hunger_risk = str(neglect.get("statusKey") or "") in {"starving", "near-death"}
            agent_state["careNeed"] = {
                "key": "survival-food" if hunger_risk else "survival-mood",
                "label": str(neglect.get("statusLabel") or "需要紧急照护"),
                "actionLabel": "马上喂食" if hunger_risk else "马上安抚",
                "message": str(neglect.get("message") or "需要马上照顾。"),
                "status": "urgent",
                "priority": 100 if neglect.get("isCritical") else 96,
                "targetType": "food" if hunger_risk else "interaction",
                "targetItemId": "",
                "targetLabel": "食物" if hunger_risk else "陪伴",
            }
            agent_state["careTip"] = (
                f"危险倒计时剩余约 {int(neglect.get('remainingHours') or 0)} 小时；"
                + ("摆放食物并让猫咪吃完即可停止挨饿计时。" if hunger_risk else "摸摸、玩具和护理用品都能帮助恢复心情。")
            )
        if neglect.get("escaped"):
            escaped_profile_ids.append(cat_id)
        row["agentState"] = agent_state
        payload[cat_id] = row
    state.cat_care = encode_cat_world_care(care)
    if escaped_profile_ids:
        escaped_set = set(escaped_profile_ids)
        remaining_profiles = [profile for profile in cat_profiles if profile.profile_id not in escaped_set]
        remaining_cats = list(dict.fromkeys(profile.breed_id for profile in remaining_profiles))
        state.cats = encode_cat_world_cats(remaining_cats)
        deactivate_cat_world_profiles(db, state.phone, escaped_profile_ids, now)
        if state.selected_cat_profile in escaped_set:
            selected = remaining_profiles[0] if remaining_profiles else None
            state.selected_cat = selected.breed_id if selected else ""
            state.selected_cat_profile = selected.profile_id if selected else None
        if state.active_food_cat_id in escaped_set:
            state.active_food_item = None
            state.active_food_cat_id = None
            state.active_food_at = None
        if state.active_care_cat_id in escaped_set:
            state.active_care_item = None
            state.active_care_cat_id = None
            state.active_care_at = None
        for cat_id in escaped_profile_ids:
            payload.pop(cat_id, None)
        changed = True
    db.add(state)
    if changed or payload:
        db.commit()
    return payload


def cat_world_active_care_payload(
    db: Session,
    state: CatWorldState,
    now: datetime | None = None,
) -> dict[str, Any]:
    item_id = str(state.active_care_item or "").strip()
    item = CAT_WORLD_SHOP_BY_ID.get(item_id)
    if not item or item.get("category") != "consumable" or item.get("useType") != "room-place" or not state.active_care_at:
        return {"active": False, "changed": False, "itemId": "", "remainingSeconds": 0}
    now = now or datetime.utcnow()
    duration_seconds = max(int(item.get("durationMinutes") or 20), 1) * 60
    elapsed_seconds = max(int((now - state.active_care_at).total_seconds()), 0)
    remaining_seconds = max(duration_seconds - elapsed_seconds, 0)
    if remaining_seconds <= 0:
        state.active_care_item = None
        state.active_care_cat_id = None
        state.active_care_at = None
        return {"active": False, "changed": True, "itemId": "", "remainingSeconds": 0}
    target_cat = cat_world_cat_for_reference(db, state, str(state.active_care_cat_id or ""))
    expires_at = state.active_care_at + timedelta(seconds=duration_seconds)
    return {
        "active": True,
        "changed": False,
        "itemId": item_id,
        "label": item.get("label") or item_id,
        "englishName": item.get("englishName") or "",
        "targetCatId": (target_cat.get("profileId") or target_cat.get("id")) if target_cat else "",
        "targetCatLabel": (target_cat.get("displayLabel") or target_cat.get("label")) if target_cat else "",
        "remainingSeconds": remaining_seconds,
        "durationSeconds": duration_seconds,
        "startedAt": state.active_care_at.replace(microsecond=0).isoformat() + "Z",
        "expiresAt": expires_at.replace(microsecond=0).isoformat() + "Z",
    }


def cat_world_active_food_token(state: CatWorldState, item_id: str, cat_id: str) -> str:
    started_at = state.active_food_at.replace(microsecond=0).isoformat() if state.active_food_at else ""
    return f"{item_id}:{cat_id}:{started_at}"


def cat_world_food_progress_targets(
    item: dict[str, Any],
    traits: dict[str, Any],
    active_food_at: datetime,
    now: datetime,
    cat_id: str = "",
    force_initial: bool = False,
) -> dict[str, int | bool]:
    duration_seconds = max(int(item.get("durationMinutes") or 30), 1) * 60
    elapsed_seconds = max(int((now - active_food_at).total_seconds()), 0)
    ratio = min(max(elapsed_seconds / duration_seconds, 0.0), 1.0)
    favorite_multiplier = cat_world_food_favorite_multiplier(item, cat_id)
    food_multiplier = float(traits["foodEnergyGain"]) * favorite_multiplier
    total_energy = max(round(int(item.get("catEnergy") or 0) * food_multiplier), 0)
    total_mood = max(round(int(item.get("mood") or 0) * food_multiplier), 0)
    consumed_energy = min(total_energy, round(total_energy * ratio))
    consumed_mood = min(total_mood, round(total_mood * ratio))
    if force_initial:
        consumed_energy = min(total_energy, max(consumed_energy, min(total_energy, max(1, round(total_energy * 0.18)))))
        consumed_mood = min(total_mood, max(consumed_mood, min(total_mood, max(1, round(total_mood * 0.18)))))
    remaining_seconds = max(duration_seconds - elapsed_seconds, 0)
    return {
        "totalEnergy": total_energy,
        "totalMood": total_mood,
        "consumedEnergy": consumed_energy,
        "consumedMood": consumed_mood,
        "remainingEnergy": max(total_energy - consumed_energy, 0),
        "remainingMood": max(total_mood - consumed_mood, 0),
        "remainingSeconds": remaining_seconds,
        "durationSeconds": duration_seconds,
        "complete": remaining_seconds <= 0 or consumed_energy >= total_energy,
    }


def cat_world_apply_active_food_progress(
    db: Session,
    state: CatWorldState,
    inventory: dict[str, int],
    room_layout: dict[str, dict[str, float]],
    now: datetime | None = None,
    force_initial: bool = False,
) -> dict[str, Any]:
    item_id = str(state.active_food_item or "").strip()
    item = CAT_WORLD_SHOP_BY_ID.get(item_id)
    if not item or item.get("category") != "food" or not state.active_food_at:
        return {"active": False, "changed": False}
    now = now or datetime.utcnow()
    changed = False
    target_cat_id = str(state.active_food_cat_id or "").strip()
    cat = cat_world_cat_for_reference(db, state, target_cat_id)
    if not cat:
        target_cat_id = cat_world_effect_target_cat_id(db, state, inventory, room_layout, "food", item_id)
        state.active_food_cat_id = target_cat_id
        cat = cat_world_cat_for_reference(db, state, target_cat_id)
        changed = True
    cat = cat or cat_world_cat_payload(CAT_WORLD_CAT_BY_ID[CAT_WORLD_DEFAULT_CAT_ID])
    breed_id = str(cat.get("breedId") or cat.get("id"))
    traits = cat_world_cat_traits(cat)
    favorite_active_ids = cat_world_active_favorite_decor_ids(breed_id, inventory, room_layout)
    log = get_or_create_cat_world_daily_log(db, state.phone, target_cat_id, date.today(), now, cat)
    changed = apply_cat_world_hourly_decay(
        log,
        traits,
        inventory,
        len(favorite_active_ids),
        now,
        int(state.litter_count or 0),
        cat_world_cat_bath_mood_penalty(state, target_cat_id, now, cat),
        cat,
    ) or changed
    agent_state, _ = ensure_cat_world_agent_state(log, cat, traits)
    token = cat_world_active_food_token(state, item_id, target_cat_id)
    if agent_state.get("activeFoodToken") != token:
        agent_state["activeFoodToken"] = token
        agent_state["activeFoodConsumedEnergy"] = 0
        agent_state["activeFoodConsumedMood"] = 0
        agent_state["activeFoodLabel"] = item.get("label") or item_id
        agent_state["activeFoodStartedAt"] = state.active_food_at.replace(microsecond=0).isoformat() + "Z"
        agent_state["activeFoodManualBites"] = 0
        agent_state["activeFoodNibbleAt"] = ""
        changed = True
    favorite_match = cat_world_item_favorite_cat_id(item_id) == breed_id
    progress = cat_world_food_progress_targets(item, traits, state.active_food_at, now, breed_id, force_initial=force_initial)
    previous_energy = max(int(agent_state.get("activeFoodConsumedEnergy") or 0), 0)
    previous_mood = max(int(agent_state.get("activeFoodConsumedMood") or 0), 0)
    total_energy = int(progress["totalEnergy"])
    total_mood = int(progress["totalMood"])
    next_energy = min(total_energy, max(int(progress["consumedEnergy"]), previous_energy))
    next_mood = min(total_mood, max(int(progress["consumedMood"]), previous_mood))
    delta_energy = max(next_energy - previous_energy, 0)
    delta_mood = max(next_mood - previous_mood, 0)
    remaining_energy = max(total_energy - next_energy, 0)
    remaining_mood = max(total_mood - next_mood, 0)
    remaining_seconds = int(progress["remainingSeconds"])
    complete = remaining_seconds <= 0 or next_energy >= total_energy
    if delta_energy or delta_mood:
        log.energy_score = clamp_cat_world_score(int(log.energy_score or 0) + delta_energy)
        log.mood_score = clamp_cat_world_score(int(log.mood_score or 0) + delta_mood)
        agent_state["activeFoodConsumedEnergy"] = next_energy
        agent_state["activeFoodConsumedMood"] = next_mood
        agent_state["activeFoodRemainingEnergy"] = remaining_energy
        agent_state["activeFoodRemainingMood"] = remaining_mood
        agent_state["activeFoodRemainingSeconds"] = remaining_seconds
        log.agent_state = encode_cat_world_agent_state(agent_state)
        agent_state = append_cat_world_agent_event(
            log,
            cat,
            traits,
            "food-progress",
            "食物补能",
            f"{cat['label']}吃掉一部分{item.get('label') or item_id}，体力 +{delta_energy}，心情 +{delta_mood}，剩余体力 {remaining_energy}。",
            now,
        )
        changed = True
    else:
        agent_state["activeFoodConsumedEnergy"] = next_energy
        agent_state["activeFoodConsumedMood"] = next_mood
    agent_state["activeFoodRemainingEnergy"] = remaining_energy
    agent_state["activeFoodRemainingMood"] = remaining_mood
    agent_state["activeFoodRemainingSeconds"] = remaining_seconds
    if complete:
        log.agent_state = encode_cat_world_agent_state(agent_state)
        agent_state = append_cat_world_agent_event(
            log,
            cat,
            traits,
            "food-finished",
            "食物吃完",
            f"{cat['label']}把{item.get('label') or item_id}吃完了，食物已经从房间里消失。",
            now,
        )
        agent_state["activeFoodRemainingEnergy"] = 0
        agent_state["activeFoodRemainingMood"] = 0
        agent_state["activeFoodRemainingSeconds"] = 0
        state.active_food_item = None
        state.active_food_cat_id = None
        state.active_food_at = None
        changed = True
    log.agent_state = encode_cat_world_agent_state(agent_state)
    db.add(log)
    db.add(state)
    if changed:
        db.commit()
        db.refresh(state)
    return {
        "active": not bool(complete),
        "changed": changed,
        "catId": cat["id"],
        "catLabel": cat["label"],
        "moodGain": delta_mood,
        "energyGain": delta_energy,
        "totalMoodGain": total_mood,
        "totalEnergyGain": total_energy,
        "remainingMood": remaining_mood,
        "remainingEnergy": remaining_energy,
        "remainingSeconds": remaining_seconds,
        "finished": bool(complete),
        "favoriteMatch": favorite_match,
    }


def cat_world_apply_active_food_nibble(
    db: Session,
    state: CatWorldState,
    cat_id: str,
    inventory: dict[str, int],
    room_layout: dict[str, dict[str, float]],
    now: datetime | None = None,
) -> dict[str, Any]:
    item_id = str(state.active_food_item or "").strip()
    item = CAT_WORLD_SHOP_BY_ID.get(item_id)
    if not item or item.get("category") != "food" or not state.active_food_at:
        return {"active": False, "recorded": False, "message": "房间里没有正在吃的食物。"}
    now = now or datetime.utcnow()
    target_cat = cat_world_cat_for_reference(db, state, str(state.active_food_cat_id or ""))
    if not target_cat:
        state.active_food_cat_id = cat_world_effect_target_cat_id(db, state, inventory, room_layout, "food", item_id)
        target_cat = cat_world_cat_for_reference(db, state, state.active_food_cat_id)
    target_cat_id = str(state.active_food_cat_id or "")
    target_cat = target_cat or cat_world_cat_payload(CAT_WORLD_CAT_BY_ID[CAT_WORLD_DEFAULT_CAT_ID])
    breed_id = str(target_cat.get("breedId") or target_cat.get("id"))
    if cat_id and cat_id != target_cat_id:
        return {
            "active": True,
            "recorded": False,
            "catId": target_cat["id"],
            "catLabel": target_cat["label"],
            "itemId": item_id,
            "itemLabel": item.get("label") or item_id,
            "message": f"这份{item.get('label') or item_id}优先留给体力最低的{target_cat['label']}。",
        }

    time_progress = cat_world_apply_active_food_progress(db, state, inventory, room_layout, now=now)
    if time_progress.get("finished") or not state.active_food_item:
        return {"recorded": False, **time_progress}

    cat = target_cat
    traits = cat_world_cat_traits(cat)
    favorite_active_ids = cat_world_active_favorite_decor_ids(breed_id, inventory, room_layout)
    log = get_or_create_cat_world_daily_log(db, state.phone, target_cat_id, date.today(), now, cat)
    apply_cat_world_hourly_decay(
        log,
        traits,
        inventory,
        len(favorite_active_ids),
        now,
        int(state.litter_count or 0),
        cat_world_cat_bath_mood_penalty(state, target_cat_id, now, cat),
        cat,
    )
    agent_state, _ = ensure_cat_world_agent_state(log, cat, traits)
    token = cat_world_active_food_token(state, item_id, cat["id"])
    if agent_state.get("activeFoodToken") != token:
        agent_state["activeFoodToken"] = token
        agent_state["activeFoodConsumedEnergy"] = int(time_progress.get("totalEnergy") or 0) - int(time_progress.get("remainingEnergy") or 0)
        agent_state["activeFoodConsumedMood"] = int(time_progress.get("totalMood") or 0) - int(time_progress.get("remainingMood") or 0)
        agent_state["activeFoodLabel"] = item.get("label") or item_id
        agent_state["activeFoodStartedAt"] = state.active_food_at.replace(microsecond=0).isoformat() + "Z"

    last_nibble_raw = str(agent_state.get("activeFoodNibbleAt") or "")
    try:
        last_nibble_at = datetime.fromisoformat(last_nibble_raw.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        last_nibble_at = None
    if last_nibble_at and now - last_nibble_at < timedelta(seconds=45):
        return {
            "recorded": False,
            "cooldown": True,
            "catId": cat["id"],
            "catLabel": cat["label"],
            "itemId": item_id,
            "itemLabel": item.get("label") or item_id,
            "message": f"{cat['label']}刚刚吃过一口，正在慢慢咽下去。",
            **time_progress,
        }

    previous_energy = max(int(agent_state.get("activeFoodConsumedEnergy") or 0), 0)
    previous_mood = max(int(agent_state.get("activeFoodConsumedMood") or 0), 0)
    remaining_energy = max(int(agent_state.get("activeFoodRemainingEnergy") or time_progress.get("remainingEnergy") or 0), 0)
    remaining_mood = max(int(agent_state.get("activeFoodRemainingMood") or time_progress.get("remainingMood") or 0), 0)
    total_energy = max(int(time_progress.get("totalEnergy") or 0), previous_energy + remaining_energy)
    total_mood = max(int(time_progress.get("totalMood") or 0), previous_mood + remaining_mood)
    if remaining_energy <= 0 and remaining_mood <= 0:
        state.active_food_item = None
        state.active_food_cat_id = None
        state.active_food_at = None
        db.add(state)
        db.commit()
        db.refresh(state)
        return {"active": False, "recorded": False, "finished": True}

    manual_bites = max(int(agent_state.get("activeFoodManualBites") or 0), 0)
    energy_bite = min(remaining_energy, max(1, round(max(total_energy, 1) * 0.14)))
    mood_bite = min(remaining_mood, max(1, round(max(total_mood, 1) * 0.14))) if remaining_mood else 0
    old_energy_score = int(log.energy_score or 0)
    old_mood_score = int(log.mood_score or 0)
    log.energy_score = clamp_cat_world_score(old_energy_score + energy_bite)
    if mood_bite:
        log.mood_score = clamp_cat_world_score(old_mood_score + mood_bite)
    actual_energy_gain = max(int(log.energy_score or 0) - old_energy_score, 0)
    actual_mood_gain = max(int(log.mood_score or 0) - old_mood_score, 0)
    next_consumed_energy = min(total_energy, previous_energy + energy_bite)
    next_consumed_mood = min(total_mood, previous_mood + mood_bite)
    next_remaining_energy = max(total_energy - next_consumed_energy, 0)
    next_remaining_mood = max(total_mood - next_consumed_mood, 0)
    message = (
        f"{cat['label']}主动吃了一口{item.get('label') or item_id}，"
        f"食物减少 {energy_bite}，体力 +{actual_energy_gain}，心情 +{actual_mood_gain}。"
    )
    agent_state = append_cat_world_agent_event(
        log,
        cat,
        traits,
        "food-nibble",
        "主动进食",
        message,
        now,
    )
    agent_state["activeFoodToken"] = token
    agent_state["activeFoodConsumedEnergy"] = next_consumed_energy
    agent_state["activeFoodConsumedMood"] = next_consumed_mood
    agent_state["activeFoodRemainingEnergy"] = next_remaining_energy
    agent_state["activeFoodRemainingMood"] = next_remaining_mood
    agent_state["activeFoodRemainingSeconds"] = int(time_progress.get("remainingSeconds") or 0)
    agent_state["activeFoodManualBites"] = manual_bites + 1
    agent_state["activeFoodNibbleAt"] = now.replace(microsecond=0).isoformat() + "Z"
    bond_gain = 2 if cat_world_item_favorite_cat_id(item_id) == breed_id else 1
    bond = cat_world_apply_cat_bond(state, target_cat_id, bond_gain, "food-nibble", item.get("label") or item_id, now)
    finished = next_remaining_energy <= 0
    if finished:
        log.agent_state = encode_cat_world_agent_state(agent_state)
        agent_state = append_cat_world_agent_event(
            log,
            cat,
            traits,
            "food-finished",
            "食物吃完",
            f"{cat['label']}把{item.get('label') or item_id}吃完了，食物已经从房间里消失。",
            now,
        )
        agent_state["activeFoodRemainingEnergy"] = 0
        agent_state["activeFoodRemainingMood"] = 0
        agent_state["activeFoodRemainingSeconds"] = 0
        state.active_food_item = None
        state.active_food_cat_id = None
        state.active_food_at = None
    log.agent_state = encode_cat_world_agent_state(agent_state)
    db.add(log)
    db.add(state)
    db.commit()
    db.refresh(state)
    return {
        "active": not finished,
        "recorded": True,
        "finished": finished,
        "catId": cat["id"],
        "catLabel": cat["label"],
        "itemId": item_id,
        "itemLabel": item.get("label") or item_id,
        "energyGain": actual_energy_gain,
        "moodGain": actual_mood_gain,
        "foodEnergyConsumed": energy_bite,
        "remainingEnergy": next_remaining_energy,
        "remainingMood": next_remaining_mood,
        "remainingSeconds": int(time_progress.get("remainingSeconds") or 0),
        "manualBites": manual_bites + 1,
        "bond": bond,
        "message": message,
    }


def cat_world_apply_daily_effect(
    db: Session,
    state: CatWorldState,
    item: dict[str, Any],
    inventory: dict[str, int],
    room_layout: dict[str, dict[str, float]],
    effect_type: str,
) -> dict[str, Any]:
    cat_id = cat_world_effect_target_cat_id(db, state, inventory, room_layout, effect_type, item.get("id") or "")
    cat = cat_world_cat_for_reference(db, state, cat_id) or cat_world_cat_payload(
        CAT_WORLD_CAT_BY_ID[CAT_WORLD_DEFAULT_CAT_ID]
    )
    breed_id = str(cat.get("breedId") or cat.get("id"))
    traits = cat_world_cat_traits(cat)
    now = datetime.utcnow()
    favorite_active_ids = cat_world_active_favorite_decor_ids(breed_id, inventory, room_layout)
    log = get_or_create_cat_world_daily_log(db, state.phone, cat_id, date.today(), now, cat)
    apply_cat_world_hourly_decay(
        log,
        traits,
        inventory,
        len(favorite_active_ids),
        now,
        int(state.litter_count or 0),
        cat_world_cat_bath_mood_penalty(state, cat_id, now, cat),
        cat,
    )
    if effect_type == "food":
        state.active_food_cat_id = cat_id
        if not state.active_food_at:
            state.active_food_at = now
        state.active_food_item = item["id"]
        log.food_count = int(log.food_count or 0) + 1
        log.last_food_item = item["id"]
        append_cat_world_agent_event(
            log,
            cat,
            traits,
            "food",
            "摆入食物",
            f"{item.get('label') or item['id']}摆进房间，优先给体力低的{cat['label']}慢慢吃。",
            now,
        )
        cat_world_apply_cat_bond(
            state,
            cat["id"],
            4 if cat_world_item_favorite_cat_id(item["id"]) == breed_id else 3,
            "food",
            item.get("label") or item["id"],
            now,
        )
        db.add(log)
        db.add(state)
        db.flush()
        return cat_world_apply_active_food_progress(
            db,
            state,
            inventory,
            room_layout,
            now=now,
            force_initial=True,
        )
    favorite_match = cat_world_item_favorite_cat_id(item["id"]) == breed_id
    mood_gain = round(int(item.get("mood") or 0) * float(traits["playMoodGain"])) + (4 if favorite_match else 0)
    energy_gain = -max(1, round(4 * float(traits["energyDrain"])))
    log.toy_count = int(log.toy_count or 0) + 1
    log.last_play_item = item["id"]
    bond = cat_world_apply_cat_bond(
        state,
        cat["id"],
        6 if favorite_match else 4,
        "toy",
        item.get("label") or item["id"],
        now,
    )
    append_cat_world_agent_event(
        log,
        cat,
        traits,
        "play",
        "玩具互动",
        f"{cat['label']}玩了{'最喜欢的' if favorite_match else ''}{item.get('label') or item['id']}，心情 +{mood_gain}，体力 {energy_gain}。",
        now,
    )
    log.mood_score = clamp_cat_world_score(int(log.mood_score or 0) + mood_gain)
    log.energy_score = clamp_cat_world_score(int(log.energy_score or 0) + energy_gain)
    db.add(log)
    return {
        "moodGain": mood_gain,
        "energyGain": energy_gain,
        "catId": cat["id"],
        "catLabel": cat["label"],
        "favoriteMatch": favorite_match,
        "bond": bond,
    }


def cat_world_apply_pet_effect(
    db: Session,
    state: CatWorldState,
    cat_id: str,
    inventory: dict[str, int],
    room_layout: dict[str, dict[str, float]],
) -> dict[str, Any]:
    cat = cat_world_cat_for_reference(db, state, cat_id) or cat_world_cat_payload(
        CAT_WORLD_CAT_BY_ID[CAT_WORLD_DEFAULT_CAT_ID]
    )
    cat_id = str(cat.get("profileId") or cat.get("id"))
    breed_id = str(cat.get("breedId") or cat.get("id"))
    traits = cat_world_cat_traits(cat)
    now = datetime.utcnow()
    favorite_active_ids = cat_world_active_favorite_decor_ids(breed_id, inventory, room_layout)
    log = db.scalar(
        select(CatWorldDailyLog)
        .where(
            CatWorldDailyLog.phone == normalize_login_phone(state.phone),
            CatWorldDailyLog.log_date == date.today(),
            CatWorldDailyLog.cat_id == cat_id,
        )
        .with_for_update()
    )
    if log is None:
        log = get_or_create_cat_world_daily_log(db, state.phone, cat_id, date.today(), now, cat)
    apply_cat_world_hourly_decay(
        log,
        traits,
        inventory,
        len(favorite_active_ids),
        now,
        int(state.litter_count or 0),
        cat_world_cat_bath_mood_penalty(state, cat_id, now, cat),
        cat,
    )
    agent_state, _ = ensure_cat_world_agent_state(log, cat, traits)
    pet_count = min(int(agent_state.get("petCount") or 0) + 1, 999)
    cooldown = cat_world_pet_reward_cooldown(
        cat_world_latest_pet_at(db, state.phone, cat_id, agent_state),
        now,
    )
    if cooldown["active"]:
        remaining_minutes = max(math.ceil(int(cooldown["remainingSeconds"]) / 60), 1)
        agent_state["petCount"] = pet_count
        log.agent_state = encode_cat_world_agent_state(agent_state)
        db.add(log)
        current_bond = cat_world_bond_payload(parse_cat_world_bonds(state.cat_bonds), [cat_id])[cat_id]
        return {
            "catId": cat["id"],
            "catLabel": cat["label"],
            "moodGain": 0,
            "bondGain": 0,
            "petCount": pet_count,
            "bond": current_bond,
            "rewarded": False,
            "cooldown": True,
            "remainingSeconds": int(cooldown["remainingSeconds"]),
            "message": (
                f"{cat['label']}还在享受刚才的摸摸；这次不重复增加心情和亲密度，"
                f"约 {remaining_minutes} 分钟后再撸会重新获得加成。"
            ),
        }
    temperament = str(traits.get("temperament") or "balanced")
    mood_gain = {
        "clingy": 4,
        "gentle": 3,
        "chatty": 3,
        "calm": 2,
        "guardian": 2,
    }.get(temperament, 2)
    if agent_state.get("dailyMoodKey") in {"quiet", "grumpy"}:
        mood_gain = max(1, mood_gain - 1)
    log.mood_score = clamp_cat_world_score(int(log.mood_score or 0) + mood_gain)
    if agent_state.get("dailyMoodKey") == "grumpy":
        message = f"{cat['label']}今天不太高兴，但还是接受了摸摸，心情 +{mood_gain}。"
    elif temperament == "chatty":
        message = f"{cat['label']}被摸摸后开始喵喵汇报学习进度，心情 +{mood_gain}。"
    elif temperament == "guardian":
        message = f"{cat['label']}巡视回来蹭了蹭你，心情 +{mood_gain}。"
    else:
        message = f"{cat['label']}收到摸摸，心情 +{mood_gain}。"
    agent_state = append_cat_world_agent_event(
        log,
        cat,
        traits,
        "pet",
        "摸摸互动",
        message,
        now,
    )
    agent_state["petCount"] = pet_count
    agent_state["lastPetAt"] = now.replace(microsecond=0).isoformat() + "Z"
    bond = cat_world_apply_cat_bond(
        state,
        cat_id,
        5 if temperament == "clingy" else 4,
        "pet",
        "摸摸",
        now,
    )
    log.agent_state = encode_cat_world_agent_state(agent_state)
    db.add(log)
    return {
        "catId": cat["id"],
        "catLabel": cat["label"],
        "moodGain": mood_gain,
        "bondGain": int(bond.get("lastGain") or 0),
        "petCount": pet_count,
        "bond": bond,
        "rewarded": True,
        "cooldown": False,
        "remainingSeconds": CAT_WORLD_PET_REWARD_COOLDOWN_SECONDS,
        "message": message,
    }


def cat_world_effect_target_cat_id(
    db: Session,
    state: CatWorldState,
    inventory: dict[str, int],
    room_layout: dict[str, dict[str, float]],
    effect_type: str,
    item_id: str = "",
) -> str:
    profiles = cat_world_active_cat_profiles(db, state.phone)
    selected_profile = cat_world_profile_for_reference(
        db,
        state,
        state.selected_cat_profile or state.selected_cat,
        profiles,
    )
    selected_cat_id = selected_profile.profile_id if selected_profile else ""
    if effect_type != "food":
        return selected_cat_id
    now = datetime.utcnow()
    target_rows: list[tuple[int, int, int, str]] = []
    for profile in profiles:
        cat_id = profile.profile_id
        breed_id = profile.breed_id
        cat = cat_world_cat_profile_payload(profile)
        traits = cat_world_cat_traits(cat)
        favorite_active_ids = cat_world_active_favorite_decor_ids(breed_id, inventory, room_layout)
        log = get_or_create_cat_world_daily_log(db, state.phone, cat_id, date.today(), now, cat)
        apply_cat_world_hourly_decay(
            log,
            traits,
            inventory,
            len(favorite_active_ids),
            now,
            int(state.litter_count or 0),
            cat_world_cat_bath_mood_penalty(state, cat_id, now, cat),
            cat,
        )
        agent_state, _ = ensure_cat_world_agent_state(log, cat, traits)
        db.add(log)
        energy_score = clamp_cat_world_score(int(log.energy_score or 0) + int(agent_state.get("energyOffset") or 0))
        favorite_rank = 0 if item_id and cat_world_item_favorite_cat_id(item_id) == breed_id else 1
        target_rows.append((energy_score, favorite_rank, len(target_rows), cat_id))
    if not target_rows:
        return selected_cat_id
    lowest_energy = min(row[0] for row in target_rows)
    hungry_rows = [row for row in target_rows if row[0] <= lowest_energy + 6]
    return sorted(hungry_rows, key=lambda row: (row[1], row[0], row[2]))[0][3]


def get_or_create_cat_world_state(db: Session, phone: str) -> CatWorldState:
    normalized = normalize_login_phone(phone)
    state = db.scalar(select(CatWorldState).where(CatWorldState.phone == normalized))
    if state:
        scene = cat_world_scene_row(db, state.current_scene_key, enabled_only=True)
        if not scene:
            scene = cat_world_scene_row(db, CAT_WORLD_DEFAULT_SCENE_KEY, enabled_only=True)
        if not scene:
            raise HTTPException(status_code=500, detail="猫咪世界还没有可用场景配置。")
        changed = False
        drawn_limited_cats = [
            cat_id
            for cat_id in db.scalars(
                select(CatWorldBlindBoxDraw.cat_id).where(CatWorldBlindBoxDraw.phone == normalized)
            ).all()
            if cat_id in CAT_WORLD_CAT_BY_ID
        ]
        owned_cats = parse_cat_world_cats(state.cats)
        restored_cats = list(dict.fromkeys([*owned_cats, *drawn_limited_cats]))
        if restored_cats != owned_cats:
            state.cats = encode_cat_world_cats(restored_cats)
            db.add(state)
            changed = True
        _, profiles_changed = ensure_cat_world_cat_profiles(db, state, restored_cats)
        changed = changed or profiles_changed
        if state.current_scene_key != scene.scene_key:
            state.current_scene_key = scene.scene_key
            db.add(state)
            changed = True
        _, created = get_or_create_cat_world_user_scene(db, state, scene)
        if created or changed:
            db.commit()
            db.refresh(state)
        return state
    drawn_limited_cats = [
        cat_id
        for cat_id in db.scalars(
            select(CatWorldBlindBoxDraw.cat_id).where(CatWorldBlindBoxDraw.phone == normalized)
        ).all()
        if cat_id in CAT_WORLD_CAT_BY_ID
    ]
    initial_cats = list(dict.fromkeys([CAT_WORLD_DEFAULT_CAT_ID, *drawn_limited_cats]))
    state = CatWorldState(
        phone=normalized,
        energy_spent=0,
        inventory=encode_cat_world_inventory({}),
        cats=encode_cat_world_cats(initial_cats),
        room_styles=encode_cat_world_room_styles({}),
        room_layout=encode_cat_world_room_layout({}),
        current_scene_key=CAT_WORLD_DEFAULT_SCENE_KEY,
        cat_bonds=encode_cat_world_bonds({}),
        cat_care=encode_cat_world_care({}),
        selected_cat=drawn_limited_cats[-1] if drawn_limited_cats else CAT_WORLD_DEFAULT_CAT_ID,
    )
    db.add(state)
    db.commit()
    db.refresh(state)
    _, profiles_changed = ensure_cat_world_cat_profiles(db, state, initial_cats)
    if profiles_changed:
        db.commit()
        db.refresh(state)
    scene = cat_world_scene_row(db, CAT_WORLD_DEFAULT_SCENE_KEY, enabled_only=True)
    if scene:
        get_or_create_cat_world_user_scene(db, state, scene)
        db.commit()
    return state


def cat_world_active_food(db: Session, state: CatWorldState) -> dict[str, Any]:
    item_id = str(state.active_food_item or "").strip()
    item = CAT_WORLD_SHOP_BY_ID.get(item_id)
    if not item or item.get("category") != "food" or not state.active_food_at:
        return {"active": False, "itemId": "", "label": "", "remainingSeconds": 0, "durationSeconds": 0}
    duration_seconds = max(int(item.get("durationMinutes") or 30), 1) * 60
    elapsed_seconds = max(int((datetime.utcnow() - state.active_food_at).total_seconds()), 0)
    remaining_seconds = max(duration_seconds - elapsed_seconds, 0)
    if remaining_seconds <= 0:
        return {"active": False, "itemId": "", "label": "", "remainingSeconds": 0, "durationSeconds": duration_seconds}
    target_cat = cat_world_cat_for_reference(db, state, str(state.active_food_cat_id or ""))
    traits = cat_world_cat_traits(target_cat or CAT_WORLD_CAT_BY_ID[CAT_WORLD_DEFAULT_CAT_ID])
    target_cat_id = str(target_cat.get("profileId") or target_cat.get("id")) if target_cat else ""
    target_breed_id = str(target_cat.get("breedId") or target_cat.get("id")) if target_cat else ""
    favorite_multiplier = cat_world_food_favorite_multiplier(item, target_breed_id)
    total_energy = round(int(item.get("catEnergy") or 0) * float(traits["foodEnergyGain"]) * favorite_multiplier)
    total_mood = round(int(item.get("mood") or 0) * float(traits["foodEnergyGain"]) * favorite_multiplier)
    remaining_energy = max(int((total_energy * remaining_seconds + duration_seconds - 1) // duration_seconds), 0)
    if remaining_energy <= 0:
        return {"active": False, "itemId": "", "label": "", "remainingSeconds": 0, "durationSeconds": duration_seconds}
    expires_at = state.active_food_at + timedelta(seconds=duration_seconds)
    return {
        "active": True,
        "itemId": item_id,
        "label": item["label"],
        "englishName": item.get("englishName") or "",
        "targetCatId": target_cat["id"] if target_cat else "",
        "targetCatLabel": target_cat["label"] if target_cat else "",
        "mood": total_mood,
        "catEnergy": total_energy,
        "remainingEnergy": remaining_energy,
        "favoriteMatch": bool(favorite_multiplier > 1),
        "consumeCount": 1,
        "remainingSeconds": remaining_seconds,
        "durationSeconds": duration_seconds,
        "expiresAt": expires_at.replace(microsecond=0).isoformat() + "Z",
    }


def cat_world_mood(
    db: Session,
    state: CatWorldState,
    inventory: dict[str, int],
    owned_cats: list[str],
    available_energy: int,
    room_layout: dict[str, dict[str, float]] | None = None,
    daily_logs: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not owned_cats:
        return {
            "score": 0,
            "label": "房间里没有猫咪",
            "catEnergy": 0,
            "catEnergyLabel": "等待重新领养",
            "canWalk": False,
            "activeFood": {"active": False, "itemId": "", "remainingSeconds": 0},
            "dailyLog": {},
            "favoriteDecorIds": [],
            "favoriteActiveDecorIds": [],
            "favoriteDecorBonus": 0,
            "recentPlay": False,
            "lastPlayItem": state.last_play_item or "",
            "lastPlayedAt": state.last_played_at.isoformat() if state.last_played_at else "",
            "selectedCatId": "",
            "traits": cat_world_cat_traits(None),
            "movementCost": 0,
            "energyCost": 0,
            "emptyRoom": True,
        }
    selected_cat = cat_world_cat_for_reference(
        db,
        state,
        state.selected_cat_profile or state.selected_cat,
    ) or cat_world_cat_payload(CAT_WORLD_CAT_BY_ID[CAT_WORLD_DEFAULT_CAT_ID])
    selected_cat_id = str(selected_cat.get("profileId") or selected_cat.get("id"))
    selected_breed_id = str(selected_cat.get("breedId") or selected_cat.get("id"))
    traits = cat_world_cat_traits(selected_cat)
    active_food = cat_world_active_food(db, state)
    daily_logs = daily_logs or {}
    if active_food.get("active"):
        target_cat_id = str(active_food.get("targetCatId") or state.active_food_cat_id or "")
        target_daily_log = daily_logs.get(target_cat_id) or {}
        agent_state = target_daily_log.get("agentState") if isinstance(target_daily_log, dict) else {}
        if isinstance(agent_state, dict):
            token = cat_world_active_food_token(state, str(active_food.get("itemId") or ""), target_cat_id)
            if agent_state.get("activeFoodToken") == token:
                consumed_energy = max(int(agent_state.get("activeFoodConsumedEnergy") or 0), 0)
                consumed_mood = max(int(agent_state.get("activeFoodConsumedMood") or 0), 0)
                remaining_energy = max(int(agent_state.get("activeFoodRemainingEnergy") or 0), 0)
                remaining_mood = max(int(agent_state.get("activeFoodRemainingMood") or 0), 0)
                active_remaining_seconds = max(int(active_food.get("remainingSeconds") or 0), 0)
                logged_remaining_seconds = max(int(agent_state.get("activeFoodRemainingSeconds") or 0), 0)
                remaining_seconds = (
                    min(active_remaining_seconds, logged_remaining_seconds)
                    if logged_remaining_seconds
                    else active_remaining_seconds
                )
                if remaining_energy <= 0:
                    active_food = {
                        "active": False,
                        "itemId": "",
                        "label": "",
                        "remainingSeconds": 0,
                        "durationSeconds": int(active_food.get("durationSeconds") or 0),
                    }
                else:
                    active_food = {
                        **active_food,
                        "catEnergy": max(int(active_food.get("catEnergy") or 0), consumed_energy + remaining_energy),
                        "mood": max(int(active_food.get("mood") or 0), consumed_mood + remaining_mood),
                        "remainingEnergy": remaining_energy,
                        "remainingMood": remaining_mood,
                        "remainingSeconds": min(int(active_food.get("remainingSeconds") or remaining_seconds), remaining_seconds),
                    }
    daily_log = daily_logs.get(selected_cat_id) or daily_logs.get(selected_breed_id) or {}
    favorite_active_ids = daily_log.get("favoriteActiveDecorIds") or cat_world_active_favorite_decor_ids(
        selected_breed_id,
        inventory,
        room_layout or {},
    )
    food_bonus = int(active_food.get("mood") or 0) if active_food.get("active") else 0
    food_energy_bonus = int(active_food.get("catEnergy") or 0) if active_food.get("active") else 0
    if active_food.get("active"):
        active_food = {
            **active_food,
            "moodEffective": food_bonus,
            "catEnergyEffective": food_energy_bonus,
        }
    toy_bonus = min(
        18,
        sum(
            int(CAT_WORLD_SHOP_BY_ID[item_id].get("mood") or 0)
            for item_id, count in inventory.items()
            if CAT_WORLD_SHOP_BY_ID[item_id]["category"] == "toy" and count > 0
        ),
    )
    decor_bonus = min(
        16,
        sum(
            int(CAT_WORLD_SHOP_BY_ID[item_id].get("mood") or 0)
            for item_id, count in inventory.items()
            if CAT_WORLD_SHOP_BY_ID[item_id]["category"] == "decor" and count > 0
        ),
    )
    cat_bonus = min(max(len(owned_cats) - 1, 0) * 3, 12)
    energy_bonus = min(max(available_energy, 0) // 250, 8)
    recent_play = bool(state.last_played_at and datetime.utcnow() - state.last_played_at <= timedelta(hours=24))
    play_bonus = round(12 * float(traits["playMoodGain"])) if recent_play else 0
    movement_cost = round(6 * float(traits["movement"]) * float(traits["moodDrain"]))
    energy_cost = round(12 * float(traits["movement"]) * float(traits["energyDrain"]))
    favorite_bonus = min(len(favorite_active_ids) * 8, 16)
    if daily_log:
        score = clamp_cat_world_score(
            int(daily_log.get("moodScore") or 0) + favorite_bonus + min(toy_bonus, 8) + min(decor_bonus, 8) + cat_bonus,
            18,
            100,
        )
        cat_energy = clamp_cat_world_score(
            int(daily_log.get("energyScore") or 0) + min(max(available_energy, 0) // 360, 14),
            5,
            100,
        )
    else:
        score = max(
            28,
            min(100, 52 + food_bonus + toy_bonus + decor_bonus + cat_bonus + energy_bonus + play_bonus - movement_cost),
        )
        cat_energy = max(
            5,
            min(
                100,
                28 + min(max(available_energy, 0) // 160, 36) + food_energy_bonus + (8 if recent_play else 0) - energy_cost,
            ),
        )
    if score >= 88:
        label = "开心到打呼噜"
    elif score >= 72:
        label = "心情很好"
    elif score >= 56:
        label = "安静陪读"
    else:
        label = "想要你陪她玩"
    return {
        "score": score,
        "label": label,
        "catEnergy": cat_energy,
        "catEnergyLabel": "体力充足" if cat_energy >= 58 else ("原地休息" if cat_energy < traits["restThreshold"] else "慢慢走动"),
        "canWalk": cat_energy >= traits["restThreshold"],
        "activeFood": active_food,
        "dailyLog": daily_log,
        "favoriteDecorIds": cat_world_cat_favorite_decor_ids(selected_breed_id),
        "favoriteActiveDecorIds": favorite_active_ids,
        "favoriteDecorBonus": favorite_bonus,
        "recentPlay": recent_play,
        "lastPlayItem": state.last_play_item or "",
        "lastPlayedAt": state.last_played_at.isoformat() if state.last_played_at else "",
        "selectedCatId": selected_cat_id,
        "traits": traits,
        "movementCost": movement_cost,
        "energyCost": energy_cost,
    }


def serialize_cat_world_payload(db: Session, state: CatWorldState) -> dict[str, Any]:
    growth = learning_growth_summary(db)
    missions = {item["key"]: item for item in growth.get("dailyMissions", []) if isinstance(item, dict)}
    spelling_count = int(missions.get("today_spelling", {}).get("value") or 0)
    play_time_reward_source = cat_world_play_time_reward_source(db, state.phone)
    play_time_day_changed = normalize_cat_world_play_time_day(state, date.today())
    if play_time_day_changed:
        db.add(state)
        db.commit()
        db.refresh(state)
    play_time = cat_world_play_time_payload(
        state,
        spelling_count,
        reward_seconds=int(play_time_reward_source["seconds"]),
    )
    essay_energy_source = cat_world_essay_energy_source(db, state.phone)
    operating_energy_source = cat_world_operating_energy_source(db, state.phone)
    earned_energy = (
        max(int(growth.get("points") or 0), 0)
        + int(essay_energy_source["energy"])
        + int(operating_energy_source["energy"])
    )
    today_energy = cat_world_today_energy(growth) + int(operating_energy_source["todayEnergy"])
    spent_energy = max(int(state.energy_spent or 0), 0)
    available_energy = max(earned_energy - spent_energy, 0)
    inventory = parse_cat_world_inventory(state.inventory)
    damaged_items = parse_cat_world_damaged_items(state.damaged_items)
    shop = cat_world_effective_shop(db)
    shop_by_id = {item["id"]: item for item in shop}
    owned_cats = parse_cat_world_cats(state.cats)
    cat_profiles, cat_profiles_changed = ensure_cat_world_cat_profiles(db, state, owned_cats)
    if cat_profiles_changed:
        db.commit()
        db.refresh(state)
    cat_bonds = parse_cat_world_bonds(state.cat_bonds)
    blind_box_catalog = cat_world_blind_box_catalog_payload(db, state, owned_cats)
    collection_catalog = cat_world_collection_catalog_payload(blind_box_catalog, owned_cats)
    current_blind_series = next(
        (
            series
            for series in blind_box_catalog["series"]
            if series["key"] == blind_box_catalog["currentSeriesKey"]
        ),
        {},
    )
    blind_box_item = shop_by_id.get("limited-cat-blind-box")
    if blind_box_item is not None:
        blind_box_item.update(
            {
                "seriesKey": current_blind_series.get("key") or CAT_WORLD_CURRENT_BLIND_BOX_SERIES_KEY,
                "seriesLabel": current_blind_series.get("label") or "限定猫咪盲盒",
                "region": current_blind_series.get("region") or "",
                "issue": current_blind_series.get("issue") or "",
                "remainingStock": int(current_blind_series.get("remainingStock") or 0),
                "drawn": bool(current_blind_series.get("drawn")),
                "drawnCatId": current_blind_series.get("drawnCatId") or "",
            }
        )
    cat_care, cat_care_changed = cat_world_ensure_profile_care_records(state, cat_profiles)
    litter_status = cat_world_refresh_litter(state, inventory, owned_cats)
    active_care = cat_world_active_care_payload(db, state)
    if cat_care_changed or litter_status.get("changed") or active_care.get("changed"):
        db.add(state)
        db.commit()
        db.refresh(state)
        inventory = parse_cat_world_inventory(state.inventory)
        cat_care = parse_cat_world_care(state.cat_care)
        litter_status = {
            **cat_world_refresh_litter(state, inventory, owned_cats),
            "autoUsed": int(litter_status.get("autoUsed") or 0),
            "addedCount": int(litter_status.get("addedCount") or 0),
            "changed": False,
        }
        active_care = cat_world_active_care_payload(db, state)
    damaged_items, damaged_changed = cat_world_apply_agent_damage_events(
        db,
        state,
        inventory,
        owned_cats,
        damaged_items,
        shop_by_id,
    )
    if damaged_changed:
        state.damaged_items = encode_cat_world_damaged_items(damaged_items)
        db.add(state)
        db.commit()
        db.refresh(state)
        inventory = parse_cat_world_inventory(state.inventory)
        damaged_items = parse_cat_world_damaged_items(state.damaged_items)
    usable_inventory = cat_world_usable_inventory(inventory, damaged_items)
    _, active_user_scene, active_scene = cat_world_active_scene_context(db, state)
    room_styles = parse_cat_world_room_styles(active_user_scene.room_styles, inventory)
    room_layout = parse_cat_world_room_layout(
        active_user_scene.layout,
        usable_inventory,
        active_scene.get("defaultLayout"),
        active_scene.get("itemRules"),
    )
    visual_room_layout = parse_cat_world_room_layout(
        active_user_scene.layout,
        inventory,
        active_scene.get("defaultLayout"),
        active_scene.get("itemRules"),
    )
    active_food_effect = cat_world_apply_active_food_progress(db, state, usable_inventory, room_layout)
    if active_food_effect.get("changed"):
        db.refresh(state)
        inventory = parse_cat_world_inventory(state.inventory)
        damaged_items = parse_cat_world_damaged_items(state.damaged_items)
        cat_bonds = parse_cat_world_bonds(state.cat_bonds)
        usable_inventory = cat_world_usable_inventory(inventory, damaged_items)
        _, active_user_scene, active_scene = cat_world_active_scene_context(db, state)
        room_styles = parse_cat_world_room_styles(active_user_scene.room_styles, inventory)
        room_layout = parse_cat_world_room_layout(
            active_user_scene.layout,
            usable_inventory,
            active_scene.get("defaultLayout"),
            active_scene.get("itemRules"),
        )
        visual_room_layout = parse_cat_world_room_layout(
            active_user_scene.layout,
            inventory,
            active_scene.get("defaultLayout"),
            active_scene.get("itemRules"),
        )
    if state.selected_cat not in owned_cats:
        state.selected_cat = owned_cats[0] if owned_cats else ""
        db.add(state)
        db.commit()
        db.refresh(state)
    daily_logs = cat_world_apply_daily_decay(db, state, usable_inventory, cat_profiles, room_layout)
    owned_cats = parse_cat_world_cats(state.cats)
    cat_profiles = cat_world_active_cat_profiles(db, state.phone)
    cat_bonds = parse_cat_world_bonds(state.cat_bonds)
    cat_care = parse_cat_world_care(state.cat_care)
    lost_cats = cat_world_lost_cats_payload(db, state.phone, cat_care, owned_cats)
    style_options = {
        decor_id: cat_world_owned_style_options(inventory, decor_id)
        for decor_id, count in inventory.items()
        if count > 0 and CAT_WORLD_SHOP_BY_ID.get(decor_id, {}).get("category") == "decor"
    }
    return {
        "playTime": play_time,
        "energy": {
            "earned": earned_energy,
            "spent": spent_energy,
            "available": available_energy,
            "today": today_energy,
            "sources": [
                *cat_world_growth_source_rows(growth),
                essay_energy_source,
                operating_energy_source,
            ],
        },
        "state": {
            "inventory": inventory,
            "usableInventory": usable_inventory,
            "damagedItems": damaged_items,
            "ownedCats": owned_cats,
            "lostCats": lost_cats,
            "catCare": cat_care,
            "catBonds": cat_world_bond_payload(
                cat_bonds,
                [profile.profile_id for profile in cat_profiles],
            ),
            "roomStyles": room_styles,
            "roomLayout": visual_room_layout,
            "currentSceneId": active_scene["id"],
            "currentScene": active_scene,
            "styleOptions": style_options,
            "selectedCat": state.selected_cat,
            "selectedCatProfile": state.selected_cat_profile or "",
            "hygiene": litter_status,
            "activeCare": active_care,
            "dailyLogs": daily_logs,
            "mood": cat_world_mood(
                db,
                state,
                usable_inventory,
                owned_cats,
                available_energy,
                room_layout,
                daily_logs,
            ),
        },
        "cats": [cat_world_cat_payload(cat) for cat in CAT_WORLD_CATS],
        "catProfiles": [cat_world_cat_profile_payload(profile) for profile in cat_profiles],
        "scenes": cat_world_scene_catalog_payload(db, state),
        "blindBoxCatalog": blind_box_catalog,
        "catCollectionCatalog": collection_catalog,
        "decorFavorites": cat_world_decor_favorite_payload(),
        "shop": shop,
        "pricingPlans": CAT_WORLD_PRICING_PLANS,
        "gameSettings": cat_world_game_settings_payload(db),
    }


def require_cat_world_phone(request: Request) -> str:
    phone = authenticated_phone_from_request(request)
    if not phone:
        raise HTTPException(status_code=401, detail="请先用手机号登录。")
    return phone


def admin_cat_world_scene_pricing_payload(db: Session) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(CatWorldScene).order_by(CatWorldScene.sort_order, CatWorldScene.id)
    ).all()
    payload: list[dict[str, Any]] = []
    for row in rows:
        config = cat_world_scene_config(row)
        if not config.get("purchasable"):
            continue
        seed = CAT_WORLD_SCENE_SEED_BY_KEY.get(row.scene_key, {})
        default_cost = max(int(seed.get("purchaseCost") or 0), 0)
        cost = max(int(config.get("purchaseCost") or 0), 0)
        payload.append(
            {
                "id": row.scene_key,
                "label": row.label,
                "englishName": row.english_name,
                "description": config.get("description") or "",
                "cost": cost,
                "defaultCost": default_cost,
                "hasCustomCost": cost != default_cost,
                "enabled": bool(row.is_enabled),
            }
        )
    return payload


def admin_cat_world_pricing_payload(db: Session) -> dict[str, Any]:
    return {
        "plans": CAT_WORLD_PRICING_PLANS,
        "items": cat_world_effective_shop(db),
        "scenes": admin_cat_world_scene_pricing_payload(db),
        "settings": cat_world_game_settings_payload(db),
    }


def page_context(request: Request, db: Session, extra: dict | None = None) -> dict:
    current_user_phone = authenticated_phone_from_request(request)
    current_admin = get_or_create_admin_user(db, current_user_phone) if current_user_phone else None
    context = {
        "request": request,
        "app_name": settings.app_name,
        "current_user_phone": current_user_phone,
        "current_admin_user": current_admin,
        "daily_quote": get_daily_quote(db),
        "sidebar_challenges": sidebar_challenge_progress(db),
        "wrong_word_count": pending_wrong_word_count(db),
        "learning_growth": learning_growth_summary(db),
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
        "currentUser": admin_user_summary(context.get("current_admin_user"), context.get("current_user_phone")),
        "dailyQuote": {
            "content": daily_quote.content,
            "author": daily_quote.author,
        }
        if daily_quote
        else None,
        "wrongWordCount": context.get("wrong_word_count", 0),
        "learningGrowth": context.get("learning_growth") or default_learning_growth_summary(),
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
            "image_issue",
            "audio_issue",
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
    missing_long_string_columns = [
        column for column in ("english_definition_audio_url", "english_example_audio_url") if column not in word_columns
    ]
    table_names = set(inspector.get_table_names())
    resource_pool_columns = (
        {column["name"] for column in inspector.get_columns("word_resource_pool")}
        if "word_resource_pool" in table_names
        else set()
    )
    wrong_columns = {column["name"] for column in inspector.get_columns("wrong_words")} if "wrong_words" in table_names else set()
    word_list_columns = {column["name"] for column in inspector.get_columns("word_lists")} if "word_lists" in table_names else set()
    challenge_progress_columns = (
        {column["name"] for column in inspector.get_columns("challenge_progress")}
        if "challenge_progress" in table_names
        else set()
    )
    admin_user_columns = (
        {column["name"] for column in inspector.get_columns("admin_user_settings")}
        if "admin_user_settings" in table_names
        else set()
    )
    cat_world_state_columns = (
        {column["name"] for column in inspector.get_columns("cat_world_states")}
        if "cat_world_states" in table_names
        else set()
    )
    cat_world_daily_log_columns = (
        {column["name"] for column in inspector.get_columns("cat_world_daily_logs")}
        if "cat_world_daily_logs" in table_names
        else set()
    )
    cat_world_cat_profile_columns = (
        {column["name"] for column in inspector.get_columns("cat_world_cat_profiles")}
        if "cat_world_cat_profiles" in table_names
        else set()
    )
    essay_entry_columns = (
        {column["name"] for column in inspector.get_columns("essay_entries")}
        if "essay_entries" in table_names
        else set()
    )

    with engine.begin() as connection:
        for column in missing_boolean_columns:
            connection.execute(text(f"ALTER TABLE words ADD COLUMN {column} {boolean_type} NOT NULL DEFAULT 0"))
        for column in missing_text_columns:
            connection.execute(text(f"ALTER TABLE words ADD COLUMN {column} TEXT NULL"))
        for column in missing_string_columns:
            connection.execute(text(f"ALTER TABLE words ADD COLUMN {column} VARCHAR(120) NULL"))
        for column in missing_long_string_columns:
            connection.execute(text(f"ALTER TABLE words ADD COLUMN {column} VARCHAR(1000) NULL"))
        if "word_resource_pool" in table_names:
            if "english_definition_audio_url" not in resource_pool_columns:
                connection.execute(text("ALTER TABLE word_resource_pool ADD COLUMN english_definition_audio_url VARCHAR(1000) NULL"))
            if "english_definition_audio_source" not in resource_pool_columns:
                connection.execute(text("ALTER TABLE word_resource_pool ADD COLUMN english_definition_audio_source VARCHAR(120) NULL"))
            if "english_example_audio_url" not in resource_pool_columns:
                connection.execute(text("ALTER TABLE word_resource_pool ADD COLUMN english_example_audio_url VARCHAR(1000) NULL"))
            if "english_example_audio_source" not in resource_pool_columns:
                connection.execute(text("ALTER TABLE word_resource_pool ADD COLUMN english_example_audio_source VARCHAR(120) NULL"))
        if "word_lists" in table_names and "display_order" not in word_list_columns:
            connection.execute(text("ALTER TABLE word_lists ADD COLUMN display_order INTEGER NOT NULL DEFAULT 0"))
        if "word_lists" in table_names and "sequence_offset" not in word_list_columns:
            connection.execute(text("ALTER TABLE word_lists ADD COLUMN sequence_offset INTEGER NOT NULL DEFAULT 0"))
        if "word_lists" in table_names and "group_id" not in word_list_columns:
            connection.execute(text("ALTER TABLE word_lists ADD COLUMN group_id INTEGER NULL"))
        if "challenge_progress" in table_names and "completed_rounds" not in challenge_progress_columns:
            connection.execute(text("ALTER TABLE challenge_progress ADD COLUMN completed_rounds INTEGER NOT NULL DEFAULT 0"))
        if "admin_user_settings" in table_names and "login_password_hash" not in admin_user_columns:
            connection.execute(text("ALTER TABLE admin_user_settings ADD COLUMN login_password_hash TEXT NULL"))
        if "cat_world_states" in table_names and "room_styles" not in cat_world_state_columns:
            connection.execute(text("ALTER TABLE cat_world_states ADD COLUMN room_styles TEXT NULL"))
        if "cat_world_states" in table_names and "room_layout" not in cat_world_state_columns:
            connection.execute(text("ALTER TABLE cat_world_states ADD COLUMN room_layout TEXT NULL"))
        if "cat_world_states" in table_names and "current_scene_key" not in cat_world_state_columns:
            connection.execute(
                text("ALTER TABLE cat_world_states ADD COLUMN current_scene_key VARCHAR(80) NOT NULL DEFAULT 'main-room'")
            )
        if "cat_world_states" in table_names and "cat_bonds" not in cat_world_state_columns:
            connection.execute(text("ALTER TABLE cat_world_states ADD COLUMN cat_bonds TEXT NULL"))
        if "cat_world_states" in table_names and "cat_care" not in cat_world_state_columns:
            connection.execute(text("ALTER TABLE cat_world_states ADD COLUMN cat_care TEXT NULL"))
        if "cat_world_states" in table_names and "selected_cat_profile" not in cat_world_state_columns:
            connection.execute(text("ALTER TABLE cat_world_states ADD COLUMN selected_cat_profile VARCHAR(80) NULL"))
        if "cat_world_states" in table_names and "active_food_item" not in cat_world_state_columns:
            connection.execute(text("ALTER TABLE cat_world_states ADD COLUMN active_food_item VARCHAR(80) NULL"))
        if "cat_world_states" in table_names and "active_food_cat_id" not in cat_world_state_columns:
            connection.execute(text("ALTER TABLE cat_world_states ADD COLUMN active_food_cat_id VARCHAR(80) NULL"))
        if "cat_world_states" in table_names and "active_food_at" not in cat_world_state_columns:
            connection.execute(text("ALTER TABLE cat_world_states ADD COLUMN active_food_at DATETIME NULL"))
        if "cat_world_states" in table_names and "active_care_item" not in cat_world_state_columns:
            connection.execute(text("ALTER TABLE cat_world_states ADD COLUMN active_care_item VARCHAR(80) NULL"))
        if "cat_world_states" in table_names and "active_care_cat_id" not in cat_world_state_columns:
            connection.execute(text("ALTER TABLE cat_world_states ADD COLUMN active_care_cat_id VARCHAR(80) NULL"))
        if "cat_world_states" in table_names and "active_care_at" not in cat_world_state_columns:
            connection.execute(text("ALTER TABLE cat_world_states ADD COLUMN active_care_at DATETIME NULL"))
        if "cat_world_states" in table_names and "litter_count" not in cat_world_state_columns:
            connection.execute(text("ALTER TABLE cat_world_states ADD COLUMN litter_count INTEGER NOT NULL DEFAULT 0"))
        if "cat_world_states" in table_names and "litter_ready_count" not in cat_world_state_columns:
            connection.execute(text("ALTER TABLE cat_world_states ADD COLUMN litter_ready_count INTEGER NOT NULL DEFAULT 0"))
        if "cat_world_states" in table_names and "litter_updated_at" not in cat_world_state_columns:
            connection.execute(text("ALTER TABLE cat_world_states ADD COLUMN litter_updated_at DATETIME NULL"))
        if "cat_world_states" in table_names and "litter_started_at" not in cat_world_state_columns:
            connection.execute(text("ALTER TABLE cat_world_states ADD COLUMN litter_started_at DATETIME NULL"))
        if "cat_world_states" in table_names and "damaged_items" not in cat_world_state_columns:
            connection.execute(text("ALTER TABLE cat_world_states ADD COLUMN damaged_items TEXT NULL"))
        if "cat_world_states" in table_names and "play_time_date" not in cat_world_state_columns:
            connection.execute(text("ALTER TABLE cat_world_states ADD COLUMN play_time_date DATE NULL"))
        if "cat_world_states" in table_names and "play_time_used_seconds" not in cat_world_state_columns:
            connection.execute(
                text("ALTER TABLE cat_world_states ADD COLUMN play_time_used_seconds INTEGER NOT NULL DEFAULT 0")
            )
        if "cat_world_states" in table_names and "play_time_last_seen_at" not in cat_world_state_columns:
            connection.execute(text("ALTER TABLE cat_world_states ADD COLUMN play_time_last_seen_at DATETIME NULL"))
        if "cat_world_daily_logs" in table_names and "agent_state" not in cat_world_daily_log_columns:
            connection.execute(text("ALTER TABLE cat_world_daily_logs ADD COLUMN agent_state TEXT NULL"))
        if "cat_world_daily_logs" in table_names and "damaged_item_id" not in cat_world_daily_log_columns:
            connection.execute(text("ALTER TABLE cat_world_daily_logs ADD COLUMN damaged_item_id VARCHAR(80) NULL"))
        if "cat_world_cat_profiles" in table_names and "personality_key" not in cat_world_cat_profile_columns:
            connection.execute(text("ALTER TABLE cat_world_cat_profiles ADD COLUMN personality_key VARCHAR(40) NULL"))
        if "cat_world_cat_profiles" in table_names and "personality_label" not in cat_world_cat_profile_columns:
            connection.execute(text("ALTER TABLE cat_world_cat_profiles ADD COLUMN personality_label VARCHAR(120) NULL"))
        if "cat_world_cat_profiles" in table_names and "personality_traits" not in cat_world_cat_profile_columns:
            connection.execute(text("ALTER TABLE cat_world_cat_profiles ADD COLUMN personality_traits TEXT NULL"))
        if "essay_entries" in table_names and "writing_score" not in essay_entry_columns:
            connection.execute(text("ALTER TABLE essay_entries ADD COLUMN writing_score INTEGER NOT NULL DEFAULT 0"))
        if "essay_entries" in table_names and "writing_score_breakdown" not in essay_entry_columns:
            connection.execute(text("ALTER TABLE essay_entries ADD COLUMN writing_score_breakdown TEXT NULL"))
        if "essay_entries" in table_names and "writing_advice" not in essay_entry_columns:
            connection.execute(text("ALTER TABLE essay_entries ADD COLUMN writing_advice TEXT NULL"))
        if "essay_entries" in table_names and "translation_body" not in essay_entry_columns:
            translation_text_type = "LONGTEXT" if dialect == "mysql" else "TEXT"
            connection.execute(
                text(f"ALTER TABLE essay_entries ADD COLUMN translation_body {translation_text_type} NULL")
            )
        if "essay_entries" in table_names and "optimized_translation_body" not in essay_entry_columns:
            translation_text_type = "LONGTEXT" if dialect == "mysql" else "TEXT"
            connection.execute(
                text(
                    "ALTER TABLE essay_entries "
                    f"ADD COLUMN optimized_translation_body {translation_text_type} NULL"
                )
            )
        if "essay_entries" in table_names and "translation_model" not in essay_entry_columns:
            connection.execute(text("ALTER TABLE essay_entries ADD COLUMN translation_model VARCHAR(120) NULL"))
        if "essay_entries" in table_names and "best_writing_score" not in essay_entry_columns:
            connection.execute(text("ALTER TABLE essay_entries ADD COLUMN best_writing_score INTEGER NOT NULL DEFAULT 0"))
        if "essay_entries" in table_names and "best_writing_points" not in essay_entry_columns:
            connection.execute(text("ALTER TABLE essay_entries ADD COLUMN best_writing_points INTEGER NOT NULL DEFAULT 0"))
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


def get_or_create_word_list_group_by_name(db: Session, name: str) -> WordListGroup:
    cleaned_name = clean_list_name(name)
    group = db.scalar(
        select(WordListGroup).where(WordListGroup.name == cleaned_name).order_by(WordListGroup.id.asc()).limit(1)
    )
    if not group:
        group = WordListGroup(name=cleaned_name, display_order=next_word_list_group_display_order(db))
        db.add(group)
        db.commit()
        db.refresh(group)
    return group


def next_word_list_group_display_order(db: Session) -> int:
    current_min = db.scalar(select(func.min(WordListGroup.display_order))) or 0
    return int(current_min) - 10


def get_or_create_word_list(db: Session, word_list_id: str, name: str) -> WordList:
    word_list = db.get(WordList, int(word_list_id)) if word_list_id.isdigit() else None
    if word_list:
        word_list.name = clean_list_name(name)
    else:
        word_list = WordList(name=clean_list_name(name), display_order=next_word_list_display_order(db))
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
        word_list = WordList(name=cleaned_name, display_order=next_word_list_display_order(db))
        db.add(word_list)
        db.commit()
        db.refresh(word_list)
    return word_list


def get_or_create_spb_word_list(
    db: Session,
    name: str,
    *,
    group_id: int | None,
    sequence_offset: int,
) -> WordList:
    cleaned_name = clean_list_name(name)
    word_list = None
    if group_id:
        word_list = db.scalar(
            select(WordList)
            .where(
                WordList.group_id == group_id,
                WordList.sequence_offset == sequence_offset,
            )
            .order_by(WordList.id.asc())
            .limit(1)
        )
    if not word_list:
        word_list = db.scalar(
            select(WordList).where(WordList.name == cleaned_name).order_by(WordList.id.asc()).limit(1)
        )
    if not word_list:
        word_list = WordList(name=cleaned_name, display_order=next_word_list_display_order(db))
        db.add(word_list)
    if group_id and word_list.group_id != group_id:
        word_list.group_id = group_id
    if word_list.sequence_offset != sequence_offset:
        word_list.sequence_offset = sequence_offset
    db.commit()
    db.refresh(word_list)
    return word_list


def next_word_list_display_order(db: Session) -> int:
    current_min = db.scalar(select(func.min(WordList.display_order))) or 0
    return int(current_min) - 10


def clear_word_list_items(db: Session, word_list_id: int) -> None:
    db.execute(delete(WordListItem).where(WordListItem.word_list_id == word_list_id))
    db.commit()


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
        default_list = WordList(name="默认单词表", display_order=0)
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
    word_lists = db.scalars(
        select(WordList).order_by(WordList.display_order.asc(), WordList.created_at.desc(), WordList.id.desc())
    ).all()
    return [word_list for word_list in word_lists if not is_wrong_word_list_name(word_list.name)]


def word_list_groups(db: Session) -> list[WordListGroup]:
    return db.scalars(
        select(WordListGroup).order_by(WordListGroup.display_order.asc(), WordListGroup.created_at.desc(), WordListGroup.id.desc())
    ).all()


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
        word.image_issue = False
        word.enrichment_error = None
        db.add(word)
        db.commit()
        remember_word_resource(db, word, image_source="batch-upload", override_media=True, commit=True)
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
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        progress = db.scalar(select(ChallengeProgress).where(ChallengeProgress.word_list_id == word_list_id))
        if progress:
            return progress
        raise
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


def parse_form_int(value: Any, default: int = 0, min_value: int | None = None, max_value: int | None = None) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        parsed = default
    if min_value is not None:
        parsed = max(parsed, min_value)
    if max_value is not None:
        parsed = min(parsed, max_value)
    return parsed


def challenge_trace_id(value: str | None = None) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:-]", "", str(value or "").strip())
    return cleaned[:80] or f"chg-{uuid4().hex[:12]}"


def challenge_http_error(status_code: int, message: str, trace_id: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=f"{message}（追踪码：{trace_id}）",
        headers={"X-SpeakEasy-Trace-Id": trace_id},
    )


def record_wrong_word(db: Session, word_id: int, wrong_date: date | None = None) -> None:
    target_date = wrong_date or date.today()
    wrong_word = db.scalar(
        select(WrongWord).where(
            WrongWord.word_id == word_id,
            WrongWord.wrong_date == target_date,
        )
    )
    if wrong_word:
        wrong_word.wrong_count += 1
    else:
        wrong_word = WrongWord(word_id=word_id, wrong_date=target_date)
    db.add(wrong_word)
    word_list = get_or_create_wrong_word_list(db, target_date)
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


def challenge_day_wrong_word_ids(db: Session, challenge_date: date) -> set[int]:
    word_ids: set[int] = set()
    wrong_word_list = get_wrong_word_list(db, challenge_date)
    if wrong_word_list:
        word_ids.update(
            row[0]
            for row in db.execute(
                select(WordListItem.word_id).where(WordListItem.word_list_id == wrong_word_list.id)
            ).all()
        )
    word_ids.update(
        row[0]
        for row in db.execute(
            select(ChallengeDailyWord.word_id)
            .where(ChallengeDailyWord.challenge_date == challenge_date)
            .where(ChallengeDailyWord.wrong_count > 0)
        ).all()
    )
    word_ids.update(
        row[0]
        for row in db.execute(select(WrongWord.word_id).where(WrongWord.wrong_date == challenge_date)).all()
    )
    return word_ids


def challenge_day_corrected_wrong_word_ids(db: Session, challenge_date: date, word_ids: set[int]) -> set[int]:
    if not word_ids:
        return set()
    sorted_word_ids = sorted(word_ids)
    return {
        row[0]
        for row in db.execute(
            select(ChallengeDailyWord.word_id)
            .where(ChallengeDailyWord.word_id.in_(sorted_word_ids))
            .where(ChallengeDailyWord.challenge_date >= challenge_date)
            .where(ChallengeDailyWord.correct_count > 0)
            .group_by(ChallengeDailyWord.word_id)
        ).all()
    }


def challenge_day_pending_wrong_word_ids(db: Session, challenge_date: date) -> set[int]:
    wrong_ids = challenge_day_wrong_word_ids(db, challenge_date)
    corrected_ids = challenge_day_corrected_wrong_word_ids(db, challenge_date, wrong_ids)
    return wrong_ids - corrected_ids


def correction_challenge_words(db: Session, word_list_id: int, wrong_date: date | None) -> list[Word]:
    if not wrong_date:
        return get_words_for_list(db, word_list_id)
    pending_ids = challenge_day_pending_wrong_word_ids(db, wrong_date)
    if not pending_ids:
        return []
    words = [word for word in get_words_for_list(db, word_list_id) if word.id in pending_ids]
    seen_ids = {word.id for word in words}
    missing_ids = sorted(pending_ids - seen_ids)
    if missing_ids:
        words.extend(db.scalars(select(Word).where(Word.id.in_(missing_ids)).order_by(Word.word.asc())).all())
    return words


def wrong_word_count(db: Session) -> int:
    return db.scalar(select(func.count(WrongWord.id))) or 0


def wrong_word_list_date_from_name(name: str) -> date | None:
    match = re.fullmatch(r"生词本 (\d{4}-\d{2}-\d{2})", str(name or "").strip())
    return parse_wrong_date(match.group(1)) if match else None


def wrong_word_dates(db: Session) -> list[date]:
    dates: set[date] = set()
    dates.update(row[0] for row in db.execute(select(WrongWord.wrong_date)).all() if row[0])
    dates.update(
        row[0]
        for row in db.execute(
            select(ChallengeDailyWord.challenge_date).where(ChallengeDailyWord.wrong_count > 0)
        ).all()
        if row[0]
    )
    dates.update(
        row[0]
        for row in db.execute(select(ChallengeDailyStat.stat_date).where(ChallengeDailyStat.wrong_count > 0)).all()
        if row[0]
    )
    for name in db.scalars(select(WordList.name).where(WordList.name.like("生词本 %"))).all():
        wrong_date = wrong_word_list_date_from_name(name)
        if wrong_date:
            dates.add(wrong_date)
    return sorted(dates, reverse=True)


def wrong_word_date_group_payload(db: Session, wrong_date: date) -> dict[str, Any]:
    day_payload = challenge_calendar_day_payload(db, wrong_date)
    wrong_items = [
        item
        for item in day_payload.get("words", [])
        if item.get("was_wrong") or int(item.get("wrong_count") or 0) > 0 or item.get("status") == "wrong"
    ]
    cover_word = next((item for item in wrong_items if item.get("image_url")), wrong_items[0] if wrong_items else None)
    count = len(wrong_items) or int(day_payload.get("wrong") or 0)
    wrong_total = int(day_payload.get("wrong_attempts") or sum(int(item.get("wrong_count") or 0) for item in wrong_items))
    corrected_count = int(day_payload.get("corrected") or 0)
    pending_count = int(day_payload.get("correction_pending") or 0)
    return {
        "date": wrong_date.isoformat(),
        "count": count,
        "wrong_total": wrong_total,
        "corrected_count": corrected_count,
        "pending_count": pending_count,
        "status": "corrected" if pending_count == 0 and count else "pending",
        "cover_word": cover_word,
        "words": [
            {
                "word": item,
                "wrong_count": int(item.get("wrong_count") or 0),
                "corrected": bool(item.get("corrected")),
            }
            for item in wrong_items
        ],
    }


def pending_wrong_word_count(db: Session) -> int:
    return sum(len(challenge_day_pending_wrong_word_ids(db, wrong_date)) for wrong_date in wrong_word_dates(db))


def needs_image_sync(word: Word) -> bool:
    return not word.image_locked and not is_local_media_url(word.image_url)


def get_pending_image_words(db: Session, word_list_id: int) -> list[Word]:
    words = db.scalars(
        select(Word)
        .join(WordListItem, WordListItem.word_id == Word.id)
        .where(WordListItem.word_list_id == word_list_id)
        .order_by(Word.word.asc())
    ).all()
    apply_word_resources(db, words, include_image=False)
    return [word for word in words if needs_image_sync(word)]


def get_missing_image_words(db: Session, word_list_id: int) -> list[Word]:
    words = db.scalars(
        select(Word)
        .join(WordListItem, WordListItem.word_id == Word.id)
        .where(WordListItem.word_list_id == word_list_id)
        .order_by(WordListItem.id.asc())
    ).all()
    apply_word_resources(db, words, include_image=False)
    return [word for word in words if not (word.image_url or "").strip()]


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


def normalize_list_ai_image_model(model: str | None) -> str:
    selected = (model or LIST_AI_IMAGE_DEFAULT_MODEL).strip()
    if selected not in LIST_AI_IMAGE_MODEL_LABELS:
        return LIST_AI_IMAGE_DEFAULT_MODEL
    return selected


def list_ai_image_model_label(model: str | None) -> str:
    selected = normalize_list_ai_image_model(model)
    return LIST_AI_IMAGE_MODEL_LABELS[selected]


def ai_image_quota_cache_key(model: str | None = None, target_date: date | None = None) -> str:
    day = target_date or date.today()
    selected_model = normalize_list_ai_image_model(model)
    return f"{AI_IMAGE_QUOTA_CACHE_PREFIX}:{selected_model}:{day.isoformat()}"


def ai_image_daily_free_limit(model: str | None = None) -> tuple[int, bool]:
    selected_model = normalize_list_ai_image_model(model)
    if selected_model in LIST_AI_IMAGE_DAILY_FREE_QUOTAS:
        return max(int(LIST_AI_IMAGE_DAILY_FREE_QUOTAS[selected_model]), 0), True
    configured_limit = max(int(settings.ai_image_daily_free_quota or 0), 0)
    return configured_limit, configured_limit > 0


def ai_image_quota_status(db: Session, target_date: date | None = None, model: str | None = None) -> dict[str, Any]:
    day = target_date or date.today()
    selected_model = normalize_list_ai_image_model(model)
    entry = db.get(CacheEntry, ai_image_quota_cache_key(selected_model, day))
    used = 0
    if entry:
        try:
            payload = json.loads(entry.payload)
            if isinstance(payload, dict):
                used = max(int(payload.get("used") or 0), 0)
        except (TypeError, ValueError, json.JSONDecodeError):
            used = 0
    limit, configured = ai_image_daily_free_limit(selected_model)
    remaining = max(limit - used, 0) if configured else None
    return {
        "date": day.isoformat(),
        "model": selected_model,
        "model_label": list_ai_image_model_label(selected_model),
        "used": used,
        "limit": limit,
        "configured": configured,
        "remaining": remaining,
    }


def ai_image_quota_requires_confirmation(quota: dict[str, Any], paid_confirmed: bool) -> bool:
    if paid_confirmed or not quota.get("configured"):
        return False
    return int(quota.get("remaining") or 0) <= 0


def ai_image_quota_confirmation_message(quota: dict[str, Any]) -> str:
    if quota.get("configured") and int(quota.get("limit") or 0) <= 0:
        return "当前模型没有免费额度，需要确认是否继续付费使用。"
    return "今日免费额度已用完，需要确认是否继续付费使用。"


def increment_ai_image_quota(db: Session, model: str | None = None, amount: int = 1) -> dict[str, Any]:
    day = date.today()
    selected_model = normalize_list_ai_image_model(model)
    key = ai_image_quota_cache_key(selected_model, day)
    current = ai_image_quota_status(db, day, selected_model)
    next_used = current["used"] + max(int(amount), 0)
    payload = {
        "date": day.isoformat(),
        "model": selected_model,
        "used": next_used,
    }
    expires_at = datetime.combine(day + timedelta(days=2), datetime.min.time())
    encoded = json.dumps(payload, ensure_ascii=False)
    entry = db.get(CacheEntry, key)
    if entry:
        entry.payload = encoded
        entry.expires_at = expires_at
    else:
        db.add(CacheEntry(key=key, payload=encoded, expires_at=expires_at))
    db.commit()
    return ai_image_quota_status(db, day, selected_model)


def update_list_ai_image_job(job_id: str, **changes) -> None:
    with IMAGE_SYNC_LOCK:
        job = LIST_AI_IMAGE_JOBS.get(job_id)
        if not job:
            return
        job.update(changes)


def append_list_ai_image_result(job_id: str, result: dict) -> None:
    with IMAGE_SYNC_LOCK:
        job = LIST_AI_IMAGE_JOBS.get(job_id)
        if not job:
            return
        job["results"].append(result)
        job["results"] = job["results"][-60:]
        job["done"] += 1
        if result.get("skipped"):
            job["skipped"] += 1
        elif result.get("ok"):
            job["generated"] += 1
        else:
            job["failed"] += 1
        if result.get("quota"):
            job["quota"] = result["quota"]


def list_ai_image_error_detail(exc: Exception) -> tuple[str, bool, bool]:
    if isinstance(exc, httpx.HTTPStatusError):
        detail = exc.response.text[:400] if exc.response is not None else str(exc)
    else:
        detail = str(exc)
    if "not configured" in detail:
        return detail, True, False
    if is_ai_quota_error(detail):
        return "额度已经用完", True, True
    return detail[:300] or "AI 生图失败", False, False


async def generate_missing_word_ai_image(db: Session, word: Word, model: str) -> dict:
    db.refresh(word)
    if (word.image_url or "").strip():
        return {"ok": True, "id": word.id, "word": word.word, "image_url": word.image_url, "skipped": True}

    content = await generate_word_image(
        provider="dashscope",
        word=word.word,
        english_definition=word.english_definition,
        chinese_definition=word.chinese_definition,
        theme="单词卡片",
        style="写实摄影",
        dashscope_api_key=settings.dashscope_api_key,
        dashscope_endpoint=settings.dashscope_image_endpoint,
        dashscope_task_endpoint=settings.dashscope_task_endpoint,
        dashscope_poll_seconds=settings.dashscope_image_poll_seconds,
        dashscope_timeout_seconds=settings.dashscope_image_timeout_seconds,
        dashscope_model=model,
    )
    previous_url = word.image_url
    image_url = store_uploaded_word_image(word.word, content, IMAGE_DIR)
    word.image_url = image_url
    word.image_locked = True
    word.image_issue = False
    word.enrichment_error = None
    db.add(word)
    db.commit()
    remember_word_resource(db, word, image_source=f"ai-image:{model}", override_media=True, commit=True)
    if previous_url != word.image_url:
        remove_local_image(previous_url, IMAGE_DIR)
    quota = increment_ai_image_quota(db, model)
    return {
        "ok": True,
        "id": word.id,
        "word": word.word,
        "image_url": word.image_url,
        "provider": "dashscope",
        "model": model,
        "model_label": list_ai_image_model_label(model),
        "quota": quota,
    }


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


def run_list_ai_image_job(job_id: str, word_list_id: int, model: str, paid_confirmed: bool = False) -> None:
    db = SessionLocal()
    try:
        pending_words = get_missing_image_words(db, word_list_id)
        paid_note = "，已确认可能产生费用" if paid_confirmed else ""
        update_list_ai_image_job(
            job_id,
            status="running",
            total=len(pending_words),
            done=0,
            failed=0,
            generated=0,
            skipped=0,
            message=f"正在使用 {list_ai_image_model_label(model)} 生成缺失图片{paid_note}",
        )
        if not pending_words:
            update_list_ai_image_job(job_id, status="complete", message="当前单词表没有缺失图片。")
            return

        fatal_error = ""
        requires_paid_confirmation = False
        for word in pending_words:
            quota = ai_image_quota_status(db, model=model)
            if ai_image_quota_requires_confirmation(quota, paid_confirmed):
                fatal_error = ai_image_quota_confirmation_message(quota)
                requires_paid_confirmation = True
                update_list_ai_image_job(job_id, quota=quota)
                break
            update_list_ai_image_job(job_id, current_word=word.word)
            try:
                result = asyncio.run(generate_missing_word_ai_image(db, word, model))
            except Exception as exc:
                detail, fatal, quota_error = list_ai_image_error_detail(exc)
                requires_paid_confirmation = quota_error and not paid_confirmed
                result = {
                    "ok": False,
                    "id": word.id,
                    "word": word.word,
                    "error": detail,
                    "fatal": fatal,
                    "quota_error": quota_error,
                }
                try:
                    word.enrichment_error = f"AI 批量生图失败: {detail}"
                    db.add(word)
                    db.commit()
                except Exception:
                    db.rollback()
                if fatal:
                    fatal_error = detail
            append_list_ai_image_result(job_id, result)
            if fatal_error:
                break

        with IMAGE_SYNC_LOCK:
            job = LIST_AI_IMAGE_JOBS.get(job_id)
            failed = job.get("failed", 0) if job else 0
            generated = job.get("generated", 0) if job else 0
        if fatal_error:
            message = fatal_error if requires_paid_confirmation else f"批量 AI 生图已停止：{fatal_error}"
            status = "failed"
        elif failed:
            message = f"已生成 {generated} 张，{failed} 个单词失败。"
            status = "failed"
        else:
            message = f"已生成 {generated} 张缺失图片。"
            status = "complete"
        update_list_ai_image_job(
            job_id,
            status=status,
            current_word="",
            message=message,
            requires_paid_confirmation=requires_paid_confirmation,
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
    progress = get_or_create_challenge_progress(db, word_list.id) if total else None
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
        if list_id:
            day_query = day_query.where(ChallengeDailyWord.word_list_id == list_id)
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


async def enrich_word_ids(word_ids: list[int], *, include_images: bool = True) -> None:
    db = SessionLocal()
    try:
        for word_id in word_ids:
            word = db.get(Word, word_id)
            if word:
                await enrich_word(db, word, include_images=include_images)
                remember_word_resource(db, word, commit=True)
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

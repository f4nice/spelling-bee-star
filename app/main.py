import asyncio
from calendar import monthrange
from datetime import date, datetime, timedelta
import html
from io import BytesIO
import json
import logging
from pathlib import Path
import random
import re
import sys
from threading import Lock, Thread
from typing import Any
import unicodedata
from urllib.parse import quote_plus, urlparse
from uuid import uuid4
import zipfile

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, func, inspect, or_, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
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
VERSION_MATRIX_PATH = MEDIA_DIR / "version_matrix.json"
DEFAULT_VERSION_MATRIX_PATH = BASE_DIR.parent / "VERSION_MATRIX.default.json"
settings = get_settings()
DEFAULT_RELEASE_VERSION = "BIZ-REL-20260705-005"
DEFAULT_PAGE_VERSION = "v20260705.5"
CHALLENGE_LOGGER = logging.getLogger("speakeasy.challenge")
LEGACY_MACHINE_CODE_FIELD = "machine" + "Code"
PUBLIC_ASSET_DIR = MEDIA_DIR / "generated-assets"
SPB_DETAIL_BACKFILL_BATCH_LIMIT = 300
SCIENCE_DISCOVERY_CACHE_DIR = MEDIA_DIR / "science-discoveries"
SCIENCE_IMAGE_VERSION = "20260629-no-text-1"
SCIENCE_DISCOVERY_DATA_VERSION = "20260629-source-mode-1"
SCIENCE_PUBLIC_CONTENT_VERSION = "v6"
SCIENCE_PUBLIC_CONTENT_TTL = timedelta(days=3650)
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
    {
        "key": "science_discoveries",
        "label": "科学探索",
        "badge_label": "探索 100 个知识点",
        "target": 100,
        "unit": "个",
        "tier": "emerald",
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


IMAGE_SYNC_LOCK = Lock()
CACHE_REFRESHING: set[str] = set()
CACHE_REFRESH_LOCK = Lock()

MEDIA_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
BOOK_COVER_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_ASSET_DIR.mkdir(parents=True, exist_ok=True)
SCIENCE_DISCOVERY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if re.fullmatch(r"/static/vue/(speakeasy-app|challenge-app)\.js", path):
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


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema_columns()
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    BOOK_COVER_DIR.mkdir(parents=True, exist_ok=True)
    SCIENCE_DISCOVERY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ensure_version_matrix_file()
    with SessionLocal() as db:
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
def good_words_science_home_page(request: Request, db: Session = Depends(get_db)):
    return vue_shell(request, db, "booklearner/science")


@app.get("/booklearner/science/{slug}", response_class=HTMLResponse)
def good_words_science_page(slug: str, request: Request, db: Session = Depends(get_db)):
    if not find_science_article(slug):
        raise HTTPException(status_code=404, detail="Science discovery not found")
    return vue_shell(request, db, f"booklearner/science/{slug}")


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


@app.get("/api/vue/shell")
def vue_shell_api(db: Session = Depends(get_db)):
    return serialize_shell_context({
        "app_name": settings.app_name,
        "daily_quote": get_daily_quote(db),
        "sidebar_challenges": sidebar_challenge_progress(db),
        "wrong_word_count": wrong_word_count(db),
        "learning_growth": learning_growth_summary(db),
    })


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
    remember_word_resource(db, word, override_text=True, commit=True)
    return {"ok": True, "field": field, "value": next_value}


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
        split_group = get_or_create_word_list_group_by_name(db, base_name)
        for chunk_index in range(0, len(rows), chunk_size):
            chunk_number = (chunk_index // chunk_size) + 1
            chunk_list = get_or_create_word_list_by_name(db, f"{base_name}-{chunk_number}")
            clear_word_list_items(db, chunk_list.id)
            chunk_list.group_id = split_group.id
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
    # Imports should not auto-match images; use the list page image tools after import.
    if word_ids:
        start_enrichment_thread(word_ids, include_images=False)
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


@app.get("/spb", response_class=HTMLResponse)
def spb_page(request: Request, db: Session = Depends(get_db)):
    return vue_shell(request, db, "spb")


SPB_INDIVIDUAL_WORD_BANK_GROUPS = [
    {
        "key": "beginner",
        "title": "小初组",
        "subtitle": "Beginner Group(G1-G2)",
        "status": "available",
        "prefix": "SPB个人赛冠军词库-小初组",
        "source_count": 1300,
        "source_file": "spb_individual_beginner_g1_g2_words.json",
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
        "spb_product_id": 5,
        "spb_flag": "BEGINNER_GROUP4",
    },
    {
        "key": "origin",
        "title": "词源单词",
        "subtitle": "Language Origin",
        "status": "available",
        "prefix": "SPB个人赛冠军词库-词源单词",
        "source_count": 2000,
        "source_file": "spb_individual_language_origin_words.json",
        "spb_product_id": 6,
        "spb_flag": "LANGUAGE_ORIGIN",
    },
    {
        "key": "challenge",
        "title": "挑战词汇",
        "subtitle": "Challenge Words",
        "status": "available",
        "prefix": "SPB个人赛冠军词库-挑战词汇",
        "source_count": 1300,
        "source_file": "spb_individual_challenge_words.json",
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
        "groups": [],
        "sync_note": "小程序公开产品接口暂未返回团体赛词库；拿到缓存或授权后会出现在这里。",
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
        "sync_note": "小程序公开产品接口暂未返回托福词库；拿到缓存或授权后会出现在这里。",
    },
    {
        "key": "ielts",
        "name": "国际考试（雅思）",
        "subtitle": "IELTS Word Banks",
        "source_type": "ielts_thesaurus",
        "groups": [],
        "sync_note": "小程序公开产品接口暂未返回雅思词库；拿到缓存或授权后会出现在这里。",
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
    }


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
            f"{group['title']} 缺少小程序授权，服务器也没有这组源词库缓存。请先配置 SPB 小程序授权后再同步。"
            if not spb_miniprogram_authorization_configured()
            else f"{group['title']} 已尝试调用小程序接口，但没有拿到可导入词库；请确认小程序账号已开通这组词库。"
        )
        raise HTTPException(
            status_code=404,
            detail=detail,
        )

    rows = await prepare_spb_rows_with_local_audio(rows, group)
    text_detail_count = sum(1 for row in rows if spb_has_text_fields(row))
    local_audio_count = sum(
        1
        for row in rows
        if is_local_audio_url(row.get("american_audio_url")) or is_local_audio_url(row.get("british_audio_url"))
    )
    word_ids, split_lists = import_spb_word_bank_rows(db, group, rows)
    if word_ids:
        start_enrichment_thread(word_ids, include_images=False)
    response = spb_payload(db, collection["key"])
    message = f"已同步 {group['title']}：{len(word_ids)} 个单词，{len(split_lists)} 个分表。"
    if text_detail_count:
        message += f" 已写入详情字段 {text_detail_count} 个。"
    elif not spb_miniprogram_authorization_configured():
        message += " 服务器未配置 SPB 小程序授权，暂时只能导入词表，不能读取小程序详情字段。"
    if local_audio_count:
        message += f" 已保存小程序音频 {local_audio_count} 个到本地。"
    response["message"] = message
    response["source"] = source_path.name
    return response


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

    resource_applied = apply_word_resources(db, words, include_image=False)
    missing_words = [
        word
        for word in words
        if not (word.phonetic or "").strip()
        or not (word.part_of_speech or "").strip()
        or not (word.english_definition or "").strip()
        or not (word.english_example or "").strip()
    ]
    queued_ids = [word.id for word in missing_words[:SPB_DETAIL_BACKFILL_BATCH_LIMIT]]
    remaining_after_batch = max(len(missing_words) - len(queued_ids), 0)
    if queued_ids:
        start_enrichment_thread(queued_ids, include_images=False)

    response = spb_payload(db, collection["key"])
    if queued_ids:
        response["message"] = f"已从公共资源表补齐 {resource_applied} 个；后台继续补全 {len(queued_ids)} 个缺音标、词性、英文定义或英文例句的单词。"
        if remaining_after_batch:
            response["message"] += f" 还有 {remaining_after_batch} 个会留到下一批，避免一次任务过大。"
    else:
        response["message"] = f"已从公共资源表补齐 {resource_applied} 个；这组音标、词性、英文定义和英文例句已经没有明显缺口。"
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
        "chinese_definition": word.chinese_definition,
        "english_example": word.english_example,
        "image_url": word.image_url,
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
    authorization_configured = spb_miniprogram_authorization_configured()
    sync_ready = group.get("status") != "locked" and not synced and (authorization_configured or cached_source_count > 0)
    sync_note = spb_group_sync_note(group, synced, cached_source_count, authorization_configured)
    return {
        "key": group["key"],
        "title": group["title"],
        "subtitle": group["subtitle"],
        "status": "synced" if synced else group.get("status", "available"),
        "source_count": group.get("source_count") or cached_source_count or None,
        "cached_source_count": cached_source_count,
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
    if authorization_configured:
        return "可从小程序接口同步；如果接口返回空结果，会自动尝试本地缓存。"
    if cached_source_count:
        return f"已找到本地源词库缓存，可导入 {cached_source_count} 个单词。"
    return "缺少小程序授权，且本地没有这组源词库缓存；请先配置服务器小程序授权。"


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


def load_spb_source_rows(group: dict[str, Any]) -> tuple[list[dict[str, Any]], Path]:
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
        word = normalize_spb_source_word_text(raw)
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
        row.update(spb_audio_urls_from_payload(value))
        text_fields = spb_text_fields_from_payload(value)
        if text_fields:
            row.update(text_fields)
            row["spb_text_source"] = "spb-source-cache"
        rows.append(row)
    return rows


SPB_WORD_PUNCTUATION = {" ", "'", "’", "-", "‐", "‑", "–", "—", "."}


def normalize_spb_source_word_text(value: Any) -> str:
    text = " ".join(str(value or "").strip().split())
    return unicodedata.normalize("NFC", text)[:128]


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
            "eurl",
        ),
    )
    generic_url = spb_find_first_field(payload, ("audioUrl", "audio_url", "audio", "voiceUrl", "voice_url", "durl"))
    result: dict[str, str] = {}
    if spb_looks_like_audio_url(us_url):
        result["american_audio_url"] = us_url
    elif spb_looks_like_audio_url(generic_url):
        result["american_audio_url"] = generic_url
    if spb_looks_like_audio_url(gb_url):
        result["british_audio_url"] = gb_url
    return result


def spb_looks_like_audio_url(value: str | None) -> bool:
    if not value:
        return False
    lower_value = value.lower()
    return lower_value.startswith(("http://", "https://")) and any(
        marker in lower_value for marker in (".mp3", ".m4a", ".wav", "/audio", "voice", "sound")
    )


def spb_text_fields_from_payload(payload: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    phonetic = spb_find_first_field(
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
    part_of_speech = spb_find_first_field(
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
    english_definition = spb_find_first_field(
        payload,
        (
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
    chinese_definition = spb_find_first_field(
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
    english_example = spb_find_first_field(
        payload,
        (
            "english_example",
            "englishExample",
            "enExample",
            "exampleEn",
            "sentenceEn",
            "exampleSentence",
            "example",
            "examples",
            "sentence",
            "sentences",
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


async def prepare_spb_rows_with_local_audio(rows: list[dict[str, Any]], group: dict[str, Any]) -> list[dict[str, Any]]:
    if not rows:
        return rows

    semaphore = asyncio.Semaphore(5)

    async def prepare(row: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
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
                    for key, value in {**detail_audio_fields, **detail_text_fields}.items():
                        prepared[key] = prepared.get(key) or value
            for accent, field_name in (("us", "american_audio_url"), ("gb", "british_audio_url")):
                audio_url = str(prepared.get(field_name) or "").strip()
                if not audio_url or is_local_audio_url(audio_url):
                    continue
                try:
                    local_url = await store_audio_candidate(
                        prepared["word"],
                        accent,
                        f"spb-{group.get('spb_flag') or group.get('key') or 'audio'}",
                        audio_url,
                        AUDIO_DIR,
                    )
                except Exception:
                    local_url = None
                if local_url:
                    prepared[field_name] = local_url
                    prepared[f"{field_name}_source"] = "spb-miniprogram"
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


async def apply_spb_details_to_word(db: Session, word: Word, *, list_id: int | None = None) -> bool:
    changed = False
    for group in spb_candidate_groups_for_word(db, word, list_id):
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
                prepared.update(detail_audio_fields)
                prepared.update(detail_text_fields)

        prepared_rows = await prepare_spb_rows_with_local_audio([prepared], group)
        prepared = prepared_rows[0] if prepared_rows else prepared
        if apply_spb_text_fields_to_word(word, prepared):
            changed = True
        if apply_imported_local_audio(word, prepared):
            changed = True
        if changed:
            remember_word_resource(
                db,
                word,
                american_audio_source=prepared.get("american_audio_url_source"),
                british_audio_source=prepared.get("british_audio_url_source"),
                override_text=bool(prepared.get("spb_text_source")),
                override_media=bool(prepared.get("american_audio_url_source") or prepared.get("british_audio_url_source")),
                commit=False,
            )
            return True
    return changed


def apply_spb_text_fields_to_word(word: Word, row: dict[str, Any]) -> bool:
    changed = False
    for field in ("phonetic", "part_of_speech"):
        value = str(row.get(field) or "").strip()
        if value and not (getattr(word, field, None) or "").strip():
            setattr(word, field, value)
            changed = True

    for field, lock_field in (
        ("english_definition", "english_definition_locked"),
        ("english_example", "english_example_locked"),
    ):
        value = str(row.get(field) or "").strip()
        if value and not (getattr(word, field, None) or "").strip():
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
        not (word.chinese_definition or "").strip()
        or should_refresh_chinese_definition(word.word, word.chinese_definition, word.english_definition)
    ):
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


def challenge_calendar_day_payload(db: Session, challenge_date: date) -> dict:
    daily_wrong_ids = challenge_day_wrong_word_ids(db, challenge_date)
    corrected_wrong_ids = challenge_day_corrected_wrong_word_ids(db, challenge_date, daily_wrong_ids)
    pending_wrong_ids = daily_wrong_ids - corrected_wrong_ids
    wrong_word_list = get_wrong_word_list(db, challenge_date)
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
            "was_wrong": bool((detail.wrong_count or 0) > 0 or word.id in daily_wrong_ids),
            "corrected": word.id in corrected_wrong_ids,
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
    seen_word_ids = {item["id"] for item in words}
    missing_wrong_ids = sorted(daily_wrong_ids - seen_word_ids)
    if missing_wrong_ids:
        wrong_words = db.scalars(select(Word).where(Word.id.in_(missing_wrong_ids)).order_by(Word.word.asc())).all()
        words.extend(
            {
                "id": word.id,
                "word": word.word,
                "status": "correct" if word.id in corrected_wrong_ids else "wrong",
                "was_wrong": True,
                "corrected": word.id in corrected_wrong_ids,
                "correct_count": 0,
                "wrong_count": 1,
                "word_list_id": wrong_word_list.id if wrong_word_list else None,
                "word_list_name": "\u5f53\u65e5\u751f\u8bcd\u672c",
                "image_url": word.image_url,
                "phonetic": word.phonetic,
                "part_of_speech": word.part_of_speech,
                "english_definition": word.english_definition,
                "chinese_definition": word.chinese_definition,
            }
            for word in wrong_words
        )

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
        word.image_issue = False
        word.enrichment_error = None
        db.add(word)
        db.commit()
        remember_word_resource(db, word, image_source="ai-image", override_media=True, commit=True)
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
    word.image_issue = False
    word.enrichment_error = None
    db.add(word)
    db.commit()
    remember_word_resource(db, word, image_source="network", override_media=True, commit=True)
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
                word.image_issue = False
                word.enrichment_error = None
                db.add(word)
                db.commit()
                remember_word_resource(db, word, image_source="network-sync", override_media=False, commit=True)
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
    target = AUDIO_DIR / f"{safe_word}-{accent}-recorded-{uuid4().hex[:8]}{suffix}"
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
        "message": "" if can_commit_audio else "当前音频优先级更高，已保留原音频。",
    }


@app.post("/api/vue/words/{word_id}/ai-audio")
async def word_ai_audio(
    word_id: int,
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

    try:
        audio_url = await generate_word_ai_audio(
            provider=settings.ai_tts_provider,
            api_key=settings.openai_api_key,
            model=settings.openai_tts_model,
            word=word.word,
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
    audio_source = ai_tts_audio_source(text_mode)
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
            apply_imported_local_audio(existing, row)
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
                override_text=bool(row.get("spb_text_source")),
                override_media=bool(row.get("american_audio_url_source") or row.get("british_audio_url_source")),
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

    return word_ids


def local_import_audio_url(value: str | None) -> str | None:
    audio_url = str(value or "").strip()
    return audio_url if is_local_audio_url(audio_url) else None


def audio_source_priority(source: str | None = None, audio_url: str | None = None) -> int:
    marker = f"{source or ''} {audio_url or ''}".lower()
    if "spb" in marker or "miniprogram" in marker:
        return 300
    if "aliyun" in marker or "dashscope" in marker or "phoneme" in marker:
        return 200
    if "ai-tts" in marker or "openai" in marker or re.search(r"-(female|male)-ai-", marker):
        return 180
    if "choice" in marker or "recorded" in marker:
        return 150
    if any(token in marker for token in ("free-dictionary", "youdao", "google", "dictionary", "tts")):
        return 100
    return 0


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


def apply_imported_local_audio(word: Word, row: dict[str, Any]) -> bool:
    changed = False
    american_audio_url = local_import_audio_url(row.get("american_audio_url"))
    british_audio_url = local_import_audio_url(row.get("british_audio_url"))
    american_source = row.get("american_audio_url_source")
    british_source = row.get("british_audio_url_source")
    if should_replace_audio(word.american_audio_url, american_audio_url, incoming_source=american_source):
        word.american_audio_url = american_audio_url
        word.american_audio_locked = True
        changed = True
    if should_replace_audio(word.british_audio_url, british_audio_url, incoming_source=british_source):
        word.british_audio_url = british_audio_url
        word.british_audio_locked = True
        changed = True
    return changed


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


def start_enrichment_thread(word_ids: list[int], *, include_images: bool = True) -> None:
    worker = Thread(target=lambda: asyncio.run(enrich_word_ids(word_ids, include_images=include_images)), daemon=True)
    worker.start()


def clean_list_name(name: str) -> str:
    text = " ".join((name or "").split())
    return text[:255] or "新单词表"


def normalize_resource_word(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())[:128]


def get_word_resource(db: Session, word_text: str | None) -> WordResourcePool | None:
    normalized = normalize_resource_word(word_text)
    if not normalized:
        return None
    return db.scalar(select(WordResourcePool).where(WordResourcePool.normalized_word == normalized))


def word_has_shareable_resource(word: Word) -> bool:
    return any(
        (getattr(word, field, None) or "").strip()
        for field in (
            "phonetic",
            "part_of_speech",
            "english_definition",
            "chinese_definition",
            "english_example",
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
    override_text: bool = False,
    override_media: bool = False,
    commit: bool = False,
) -> bool:
    normalized = normalize_resource_word(word.word)
    if not normalized or not word_has_shareable_resource(word):
        return False

    resource = get_word_resource(db, word.word)
    changed = False
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

    if changed:
        db.add(resource)
        if commit:
            db.commit()
    return changed


def apply_word_resource(db: Session, word: Word, *, commit: bool = False, include_image: bool = True) -> bool:
    resource = get_word_resource(db, word.word)
    if not resource:
        return False

    changed = False
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
        if value and not (getattr(word, field, None) or "").strip():
            setattr(word, field, value)
            setattr(word, lock_field, True)
            changed = True

    if include_image and (resource.image_url or "").strip() and not (word.image_url or "").strip():
        word.image_url = resource.image_url
        word.image_locked = True
        word.image_issue = False
        changed = True
    if (resource.american_audio_url or "").strip() and should_replace_audio(
        word.american_audio_url,
        resource.american_audio_url,
        incoming_source=resource.american_audio_source,
    ):
        word.american_audio_url = resource.american_audio_url
        word.american_audio_locked = True
        changed = True
    if (resource.british_audio_url or "").strip() and should_replace_audio(
        word.british_audio_url,
        resource.british_audio_url,
        incoming_source=resource.british_audio_source,
    ):
        word.british_audio_url = resource.british_audio_url
        word.british_audio_locked = True
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
        {"key": "science_discoveries", "label": "科学点", "points": 8},
    ]


def learning_growth_summary(db: Session) -> dict[str, Any]:
    try:
        trophy_image = growth_trophy_image_url()
        spelling_words = db.scalar(select(func.count(ChallengeSpellingAttempt.id))) or 0
        challenge_rounds = db.scalar(select(func.coalesce(func.sum(ChallengeProgress.completed_rounds), 0))) or 0
        good_quotes = max(good_quote_growth_count(), growth_metric_value(db, "good_quotes"))
        science_discoveries = max(science_growth_count(), growth_metric_value(db, "science_discoveries"))
        values = {
            "spelling_words": int(spelling_words),
            "challenge_rounds": int(challenge_rounds),
            "good_quotes": int(good_quotes),
            "science_discoveries": int(science_discoveries),
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
        points = values["spelling_words"] * 2 + values["challenge_rounds"] * 50 + values["good_quotes"] * 3 + values["science_discoveries"] * 8
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
                {
                    "key": "science_seed",
                    "label": "科学探索库",
                    "value": values["science_discoveries"],
                    "target": 100,
                    "percent": percent_value(values["science_discoveries"], 100),
                },
            ],
        }
    except Exception:
        db.rollback()
        return default_learning_growth_summary()


def page_context(request: Request, db: Session, extra: dict | None = None) -> dict:
    context = {
        "request": request,
        "app_name": settings.app_name,
        "daily_quote": get_daily_quote(db),
        "sidebar_challenges": sidebar_challenge_progress(db),
        "wrong_word_count": wrong_word_count(db),
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
        if "word_lists" in table_names and "display_order" not in word_list_columns:
            connection.execute(text("ALTER TABLE word_lists ADD COLUMN display_order INTEGER NOT NULL DEFAULT 0"))
        if "word_lists" in table_names and "sequence_offset" not in word_list_columns:
            connection.execute(text("ALTER TABLE word_lists ADD COLUMN sequence_offset INTEGER NOT NULL DEFAULT 0"))
        if "word_lists" in table_names and "group_id" not in word_list_columns:
            connection.execute(text("ALTER TABLE word_lists ADD COLUMN group_id INTEGER NULL"))
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

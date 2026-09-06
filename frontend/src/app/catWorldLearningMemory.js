function safeCount(value) {
  return Math.max(Math.floor(Number(value) || 0), 0);
}

function clamp(value, min, max) {
  return Math.min(Math.max(Number(value) || 0, min), max);
}

const DEFAULT_MEMORY_STAGES = Object.freeze([
  Object.freeze({ key: "starter", label: "起步搭子", threshold: 1 }),
  Object.freeze({ key: "familiar", label: "熟悉节奏", threshold: 4 }),
  Object.freeze({ key: "steady", label: "稳定陪学", threshold: 10 }),
  Object.freeze({ key: "guardian", label: "英语守护猫", threshold: 24 }),
]);

const MEMORY_DAY_KEYS = new Set(["started", "warmup", "output", "warmup-output", "loop"]);
const MEMORY_REVIEW_STAGE_KEYS = new Set(["first", "strengthen", "settled"]);
const RECALL_WORD_PATTERN = /^[A-Za-z]+(?:['\u2019-][A-Za-z]+)*$/;
const RECALL_SENTENCE_WORD_PATTERN = /[A-Za-z]+(?:['\u2019-][A-Za-z]+)*/g;

const MEMORY_VISIT_TARGETS = Object.freeze({
  "gentle-starter": Object.freeze(["learning-garden", "reading-lamp", "word-gallery"]),
  "story-builder": Object.freeze(["study-desk", "word-gallery", "book-shelf"]),
  "idea-sparring": Object.freeze(["reading-lamp", "study-desk", "word-gallery"]),
  "loop-keeper": Object.freeze(["word-gallery", "study-desk", "learning-garden"]),
  "streak-keeper": Object.freeze(["learning-garden", "book-shelf", "reading-lamp"]),
  "review-organizer": Object.freeze(["book-shelf", "word-gallery", "study-desk"]),
  balanced: Object.freeze(["learning-garden", "study-desk", "book-shelf"]),
});

const MEMORY_VISIT_ANIMATIONS = Object.freeze({
  "gentle-starter": "blink",
  "story-builder": "book",
  "idea-sparring": "chirp",
  "loop-keeper": "paw",
  "streak-keeper": "heart",
  "review-organizer": "book",
  balanced: "book",
});

const MEMORY_VISIT_RITUALS = Object.freeze({
  "gentle-starter": Object.freeze({
    label: "轻声复述",
    statusVerb: "正在轻声复述",
    memoryStatus: "正在轻声翻看学习脚印",
    regularLead: (word) => `我想把 ${word} 轻声念一遍，你写过：`,
    todayLead: (word) => `今天刚找回的 ${word}，我想轻声再念一遍：`,
  }),
  "story-builder": Object.freeze({
    label: "句子续写",
    statusVerb: "正在把词放回句子",
    memoryStatus: "正在翻看我们的故事页",
    regularLead: (word) => `我把 ${word} 放回你写过的小故事里：`,
    todayLead: (word) => `今天刚找回的 ${word}，我把它放回这句话里：`,
  }),
  "idea-sparring": Object.freeze({
    label: "试新用法",
    statusVerb: "正在试一个新用法",
    memoryStatus: "正在琢磨旧词的新用法",
    regularLead: (word) => `我在想 ${word} 还能用进哪句话，先看看你写过的：`,
    todayLead: (word) => `今天刚找回的 ${word}，我已经在想它的新用法了：`,
  }),
  "loop-keeper": Object.freeze({
    label: "遮答回想",
    statusVerb: "正在遮答回想",
    memoryStatus: "正在遮住答案回想",
    regularLead: (word) => `我先遮住词义找回 ${word}，再对照你写过的：`,
    todayLead: (word) => `今天刚找回的 ${word}，我再遮住答案试一次：`,
  }),
  "streak-keeper": Object.freeze({
    label: "守住熟练",
    statusVerb: "正在守住熟练爪印",
    memoryStatus: "正在守住这页学习脚印",
    regularLead: (word) => `我来守住 ${word} 这枚熟练爪印，你写过：`,
    todayLead: (word) => `今天刚找回的 ${word}，这枚熟练爪印要收好：`,
  }),
  "review-organizer": Object.freeze({
    label: "整理复习页",
    statusVerb: "正在整理复习页",
    memoryStatus: "正在整理共同学习手册",
    regularLead: (word) => `我把 ${word} 放回复习页的正确位置，你写过：`,
    todayLead: (word) => `今天刚找回的 ${word}，我把它收回复习页：`,
  }),
  balanced: Object.freeze({
    label: "再看一遍",
    statusVerb: "正在再看一遍",
    memoryStatus: "正在翻看共同学习手册",
    regularLead: (word) => `我再看一遍 ${word}，还记得你写过：`,
    todayLead: (word) => `今天刚找回的 ${word}，我想再看一遍：`,
  }),
});

const MEMORY_VISIT_TONES = Object.freeze({
  calm: Object.freeze(["这次慢慢看就好。", "我想安静陪它待一会儿。"]),
  clingy: Object.freeze(["我想贴着你再念一遍。", "这次也要和你一起记住。"]),
  guardian: Object.freeze(["这一页我会替你守好。", "这个词先交给我看着。"]),
  chatty: Object.freeze(["下次也想听你亲口说。", "我已经想听它出现在新句子里了。"]),
  gentle: Object.freeze(["不用赶，想起一点就很好。", "我们轻轻记住这一页就好。"]),
  adventurous: Object.freeze(["下次再给它找个新句子。", "这个词还能带我们去新地方。"]),
  balanced: Object.freeze(["这一页先好好留住。", "下次见到它就更熟了。"]),
});

const MEMORY_TREASURE_SELECTION_LABELS = Object.freeze({
  "gentle-starter": "短句起步",
  "story-builder": "长句续写",
  "idea-sparring": "生词试用",
  "loop-keeper": "旧词接力",
  "streak-keeper": "熟词守护",
  "review-organizer": "薄弱词整理",
  balanced: "随手回看",
});

const MEMORY_REFLECTION_COPY = Object.freeze({
  started: Object.freeze({
    achievement: "那天先迈出了最小的一步，点亮了起步爪印。",
    reviewPrompt: "今天也可以只做 5 个词，开始就算进步。",
    actionLabel: "再练 5 个词",
    href: "/lists",
  }),
  warmup: Object.freeze({
    achievement: "那天完成了 20 词热身，把英语状态叫醒了。",
    reviewPrompt: "从那天的词里挑 1 个，遮住答案主动回想一次。",
    actionLabel: "再练一组词",
    href: "/lists",
  }),
  output: Object.freeze({
    achievement: "那天把英语真正用出来了，留下了一次表达。",
    reviewPrompt: "今天先补 5 个词，再把其中 1 个用进新句子。",
    actionLabel: "补一次练词",
    href: "/lists",
  }),
  "warmup-output": Object.freeze({
    achievement: "那天既完成了词汇热身，也把英语用出来了。",
    reviewPrompt: "复用那天的 1 个旧词，写或说一句新的表达。",
  }),
  loop: Object.freeze({
    achievement: "那天走完了输入、表达和回顾的完整英语闭环。",
    reviewPrompt: "先回想 1 个词和 1 句话，再决定今天还要不要继续。",
  }),
});

const MEMORY_REFLECTION_TONES = Object.freeze({
  calm: Object.freeze(["我把这页安静收好了。", "这页不用赶，我记得很稳。"]),
  clingy: Object.freeze(["那天我也一直贴在你旁边。", "这枚脚印是我们靠在一起留下的。"]),
  guardian: Object.freeze(["这页成果我替你守得好好的。", "这次闭环我一直替你记着。"]),
  chatty: Object.freeze(["我还记得那天英语响起来的样子。", "这页一翻开，我就想听你再说一次。"]),
  gentle: Object.freeze(["那天慢慢完成的样子很好。", "这页很轻，但每一步都算数。"]),
  adventurous: Object.freeze(["那天我们又探索出一小段新路。", "这页是一次很像样的小冒险。"]),
  balanced: Object.freeze(["这页把认真走过的一步留住了。", "我记得这一天的学习节奏。"]),
});

function stableIndex(seed, size) {
  let hash = 2166136261;
  for (const char of String(seed || "")) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return size > 0 ? (hash >>> 0) % size : 0;
}

function memoryVisitDay(memory) {
  return memory.reviewDueToday
    ? memory.recentDays.find((day) => day.date === memory.suggestedReviewDate)
      || memory.recentDays[0]
    : memory.recentDays[0];
}

function memoryVisitSentence(memory) {
  if (memory.reviewedToday && memory.todayRecallWord) {
    return `今天刚找回的 ${memory.todayRecallWord}，我想再悄悄念一次。`;
  }
  const latest = memoryVisitDay(memory) || {};
  const dayLabel = latest.dayLabel || formatCatWorldLearningMemoryDate(latest.date || memory.latestDate);
  const prefix = dayLabel ? `我想翻翻我们 ${dayLabel} 的那一页` : "我想翻翻我们的共同学习手册";
  if (memory.reviewDueToday) {
    return `${prefix}，今天正好到了${latest.reviewStageLabel || "回想"}的时间。`;
  }
  const endings = {
    loop: "，那天把词汇和表达好好接在一起了。",
    "warmup-output": "，那天既练了词，也把英语用出来了。",
    warmup: "，那天认真完成了词汇热身。",
    output: "，那天勇敢地用英语表达了。",
    started: "，那天留下了一枚起步爪印。",
  };
  return `${prefix}${endings[latest.statusKey] || "，看看我们一起走过的学习脚印。"}`;
}

function compactMemorySentence(sentence, maxLength = 68) {
  const value = String(sentence || "").replace(/\s+/g, " ").trim();
  if (value.length <= maxLength) return value;
  const clipped = value.slice(0, maxLength + 1);
  const wordBoundary = clipped.lastIndexOf(" ");
  return `${clipped.slice(0, wordBoundary >= Math.floor(maxLength * 0.62) ? wordBoundary : maxLength).trim()}...`;
}

function memoryTreasureWordCount(treasure) {
  return String(treasure.sentence || "").match(RECALL_SENTENCE_WORD_PATTERN)?.length || 0;
}

function memoryTreasureReviewDate(treasure) {
  return String(treasure.reviewDate || treasure.sourceDate || "9999-12-31");
}

function compareMemoryTreasures(left, right, styleKey) {
  if (styleKey === "gentle-starter") {
    return memoryTreasureWordCount(left) - memoryTreasureWordCount(right)
      || left.sentence.length - right.sentence.length;
  }
  if (styleKey === "story-builder") {
    return memoryTreasureWordCount(right) - memoryTreasureWordCount(left)
      || right.sentence.length - left.sentence.length;
  }
  if (styleKey === "idea-sparring") {
    return left.reviewCount - right.reviewCount
      || right.word.length - left.word.length;
  }
  if (styleKey === "loop-keeper") {
    return String(left.sourceDate || "9999-12-31").localeCompare(String(right.sourceDate || "9999-12-31"))
      || left.reviewCount - right.reviewCount;
  }
  if (styleKey === "streak-keeper") {
    return right.reviewCount - left.reviewCount
      || memoryTreasureReviewDate(right).localeCompare(memoryTreasureReviewDate(left));
  }
  if (styleKey === "review-organizer") {
    return left.reviewCount - right.reviewCount
      || memoryTreasureReviewDate(left).localeCompare(memoryTreasureReviewDate(right));
  }
  return 0;
}

function memoryVisitTreasure(memory, catId, sceneId, memoryToken, styleKey) {
  const hiddenSourceDate = memory.reviewDueToday ? memory.suggestedReviewDate : "";
  const visibleTreasures = memory.recallTreasures.filter(
    (treasure) => !hiddenSourceDate || treasure.sourceDate !== hiddenSourceDate,
  );
  if (!visibleTreasures.length) return null;

  const todayKey = String(memory.todayRecallWord || "").toLocaleLowerCase("en-US");
  if (memory.reviewedToday && todayKey) {
    const todayTreasure = visibleTreasures.find((treasure) => treasure.key.toLocaleLowerCase("en-US") === todayKey);
    if (todayTreasure) return { treasure: todayTreasure, selectionLabel: "今日新记" };
  }

  const rankedTreasures = visibleTreasures
    .map((treasure) => ({
      treasure,
      tieRank: stableIndex(
        `${catId}:${sceneId}:${memoryToken}:${treasure.key}:word-treasure`,
        0x100000000,
      ),
    }))
    .sort((left, right) => (
      compareMemoryTreasures(left.treasure, right.treasure, styleKey)
      || left.tieRank - right.tieRank
    ));
  return {
    treasure: rankedTreasures[0].treasure,
    selectionLabel: MEMORY_TREASURE_SELECTION_LABELS[styleKey] || MEMORY_TREASURE_SELECTION_LABELS.balanced,
  };
}

function memoryVisitTone(cat, memoryToken) {
  const temperament = String(cat.traits?.temperament || cat.temperament || "balanced");
  const tonePool = MEMORY_VISIT_TONES[temperament] || MEMORY_VISIT_TONES.balanced;
  const catId = String(cat.id || cat.profileId || cat.nickname || cat.label || "cat");
  return tonePool[stableIndex(`${catId}:${memoryToken}:memory-visit-tone`, tonePool.length)];
}

function memoryTreasureVisitCopy(memory, treasure, cat, styleKey, selectionLabel) {
  const ritual = MEMORY_VISIT_RITUALS[styleKey] || MEMORY_VISIT_RITUALS.balanced;
  const sentence = compactMemorySentence(treasure.sentence, 54);
  const recalledToday = treasure.word.toLocaleLowerCase("en-US")
    === memory.todayRecallWord.toLocaleLowerCase("en-US");
  const lead = memory.reviewedToday && recalledToday
    ? ritual.todayLead(treasure.word)
    : ritual.regularLead(treasure.word);
  return {
    message: `${selectionLabel}。${lead}${sentence} ${memoryVisitTone(cat, treasure.key)}`,
    ritualLabel: ritual.label,
    statusLabel: `${ritual.statusVerb} ${treasure.word}`,
  };
}

function memoryPageVisitCopy(memory, cat, styleKey, memoryToken) {
  const ritual = MEMORY_VISIT_RITUALS[styleKey] || MEMORY_VISIT_RITUALS.balanced;
  return {
    message: `${memoryVisitSentence(memory)} ${memoryVisitTone(cat, memoryToken)}`,
    ritualLabel: ritual.label,
    statusLabel: ritual.memoryStatus,
  };
}

export function catWorldLearningMemoryReflection(day = {}, cat = {}) {
  const normalizedDay = normalizeMemoryDay(day);
  const statusKey = normalizedDay.statusKey;
  const copy = MEMORY_REFLECTION_COPY[statusKey] || MEMORY_REFLECTION_COPY.started;
  const temperament = String(cat.traits?.temperament || cat.temperament || "balanced");
  const tonePool = MEMORY_REFLECTION_TONES[temperament] || MEMORY_REFLECTION_TONES.balanced;
  const catId = String(cat.id || cat.profileId || cat.nickname || cat.label || "cat");
  const catName = String(cat.nickname || cat.displayLabel || cat.label || cat.breedLabel || "猫咪");
  const tone = tonePool[stableIndex(`${catId}:${normalizedDay.date}:${statusKey}:reflection`, tonePool.length)];
  const preferredOutput = cat.learningStyle?.preferredOutput === "debate" ? "debate" : "essay";
  const outputAction = preferredOutput === "debate"
    ? { actionLabel: "说一个新理由", href: "/debate" }
    : { actionLabel: "写一句新表达", href: "/essays" };
  const action = ["warmup-output", "loop"].includes(statusKey) ? outputAction : copy;
  const styleLabel = String(cat.learningStyle?.label || "").trim();
  return {
    date: normalizedDay.date,
    dateLabel: normalizedDay.dayLabel || formatCatWorldLearningMemoryDate(normalizedDay.date),
    statusKey,
    statusLabel: normalizedDay.statusLabel,
    achievement: copy.achievement,
    reviewPrompt: copy.reviewPrompt,
    actionLabel: action.actionLabel,
    href: action.href,
    catName,
    catMessage: `${tone}${styleLabel ? ` 我还记得我们用的是“${styleLabel}”。` : ""}`,
  };
}

function normalizeMemoryStage(stage = {}, memoryPoints = 0, levelKey = "waiting") {
  const key = String(stage.key || "");
  const threshold = safeCount(stage.threshold);
  return {
    key,
    label: String(stage.label || key || "陪学印章"),
    threshold,
    unlocked: Boolean(stage.unlocked || memoryPoints >= threshold),
    current: Boolean(stage.current || key === levelKey),
  };
}

function normalizeMemoryDay(day = {}) {
  const statusKey = MEMORY_DAY_KEYS.has(String(day.statusKey)) ? String(day.statusKey) : "started";
  const reviewStageKey = MEMORY_REVIEW_STAGE_KEYS.has(String(day.reviewStageKey))
    ? String(day.reviewStageKey)
    : "first";
  return {
    date: String(day.date || ""),
    dayLabel: String(day.dayLabel || formatCatWorldLearningMemoryDate(day.date)),
    statusKey,
    statusLabel: String(day.statusLabel || "留下学习足迹"),
    milestones: Array.isArray(day.milestones) ? day.milestones.map(String) : [],
    reviewCount: safeCount(day.reviewCount),
    reviewStageKey,
    reviewStageLabel: String(day.reviewStageLabel || (reviewStageKey === "settled" ? "已经稳固" : "隔日回想")),
    reviewProgressLabel: String(day.reviewProgressLabel || `${Math.min(safeCount(day.reviewCount), 2)}/2`),
    reviewDue: Boolean(day.reviewDue),
    reviewedToday: Boolean(day.reviewedToday),
    lastReviewDate: String(day.lastReviewDate || ""),
    nextReviewDate: String(day.nextReviewDate || ""),
    latestRecallWord: String(day.latestRecallWord || "").trim(),
    latestRecallSentence: String(day.latestRecallSentence || "").trim(),
  };
}

function normalizeRecallTreasure(treasure = {}) {
  const word = String(treasure.word || "").trim();
  const sentence = String(treasure.sentence || "").trim();
  return {
    key: String(treasure.key || word.toLocaleLowerCase("en-US")).trim(),
    word,
    sentence,
    sourceDate: String(treasure.sourceDate || ""),
    reviewDate: String(treasure.reviewDate || ""),
    reviewCount: Math.max(safeCount(treasure.reviewCount), 1),
  };
}

export function catWorldLearningRecallDraft(rawWord = "", rawSentence = "") {
  const word = String(rawWord || "").replace(/\s+/g, " ").trim();
  const sentence = String(rawSentence || "").replace(/\s+/g, " ").trim();
  const sentenceWordCount = sentence.match(RECALL_SENTENCE_WORD_PATTERN)?.length || 0;
  const wordReady = word.length <= 48 && RECALL_WORD_PATTERN.test(word);
  const sentenceReady = sentence.length <= 240 && sentenceWordCount >= 3;
  return {
    word,
    sentence,
    wordReady,
    sentenceReady,
    sentenceWordCount,
    ready: wordReady && sentenceReady,
  };
}

export function normalizeCatWorldLearningMemory(memory = {}) {
  const companionDays = safeCount(memory.companionDays);
  const loopDays = Math.min(safeCount(memory.loopDays), companionDays);
  const memoryPoints = Math.max(safeCount(memory.memoryPoints), companionDays + loopDays);
  const levelCount = Math.max(safeCount(memory.levelCount), 1);
  const levelIndex = Math.min(safeCount(memory.levelIndex), levelCount - 1);
  const levelKey = String(memory.levelKey || (companionDays ? "starter" : "waiting"));
  const stageSource = Array.isArray(memory.stages) && memory.stages.length
    ? memory.stages
    : DEFAULT_MEMORY_STAGES;
  const stages = stageSource
    .map((stage) => normalizeMemoryStage(stage, memoryPoints, levelKey))
    .filter((stage) => stage.key && stage.key !== "waiting");
  const recentDays = Array.isArray(memory.recentDays)
    ? memory.recentDays.map(normalizeMemoryDay).filter((day) => day.date).slice(0, 6)
    : [];
  const recallTreasures = Array.isArray(memory.recallTreasures)
    ? memory.recallTreasures
      .map(normalizeRecallTreasure)
      .filter((treasure) => treasure.key && treasure.word && treasure.sentence)
      .slice(0, 8)
    : [];
  return {
    hasMemory: Boolean(memory.hasMemory || companionDays),
    companionDays,
    startedDays: Math.min(safeCount(memory.startedDays), companionDays),
    warmupDays: Math.min(safeCount(memory.warmupDays), companionDays),
    outputDays: Math.min(safeCount(memory.outputDays), companionDays),
    loopDays,
    memoryPoints,
    levelKey,
    levelLabel: String(memory.levelLabel || (companionDays ? "起步搭子" : "等待初次陪学")),
    levelIndex,
    levelCount,
    progressPercent: clamp(memory.progressPercent, 0, 100),
    nextLevelLabel: String(memory.nextLevelLabel || ""),
    nextLevelPoints: safeCount(memory.nextLevelPoints),
    nextRemaining: safeCount(memory.nextRemaining),
    firstDate: String(memory.firstDate || ""),
    latestDate: String(memory.latestDate || ""),
    reviewCount: safeCount(memory.reviewCount),
    recallTreasureCount: Math.max(safeCount(memory.recallTreasureCount), recallTreasures.length),
    recallTreasures,
    reviewedToday: Boolean(memory.reviewedToday),
    todayRecallWord: String(memory.todayRecallWord || "").trim(),
    todayRecallSentence: String(memory.todayRecallSentence || "").trim(),
    todayReviewSourceDate: String(memory.todayReviewSourceDate || ""),
    lastReviewDate: String(memory.lastReviewDate || ""),
    lastReviewSourceDate: String(memory.lastReviewSourceDate || ""),
    reviewDueToday: Boolean(memory.reviewDueToday),
    suggestedReviewDate: String(memory.suggestedReviewDate || ""),
    suggestedReviewStageLabel: String(memory.suggestedReviewStageLabel || ""),
    nextReviewDate: String(memory.nextReviewDate || ""),
    stages,
    recentDays,
  };
}

export function catWorldLearningMemoryDefaultDate(memory = {}) {
  const normalized = normalizeCatWorldLearningMemory(memory);
  const visibleDates = new Set(normalized.recentDays.map((day) => day.date));
  if (normalized.reviewedToday && visibleDates.has(normalized.todayReviewSourceDate)) {
    return normalized.todayReviewSourceDate;
  }
  if (normalized.reviewDueToday && visibleDates.has(normalized.suggestedReviewDate)) {
    return normalized.suggestedReviewDate;
  }
  return normalized.recentDays[0]?.date || "";
}

export function formatCatWorldLearningMemoryDate(value = "") {
  const match = String(value).match(/^\d{4}-(\d{2})-(\d{2})$/);
  if (!match) return "";
  return `${Number(match[1])}月${Number(match[2])}日`;
}

export function catWorldLearningMemoryLine(memory = {}) {
  const normalized = normalizeCatWorldLearningMemory(memory);
  if (!normalized.hasMemory) return "还没有一起留下学习记忆";
  return `${normalized.levelLabel} · 陪学 ${normalized.companionDays} 天 · 闭环 ${normalized.loopDays} 次`;
}

export function catWorldLearningMemoryNextLine(memory = {}) {
  const normalized = normalizeCatWorldLearningMemory(memory);
  if (!normalized.nextLevelLabel) return "已经获得最高陪学称号";
  return `再积累 ${normalized.nextRemaining} 点陪学记忆，成为${normalized.nextLevelLabel}`;
}

export function catWorldLearningMemoryRoomCue(memory = {}, complete = false) {
  const normalized = normalizeCatWorldLearningMemory(memory);
  if (!normalized.hasMemory) return "这是我们第一次一起留下学习记忆。";
  if (complete && normalized.loopDays) {
    return `我们已经一起完成 ${normalized.loopDays} 次英语闭环，这次也好好记住了。`;
  }
  const treasureLine = normalized.recallTreasureCount
    ? `，手册里还珍藏着 ${normalized.recallTreasureCount} 个回想词`
    : "";
  const latestDate = formatCatWorldLearningMemoryDate(normalized.latestDate);
  if (latestDate) {
    return `我们的最新一页写在 ${latestDate}，已经一起学过 ${normalized.companionDays} 天${treasureLine}。`;
  }
  return `我记得我们已经一起学过 ${normalized.companionDays} 天${treasureLine}。`;
}

export function catWorldLearningMemoryVisitPlan(cat = {}, behavior = {}, context = {}) {
  const memory = normalizeCatWorldLearningMemory(cat.learningMemory);
  const catId = String(cat.id || "");
  const sceneId = String(context.sceneId || "main-room");
  const cycle = Math.max(Math.floor(Number(context.cycle || 0)), 1);
  const restThreshold = Math.max(Number(behavior.restThreshold || 34), 1);
  const energy = Math.max(Number(behavior.energy || 0), 0);
  const carePriority = Math.max(Number(context.carePriority || 0), 0);
  if (
    !catId
    || !memory.hasMemory
    || memory.companionDays < 2
    || !behavior.canWalk
    || behavior.sleeping
    || ["resting", "waking"].includes(String(behavior.key || ""))
    || energy < restThreshold + 14
    || carePriority >= 70
  ) {
    return null;
  }

  const cadence = memory.reviewDueToday ? 3 : memory.levelIndex >= 3 ? 3 : 4;
  const memoryToken = memory.suggestedReviewDate || memory.latestDate || `${memory.levelKey}:${memory.memoryPoints}`;
  const slot = stableIndex(`${catId}:${sceneId}:${memoryToken}:memory-visit`, cadence);
  if (cycle % cadence !== slot) return null;

  const requestedStyleKey = String(cat.learningStyle?.key || "balanced");
  const styleKey = MEMORY_VISIT_TARGETS[requestedStyleKey] ? requestedStyleKey : "balanced";
  const attention = Math.max(Math.min(Number(behavior.attention || 50), 100), 0);
  const visitDay = memoryVisitDay(memory) || {};
  const treasureChoice = memoryVisitTreasure(memory, catId, sceneId, memoryToken, styleKey);
  const treasure = treasureChoice?.treasure || null;
  const selectionLabel = treasureChoice?.selectionLabel || "";
  const visitCopy = treasure
    ? memoryTreasureVisitCopy(memory, treasure, cat, styleKey, selectionLabel)
    : memoryPageVisitCopy(memory, cat, styleKey, memoryToken);
  return {
    kind: "learning-memory",
    visitKey: `${sceneId}:${catId}:${memoryToken}`,
    targetItemIds: [...MEMORY_VISIT_TARGETS[styleKey]],
    message: visitCopy.message,
    animation: MEMORY_VISIT_ANIMATIONS[styleKey],
    styleKey,
    ritualLabel: visitCopy.ritualLabel,
    selectionLabel,
    levelKey: memory.levelKey,
    levelLabel: memory.levelLabel,
    dayLabel: visitDay.dayLabel || formatCatWorldLearningMemoryDate(visitDay.date || memory.latestDate),
    treasure,
    statusLabel: visitCopy.statusLabel,
    targetLabel: treasure ? `珍藏词 ${treasure.word} · ${selectionLabel}` : "共同学习手册",
    holdMs: 6400,
    priority: Math.max(
      Math.min(36 + memory.levelIndex * 4 + Math.round(attention / 20) + (memory.reviewDueToday ? 4 : 0), 62),
      38,
    ),
  };
}

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

function memoryVisitTreasure(memory, catId, sceneId, memoryToken) {
  const hiddenSourceDate = memory.reviewDueToday ? memory.suggestedReviewDate : "";
  const visibleTreasures = memory.recallTreasures.filter(
    (treasure) => !hiddenSourceDate || treasure.sourceDate !== hiddenSourceDate,
  );
  if (!visibleTreasures.length) return null;

  const todayKey = String(memory.todayRecallWord || "").toLocaleLowerCase("en-US");
  if (memory.reviewedToday && todayKey) {
    const todayTreasure = visibleTreasures.find((treasure) => treasure.key.toLocaleLowerCase("en-US") === todayKey);
    if (todayTreasure) return todayTreasure;
  }

  return visibleTreasures[
    stableIndex(`${catId}:${sceneId}:${memoryToken}:word-treasure`, visibleTreasures.length)
  ];
}

function memoryTreasureVisitSentence(memory, treasure) {
  const sentence = compactMemorySentence(treasure.sentence);
  const recalledToday = treasure.word.toLocaleLowerCase("en-US")
    === memory.todayRecallWord.toLocaleLowerCase("en-US");
  if (memory.reviewedToday && recalledToday) {
    return `今天刚找回的 ${treasure.word}，我还记得你写过：${sentence}`;
  }
  return `我在词牌上看见 ${treasure.word}，还记得你写过：${sentence}`;
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
  const treasure = memoryVisitTreasure(memory, catId, sceneId, memoryToken);
  return {
    kind: "learning-memory",
    visitKey: `${sceneId}:${catId}:${memoryToken}`,
    targetItemIds: [...MEMORY_VISIT_TARGETS[styleKey]],
    message: treasure ? memoryTreasureVisitSentence(memory, treasure) : memoryVisitSentence(memory),
    animation: MEMORY_VISIT_ANIMATIONS[styleKey],
    levelKey: memory.levelKey,
    levelLabel: memory.levelLabel,
    dayLabel: visitDay.dayLabel || formatCatWorldLearningMemoryDate(visitDay.date || memory.latestDate),
    treasure,
    statusLabel: treasure ? `正在回看 ${treasure.word}` : "正在回看学习脚印",
    targetLabel: treasure ? `珍藏词 ${treasure.word}` : "共同学习手册",
    holdMs: 6400,
    priority: Math.max(
      Math.min(36 + memory.levelIndex * 4 + Math.round(attention / 20) + (memory.reviewDueToday ? 4 : 0), 62),
      38,
    ),
  };
}

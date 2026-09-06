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

function stableIndex(seed, size) {
  let hash = 2166136261;
  for (const char of String(seed || "")) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return size > 0 ? (hash >>> 0) % size : 0;
}

function memoryVisitSentence(memory) {
  const latest = memory.recentDays[0] || {};
  const dayLabel = latest.dayLabel || formatCatWorldLearningMemoryDate(latest.date || memory.latestDate);
  const prefix = dayLabel ? `我想翻翻我们 ${dayLabel} 的那一页` : "我想翻翻我们的共同学习手册";
  const endings = {
    loop: "，那天把词汇和表达好好接在一起了。",
    "warmup-output": "，那天既练了词，也把英语用出来了。",
    warmup: "，那天认真完成了词汇热身。",
    output: "，那天勇敢地用英语表达了。",
    started: "，那天留下了一枚起步爪印。",
  };
  return `${prefix}${endings[latest.statusKey] || "，看看我们一起走过的学习脚印。"}`;
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
  return {
    date: String(day.date || ""),
    dayLabel: String(day.dayLabel || formatCatWorldLearningMemoryDate(day.date)),
    statusKey,
    statusLabel: String(day.statusLabel || "留下学习足迹"),
    milestones: Array.isArray(day.milestones) ? day.milestones.map(String) : [],
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
    stages,
    recentDays,
  };
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
  const latestDate = formatCatWorldLearningMemoryDate(normalized.latestDate);
  if (latestDate) {
    return `我们的最新一页写在 ${latestDate}，已经一起学过 ${normalized.companionDays} 天。`;
  }
  return `我记得我们已经一起学过 ${normalized.companionDays} 天。`;
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

  const cadence = memory.levelIndex >= 3 ? 3 : 4;
  const memoryToken = memory.latestDate || `${memory.levelKey}:${memory.memoryPoints}`;
  const slot = stableIndex(`${catId}:${sceneId}:${memoryToken}:memory-visit`, cadence);
  if (cycle % cadence !== slot) return null;

  const requestedStyleKey = String(cat.learningStyle?.key || "balanced");
  const styleKey = MEMORY_VISIT_TARGETS[requestedStyleKey] ? requestedStyleKey : "balanced";
  const attention = Math.max(Math.min(Number(behavior.attention || 50), 100), 0);
  return {
    kind: "learning-memory",
    visitKey: `${sceneId}:${catId}:${memoryToken}`,
    targetItemIds: [...MEMORY_VISIT_TARGETS[styleKey]],
    message: memoryVisitSentence(memory),
    animation: MEMORY_VISIT_ANIMATIONS[styleKey],
    levelKey: memory.levelKey,
    levelLabel: memory.levelLabel,
    dayLabel: memory.recentDays[0]?.dayLabel || formatCatWorldLearningMemoryDate(memory.latestDate),
    holdMs: 6400,
    priority: Math.max(Math.min(36 + memory.levelIndex * 4 + Math.round(attention / 20), 58), 38),
  };
}

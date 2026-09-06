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

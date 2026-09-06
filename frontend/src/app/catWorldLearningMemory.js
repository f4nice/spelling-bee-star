function safeCount(value) {
  return Math.max(Math.floor(Number(value) || 0), 0);
}

function clamp(value, min, max) {
  return Math.min(Math.max(Number(value) || 0, min), max);
}

export function normalizeCatWorldLearningMemory(memory = {}) {
  const companionDays = safeCount(memory.companionDays);
  const loopDays = Math.min(safeCount(memory.loopDays), companionDays);
  const memoryPoints = Math.max(safeCount(memory.memoryPoints), companionDays + loopDays);
  const levelCount = Math.max(safeCount(memory.levelCount), 1);
  const levelIndex = Math.min(safeCount(memory.levelIndex), levelCount - 1);
  return {
    hasMemory: Boolean(memory.hasMemory || companionDays),
    companionDays,
    startedDays: Math.min(safeCount(memory.startedDays), companionDays),
    warmupDays: Math.min(safeCount(memory.warmupDays), companionDays),
    outputDays: Math.min(safeCount(memory.outputDays), companionDays),
    loopDays,
    memoryPoints,
    levelKey: String(memory.levelKey || (companionDays ? "starter" : "waiting")),
    levelLabel: String(memory.levelLabel || (companionDays ? "起步搭子" : "等待初次陪学")),
    levelIndex,
    levelCount,
    progressPercent: clamp(memory.progressPercent, 0, 100),
    nextLevelLabel: String(memory.nextLevelLabel || ""),
    nextLevelPoints: safeCount(memory.nextLevelPoints),
    nextRemaining: safeCount(memory.nextRemaining),
    firstDate: String(memory.firstDate || ""),
    latestDate: String(memory.latestDate || ""),
  };
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
  return `我记得我们已经一起学过 ${normalized.companionDays} 天。`;
}

export const LITTER_MOOD_PENALTY_PER_PILE = 2;
export const LITTER_MOOD_PENALTY_MAX = 8;

export function litterMoodPenalty(count) {
  const normalized = Math.max(Math.floor(Number(count) || 0), 0);
  return Math.min(normalized * LITTER_MOOD_PENALTY_PER_PILE, LITTER_MOOD_PENALTY_MAX);
}

export function litterUseHint(item = {}, count = 0) {
  if (item.useType === "litter-clean") {
    return Number(count) > 0 ? "点击房间里的猫屎清理" : "有猫屎时点击使用";
  }
  if (item.useType === "litter-prevent") return "猫咪拉屎时自动使用";
  return "点击背包使用";
}

export function bathStatusLabel(hygiene = {}) {
  if (hygiene.needsBath) return `${Number(hygiene.daysSinceBath || 0)} 天没洗 · 已炸毛`;
  const daysUntilBath = Math.max(Number(hygiene.daysUntilBath || 0), 0);
  return `${Number(hygiene.daysSinceBath || 0)} 天前洗过 · ${daysUntilBath} 天后再洗`;
}

export function neglectCountdownLabel(neglect = {}) {
  if (neglect.escaped) return neglect.escapeLabel || "已经离家";
  if (!neglect.isWarning) return "体力和心情均安全";
  const hours = Math.max(Number(neglect.remainingHours || 0), 0);
  const days = Math.floor(hours / 24);
  const restHours = hours % 24;
  const remaining = days ? `${days} 天 ${restHours} 小时` : `${restHours} 小时`;
  return `${neglect.statusLabel || "需要照护"} · 约 ${remaining} 后可能离家`;
}

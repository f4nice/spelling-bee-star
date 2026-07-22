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
  if (item.useType === "litter-prevent") return "点击放进活动室，猫咪使用后消失";
  return "点击背包使用";
}

export function bathStatusLabel(hygiene = {}) {
  const accelerationHours = Math.max(Number(hygiene.bathAccelerationHours || 0), 0);
  const accelerationLabel = accelerationHours ? ` · 猫屎久置加速 ${accelerationHours} 小时` : "";
  if (hygiene.needsBath) return `${Number(hygiene.daysSinceBath || 0)} 天没洗 · 已炸毛${accelerationLabel}`;
  const daysUntilBath = Math.max(Number(hygiene.daysUntilBath || 0), 0);
  return `${Number(hygiene.daysSinceBath || 0)} 天前洗过 · ${daysUntilBath} 天后再洗${accelerationLabel}`;
}

export function litterBathAccelerationLabel(hygiene = {}) {
  if (Number(hygiene.count || 0) <= 0) return "";
  const litterAgeHours = Math.max(Number(hygiene.litterAgeHours || 0), 0);
  const accelerationHours = Math.max(Number(hygiene.bathAccelerationHours || 0), 0);
  if (accelerationHours) {
    return `最久已放 ${litterAgeHours} 小时 · 洗澡进度额外 +${accelerationHours} 小时`;
  }
  const graceHours = Math.max(Number(hygiene.bathGraceHours || 6), 1);
  return `最久已放 ${litterAgeHours} 小时 · 超过 ${graceHours} 小时会加速变脏`;
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

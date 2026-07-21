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

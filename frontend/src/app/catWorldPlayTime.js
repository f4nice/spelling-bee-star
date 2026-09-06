export function normalizePlayTimeSeconds(value) {
  const seconds = Number(value);
  return Number.isFinite(seconds) ? Math.max(Math.ceil(seconds), 0) : 0;
}

export function formatCatWorldPlayTime(value) {
  const seconds = normalizePlayTimeSeconds(value);
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

export function isCatWorldPlayTimeLocked(value) {
  return normalizePlayTimeSeconds(value) <= 0;
}

export function projectCatWorldPlayTime(playTime, syncedAt, now, active = true) {
  const remaining = normalizePlayTimeSeconds(playTime?.remainingSeconds);
  if (!active || remaining <= 0) return remaining;
  const elapsed = Math.max(Math.floor((Number(now) - Number(syncedAt)) / 1000), 0);
  return Math.max(remaining - elapsed, 0);
}

export function formatCatWorldPlayTimeTiers(playTime) {
  const tiers = Array.isArray(playTime?.tiers) ? playTime.tiers : [];
  if (!tiers.length) return "20 词起步 · 100 词进阶 · 200 词达成";
  return tiers
    .map((tier) => `${Math.max(Number(tier?.target || 0), 0)} 词 ${Math.max(Number(tier?.minutes || 0), 0)} 分钟`)
    .join(" · ");
}

export function formatCatWorldPlayTimeProgress(playTime) {
  const count = Math.max(Number(playTime?.spellingCount || 0), 0);
  const rewardMinutes = Math.max(Number(playTime?.rewardMinutes || 0), 0);
  const nextTarget = Math.max(Number(playTime?.nextTarget || 0), 0);
  const nextRewardMinutes = Math.max(Number(playTime?.nextRewardMinutes || 0), 0);
  const earnedMinutes = Math.max(Number(playTime?.baseEarnedSeconds || 0) / 60, 0);
  let label = `今日已解锁 ${Math.round(earnedMinutes)} 分钟`;
  if (nextTarget > 0) {
    label = earnedMinutes > 0
      ? `已解锁 ${Math.round(earnedMinutes)} 分钟 · 再拼 ${Math.max(nextTarget - count, 0)} 词升至 ${nextRewardMinutes} 分钟`
      : `再拼 ${Math.max(nextTarget - count, 0)} 词解锁 ${nextRewardMinutes} 分钟`;
  }
  return rewardMinutes > 0 ? `${label} · 奖励 +${rewardMinutes} 分钟` : label;
}

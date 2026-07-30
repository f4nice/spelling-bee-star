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

export function projectCatWorldPlayTime(playTime, syncedAt, now, active = true) {
  const remaining = normalizePlayTimeSeconds(playTime?.remainingSeconds);
  if (!active || remaining <= 0) return remaining;
  const elapsed = Math.max(Math.floor((Number(now) - Number(syncedAt)) / 1000), 0);
  return Math.max(remaining - elapsed, 0);
}

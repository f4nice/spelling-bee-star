function clamp(value, min, max) {
  return Math.min(Math.max(Number(value) || 0, min), max);
}

function stableHash(value = "") {
  let hash = 2166136261;
  for (const char of String(value || "")) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619) >>> 0;
  }
  return hash >>> 0;
}

export function normalizeCatWorldSceneMoves(moves = []) {
  if (!Array.isArray(moves)) return [];
  return moves
    .map((move) => ({
      catId: String(move?.catId || ""),
      catLabel: String(move?.catLabel || "猫咪"),
      fromSceneId: String(move?.fromSceneId || ""),
      fromSceneLabel: String(move?.fromSceneLabel || "别的房间"),
      toSceneId: String(move?.toSceneId || ""),
      toSceneLabel: String(move?.toSceneLabel || "新的房间"),
      period: String(move?.period || ""),
      reason: String(move?.reason || "想换个地方活动"),
      targetItemId: String(move?.targetItemId || ""),
      targetItemLabel: String(move?.targetItemLabel || ""),
      occurredAt: String(move?.occurredAt || ""),
      message: String(move?.message || ""),
    }))
    .filter((move) => move.catId && move.fromSceneId && move.toSceneId);
}

export function catWorldSceneMoveToken(move = {}) {
  return [
    move.catId,
    move.fromSceneId,
    move.toSceneId,
    move.occurredAt || move.period,
    move.message,
  ].join(":");
}

export function catWorldSceneMoveForScene(move = {}, sceneId = "") {
  if (move.toSceneId === sceneId) return "arrival";
  if (move.fromSceneId === sceneId) return "departure";
  return "remote";
}

export function catWorldSceneArrivalPlan(move = {}, destination = {}, bounds = {}, walkSpeed = 1) {
  const minX = Number(bounds.minX ?? 38);
  const maxX = Math.max(Number(bounds.maxX ?? 1148), minX);
  const minY = Number(bounds.minY ?? 312);
  const maxY = Math.max(Number(bounds.maxY ?? 490), minY);
  const targetX = clamp(destination.x, minX, maxX);
  const targetY = clamp(destination.y, minY, maxY);
  const entersFromLeft = stableHash(`${move.catId}:${move.fromSceneId}:${move.toSceneId}`) % 2 === 0;
  const startX = entersFromLeft ? minX : maxX;
  const startY = clamp(targetY + (stableHash(`${move.catId}:arrival-y`) % 33) - 16, minY, maxY);
  const distance = Math.hypot(targetX - startX, targetY - startY);
  const duration = clamp(Math.round((960 + distance * 1.15) / Math.max(Number(walkSpeed) || 1, 0.45)), 1150, 2800);
  return {
    startX,
    startY,
    targetX,
    targetY,
    duration,
    facing: targetX >= startX ? 1 : -1,
  };
}

export function catWorldSceneDeparturePlan(move = {}, origin = {}, bounds = {}, walkSpeed = 1) {
  const minX = Number(bounds.minX ?? 38);
  const maxX = Math.max(Number(bounds.maxX ?? 1148), minX);
  const minY = Number(bounds.minY ?? 312);
  const maxY = Math.max(Number(bounds.maxY ?? 490), minY);
  const startX = clamp(origin.x, minX, maxX);
  const startY = clamp(origin.y, minY, maxY);
  const leavesToLeft = stableHash(`${move.catId}:${move.fromSceneId}:${move.toSceneId}`) % 2 === 0;
  const targetX = leavesToLeft ? minX : maxX;
  const targetY = clamp(startY + (stableHash(`${move.catId}:departure-y`) % 29) - 14, minY, maxY);
  const distance = Math.hypot(targetX - startX, targetY - startY);
  const duration = clamp(Math.round((880 + distance * 1.08) / Math.max(Number(walkSpeed) || 1, 0.45)), 1050, 2700);
  return {
    startX,
    startY,
    targetX,
    targetY,
    duration,
    facing: targetX >= startX ? 1 : -1,
  };
}

export const CAT_SPOT_MEMORY_MAX_STRENGTH = 5;

const MEMORY_LEVEL_LABELS = Object.freeze([
  "",
  "初次记住",
  "有点熟悉",
  "常去看看",
  "熟门熟路",
  "自己的角落",
]);

function clamp(value, min, max) {
  return Math.min(Math.max(Number(value) || 0, min), max);
}

export function normalizeCatSpotMemory(position = {}) {
  const itemId = String(position?.memoryItemId || "").trim();
  if (!itemId) return { itemId: "", strength: 0 };
  return {
    itemId,
    strength: clamp(Math.round(Number(position?.memoryStrength || 1)), 1, CAT_SPOT_MEMORY_MAX_STRENGTH),
  };
}

export function nextCatSpotMemory(position = {}, placedItemId = "") {
  const itemId = String(placedItemId || "").trim();
  if (!itemId) return normalizeCatSpotMemory(position);
  const previous = normalizeCatSpotMemory(position);
  return {
    itemId,
    strength: previous.itemId === itemId
      ? clamp(previous.strength + 1, 1, CAT_SPOT_MEMORY_MAX_STRENGTH)
      : 1,
  };
}

export function catSpotMemorySummary(position = {}, itemLookup = {}) {
  const memory = normalizeCatSpotMemory(position);
  if (!memory.itemId) {
    return { ...memory, label: "", levelLabel: "" };
  }
  return {
    ...memory,
    label: String(itemLookup?.[memory.itemId]?.label || memory.itemId),
    levelLabel: MEMORY_LEVEL_LABELS[memory.strength] || MEMORY_LEVEL_LABELS[1],
  };
}

export function catSpotMemoryPriority(cat = {}, behavior = {}) {
  const memory = normalizeCatSpotMemory(cat.scenePosition);
  if (!memory.itemId) return 0;
  const temperament = String(behavior.temperament || cat.traits?.temperament || "balanced");
  const mood = clamp(behavior.mood ?? 55, 0, 100);
  const energy = clamp(behavior.energy ?? 55, 0, 100);
  const calmBonus = ["calm", "gentle", "quiet", "clingy"].includes(temperament) ? 7 : 0;
  const moodBonus = mood < 52 ? 7 : mood > 82 ? -3 : 0;
  const energyPenalty = energy < 38 ? 18 : energy < 52 ? 7 : 0;
  return clamp(43 + memory.strength * 7 + calmBonus + moodBonus - energyPenalty, 24, 84);
}

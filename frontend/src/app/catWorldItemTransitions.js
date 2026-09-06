function normalizeVisualItems(items = []) {
  if (!Array.isArray(items)) return [];
  const seen = new Set();
  return items
    .map((item) => ({
      id: String(item?.id || ""),
      kind: item?.kind === "toy" ? "toy" : "decor",
      label: String(item?.label || "物品"),
    }))
    .filter((item) => {
      if (!item.id || seen.has(item.id)) return false;
      seen.add(item.id);
      return true;
    });
}

function stableHash(value = "") {
  let hash = 2166136261;
  for (const char of String(value || "")) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619) >>> 0;
  }
  return hash >>> 0;
}

export function catWorldNewVisibleItemArrivals(previousItems = [], nextItems = [], options = {}) {
  if (!options.sameScene || options.interactionLocked) return [];
  const previousIds = new Set(normalizeVisualItems(previousItems).map((item) => item.id));
  return normalizeVisualItems(nextItems).filter((item) => !previousIds.has(item.id));
}

export function catWorldItemArrivalPlan(itemId = "", index = 0) {
  const hash = stableHash(itemId);
  return {
    delay: Math.min(Math.max(Number(index) || 0, 0), 6) * 85,
    duration: 520 + (hash % 4) * 45,
    lift: 24 + (hash % 13),
    startScale: 0.82 + (hash % 5) * 0.02,
    dustColor: [0xffef82, 0x7fffd4, 0xff8cad, 0x87d9ff][hash % 4],
  };
}

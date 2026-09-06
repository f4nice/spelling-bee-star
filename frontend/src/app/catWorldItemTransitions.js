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

const ITEM_DEPARTURE_REACTIONS = Object.freeze({
  calm: Object.freeze([
    "{item}收好了，我去安静看看别处。",
    "先让{item}休息，我也换个角落待着。",
  ]),
  gentle: Object.freeze([
    "{item}收起来也没关系，我慢慢去别处。",
    "我和{item}说过再见啦，去找个舒服地方。",
  ]),
  chatty: Object.freeze([
    "咦，{item}收起来啦？我要去告诉大家。",
    "{item}下班啦，我边走边讲今天的故事。",
  ]),
  guardian: Object.freeze([
    "{item}已经收纳，我继续巡房。",
    "确认{item}收好，我去检查下一个角落。",
  ]),
  clingy: Object.freeze([
    "{item}收起来啦，那我先跟着你。",
    "没有{item}也没事，我去你附近待着。",
  ]),
  adventurous: Object.freeze([
    "{item}先休息，我去找下一样好玩的。",
    "收好{item}，正好换一条新路线探险。",
  ]),
  balanced: Object.freeze([
    "{item}收好啦，我换个地方活动。",
    "和{item}玩完了，我继续逛逛房间。",
  ]),
});

export function catWorldItemDepartureReaction(cat = {}, behavior = {}, itemLabel = "物品") {
  const temperament = String(
    behavior?.temperament
    || cat?.traits?.temperament
    || "balanced",
  );
  const lines = ITEM_DEPARTURE_REACTIONS[temperament] || ITEM_DEPARTURE_REACTIONS.balanced;
  const identity = String(cat?.id || cat?.profileId || cat?.label || "cat");
  const label = String(itemLabel || "物品").trim().slice(0, 12) || "物品";
  return lines[stableHash(`${identity}:${label}:stored`) % lines.length].replace("{item}", label);
}

export function catWorldNewVisibleItemArrivals(previousItems = [], nextItems = [], options = {}) {
  if (!options.sameScene || options.interactionLocked) return [];
  const previousIds = new Set(normalizeVisualItems(previousItems).map((item) => item.id));
  return normalizeVisualItems(nextItems).filter((item) => !previousIds.has(item.id));
}

export function catWorldNewHiddenItemDepartures(previousItems = [], nextItems = [], options = {}) {
  if (!options.sameScene || options.interactionLocked) return [];
  const nextIds = new Set(normalizeVisualItems(nextItems).map((item) => item.id));
  return normalizeVisualItems(previousItems).filter((item) => !nextIds.has(item.id));
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

export function catWorldItemDeparturePlan(itemId = "", index = 0) {
  const hash = stableHash(itemId);
  return {
    delay: Math.min(Math.max(Number(index) || 0, 0), 6) * 70,
    duration: 500 + (hash % 4) * 45,
    lift: 46 + (hash % 19),
    drift: (hash % 17) - 8,
    targetScale: 0.34 + (hash % 4) * 0.03,
    dustColor: [0xffef82, 0x7fffd4, 0xff8cad, 0x87d9ff][hash % 4],
  };
}

export function catWorldItemArrivalFollower(candidates = [], itemId = "") {
  if (!Array.isArray(candidates)) return "";
  return candidates
    .map((candidate) => {
      const id = String(candidate?.id || "");
      const energy = Number(candidate?.energy || 0);
      const restThreshold = Number(candidate?.restThreshold || 34);
      const carePriority = Number(candidate?.carePriority || 0);
      const eligible = Boolean(
        id
        && candidate?.canWalk
        && !candidate?.sleeping
        && !["resting", "waking"].includes(String(candidate?.behaviorKey || ""))
        && !candidate?.busy
        && !candidate?.carried
        && energy >= restThreshold + 8
        && carePriority < 78
      );
      const score = (
        Number(candidate?.curiosity || 0) * 0.45
        + Number(candidate?.activityBias || 0) * 0.25
        + Number(candidate?.mood || 0) * 0.15
        + energy * 0.1
        + (stableHash(`${itemId}:${id}`) % 11)
      );
      return { id, eligible, score };
    })
    .filter((candidate) => candidate.eligible)
    .sort((left, right) => right.score - left.score || left.id.localeCompare(right.id))[0]?.id || "";
}

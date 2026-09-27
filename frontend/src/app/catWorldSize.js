const BREED_SIZE_SCALE = Object.freeze({
  mimi: 1,
  "british-shorthair": 1.08,
  ragdoll: 1.16,
  "maine-coon": 1.22,
  siamese: 0.86,
  "china-lihua": 0.98,
  "linqing-lion": 1.18,
  "jianzhou-cat": 1.04,
  "japanese-bobtail": 0.82,
  "turkish-van": 1.12,
  "turkish-angora": 0.93,
  "festival-moon": 0.88,
  "festival-osmanthus": 1.04,
  "festival-lantern": 1.14,
  "festival-maple": 0.98,
});

const SIZE_LABELS = Object.freeze({
  small: { label: "小只派", humor: "一溜烟就钻进纸箱" },
  medium: { label: "标准号", humor: "刚好一把抱住" },
  large: { label: "大只派", humor: "走过来像一朵移动的云" },
});

export const CAT_BODY_FLOOR_Y = 56;

function stableRatio(value) {
  let hash = 2166136261;
  for (const character of String(value || "")) {
    hash ^= character.codePointAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) / 4294967296;
}

function clamp(value, minimum, maximum) {
  return Math.min(Math.max(value, minimum), maximum);
}

export function catWorldSizeProfile(cat = {}) {
  const breedId = String(cat.breedId || cat.id || "mimi");
  const identity = cat.profileCode || cat.profileId || cat.id || breedId;
  const baseScale = BREED_SIZE_SCALE[breedId] || BREED_SIZE_SCALE.mimi;
  // Keep each individual stable, but let two cats of one breed feel a little different.
  const individualVariation = (stableRatio(`${identity}:body-size`) - 0.5) * 0.08;
  const scale = Math.round(clamp(baseScale + individualVariation, 0.78, 1.26) * 100) / 100;
  const sizeKey = scale <= 0.92 ? "small" : scale >= 1.12 ? "large" : "medium";
  return {
    breedId,
    scale,
    baselineY: -Math.round((scale - 1) * CAT_BODY_FLOOR_Y),
    sizeKey,
    ...SIZE_LABELS[sizeKey],
  };
}


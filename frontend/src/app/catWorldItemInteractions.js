export const CAT_WORLD_ITEM_INTERACTIONS = Object.freeze({
  "reading-lamp": Object.freeze({
    itemKind: "decor",
    behavior: "toggle-attract",
    label: "阅读台灯",
  }),
  "study-desk": Object.freeze({
    itemKind: "decor",
    behavior: "walk-and-jump",
    label: "英文书桌",
  }),
  "feather-wand": Object.freeze({
    itemKind: "toy",
    behavior: "pointer-follow",
    label: "逗猫棒",
  }),
});

export function itemInteractionFor(itemId, itemKind = "") {
  const interaction = CAT_WORLD_ITEM_INTERACTIONS[itemId] || null;
  if (!interaction || (itemKind && interaction.itemKind !== itemKind)) return null;
  return interaction;
}

export function catLikesItem(cat, itemId, itemKind) {
  const favoriteKey = itemKind === "toy" ? "favoriteToyIds" : "favoriteDecorIds";
  return Array.isArray(cat?.[favoriteKey]) && cat[favoriteKey].includes(itemId);
}

export function interactionMoveDuration(from = {}, to = {}, walkSpeed = 1, limits = {}) {
  const distance = Math.hypot(Number(to.x || 0) - Number(from.x || 0), Number(to.y || 0) - Number(from.y || 0));
  const speed = Math.max(Number(walkSpeed) || 1, 0.2);
  const minMs = Number(limits.minMs || 2600);
  const maxMs = Number(limits.maxMs || 9000);
  return Math.min(Math.max(Math.round((distance / (72 * speed)) * 1000), minMs), maxMs);
}

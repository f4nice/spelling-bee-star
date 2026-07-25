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
  "bubble-bathtub": Object.freeze({
    itemKind: "decor",
    behavior: "walk-and-bathe",
    label: "泡泡浴缸",
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

export function wandChaseJoinDecision({
  active = false,
  alreadyFollowing = false,
  canWalk = false,
} = {}) {
  if (!active) return "inactive";
  if (alreadyFollowing) return "following";
  if (!canWalk) return "resting";
  return "join";
}

export function interactionMoveDuration(from = {}, to = {}, walkSpeed = 1, limits = {}) {
  const distance = Math.hypot(Number(to.x || 0) - Number(from.x || 0), Number(to.y || 0) - Number(from.y || 0));
  const speed = Math.max(Number(walkSpeed) || 1, 0.2);
  const minMs = Number(limits.minMs || 2600);
  const maxMs = Number(limits.maxMs || 9000);
  return Math.min(Math.max(Math.round((distance / (72 * speed)) * 1000), minMs), maxMs);
}

export function floorDropPosition(pointer = {}, spec = {}, world = {}) {
  const width = Math.max(Number(spec.width) || 0, 0);
  const height = Math.max(Number(spec.height) || 0, 0);
  const worldWidth = Math.max(Number(world.width) || width, width);
  const floorTop = Number(world.floorTop) || 0;
  const floorBottom = Math.max(Number(world.floorBottom) || floorTop + height, floorTop + height);
  const border = Math.max(Number(world.border) || 0, 0);
  const focusX = Number(spec.focusX) || width / 2;
  const focusY = Number(spec.focusY) || height / 2;
  const minY = Math.max(floorTop - height, border);
  const maxY = Math.max(floorBottom - height, minY);
  return {
    x: Math.min(Math.max((Number(pointer.x) || 0) - focusX, border), Math.max(worldWidth - width - border, border)),
    y: Math.min(Math.max((Number(pointer.y) || 0) - focusY, minY), maxY),
  };
}

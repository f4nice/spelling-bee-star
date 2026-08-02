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

function windowPerchInteraction(label, catMessage, holdMs = 9500) {
  return Object.freeze({
    behavior: "perch",
    label,
    actionLabel: "放到窗台",
    catMessage,
    anchorX: 0.5,
    anchorY: 0.55,
    offsetX: -48,
    offsetY: 0,
    holdMs,
  });
}

export const CAT_WORLD_CAT_DROP_INTERACTIONS = Object.freeze({
  "study-desk": Object.freeze({
    behavior: "perch",
    label: "英文书桌",
    actionLabel: "跳上书桌",
    catMessage: "被放到书桌上啦，我在这里陪你学习。",
    anchorX: 0.5,
    anchorY: 0,
    offsetX: -48,
    offsetY: -48,
    holdMs: 9000,
  }),
  "bubble-bathtub": Object.freeze({
    behavior: "bathe",
    label: "泡泡浴缸",
    actionLabel: "放进浴缸",
    catMessage: "泡泡好多，洗得香香的。",
    anchorX: 0.5,
    anchorY: 0,
    offsetX: -48,
    offsetY: 66,
    holdMs: 6000,
  }),
  "window-hammock": Object.freeze({
    behavior: "nap",
    label: "窗边吊床",
    actionLabel: "放到吊床",
    catMessage: "吊床晃悠悠的，我想在这里眯一会儿。",
    anchorX: 0.5,
    anchorY: 0.55,
    offsetX: -48,
    offsetY: -24,
    holdMs: 10000,
  }),
  "felt-cat-bed": Object.freeze({
    behavior: "nap",
    label: "毛毡猫窝",
    actionLabel: "放进猫窝",
    catMessage: "猫窝软软的，我先团成一小团。",
    anchorX: 0.5,
    anchorY: 0.5,
    offsetX: -48,
    offsetY: -48,
    holdMs: 10000,
  }),
  "moon-cushion": Object.freeze({
    behavior: "nap",
    label: "月亮软垫",
    actionLabel: "放到软垫",
    catMessage: "软垫接住我啦，这里很舒服。",
    anchorX: 0.5,
    anchorY: 0.5,
    offsetX: -48,
    offsetY: -42,
    holdMs: 8500,
  }),
  "cloud-rug": Object.freeze({
    behavior: "roll",
    label: "云朵地毯",
    actionLabel: "放到地毯",
    catMessage: "云朵地毯软乎乎的，我要滚一圈。",
    anchorX: 0.5,
    anchorY: 0.5,
    offsetX: -48,
    offsetY: -48,
    holdMs: 8000,
  }),
  "sun-window": windowPerchInteraction("阳光窗台", "窗边暖暖的，我在这里晒一会儿太阳。"),
  "moon-window": windowPerchInteraction("月光窗台", "月亮挂在窗外，我想在这里安静看一会儿星星。", 10000),
  "rain-window": windowPerchInteraction("雨声窗台", "雨点轻轻敲着玻璃，我在这里听一会儿雨。", 10500),
  "garden-window": windowPerchInteraction("花园窗台", "窗外有花和蝴蝶，我要坐高一点认真观察。", 9500),
  "snow-window": windowPerchInteraction("雪景窗台", "外面在下雪，窗台里面暖暖的。", 11000),
  "sea-window": windowPerchInteraction("海风窗台", "远处有小帆船，我想坐在这里看看海。", 10500),
  "cat-climbing-tree": Object.freeze({
    behavior: "climb",
    label: "原木猫爬架",
    actionLabel: "放到猫爬架",
    catMessage: "一下就到了高处，我要巡视整个房间。",
    anchorX: 0.5,
    anchorY: 0.35,
    offsetX: -48,
    offsetY: -34,
    holdMs: 9000,
  }),
  "mini-fountain": Object.freeze({
    behavior: "drink",
    label: "循环饮水机",
    actionLabel: "放到饮水机旁",
    catMessage: "水在咕噜咕噜流，我来喝几口。",
    anchorX: 0.5,
    anchorY: 0.65,
    offsetX: -92,
    offsetY: -34,
    holdMs: 7000,
  }),
  "reading-lamp": Object.freeze({
    behavior: "read",
    label: "阅读台灯",
    actionLabel: "放到台灯旁",
    catMessage: "灯光刚刚好，我陪你安静读一会儿。",
    anchorX: 0.5,
    anchorY: 0.9,
    offsetX: -48,
    offsetY: -20,
    holdMs: 8500,
  }),
});

export function itemInteractionFor(itemId, itemKind = "") {
  const interaction = CAT_WORLD_ITEM_INTERACTIONS[itemId] || null;
  if (!interaction || (itemKind && interaction.itemKind !== itemKind)) return null;
  return interaction;
}

export function catDropInteractionFor(itemId) {
  return CAT_WORLD_CAT_DROP_INTERACTIONS[itemId] || null;
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

const TIMED_INTERACTION_LABELS = Object.freeze({
  "bubble-bathtub": "泡泡洗澡",
  "study-desk": "书桌陪读",
  "reading-lamp": "灯下陪读",
  "window-hammock": "吊床休息",
  "felt-cat-bed": "猫窝休息",
  "moon-cushion": "软垫休息",
  "cloud-rug": "地毯打滚",
  "cat-climbing-tree": "爬架巡视",
  "mini-fountain": "饮水时间",
  "sun-window": "窗边晒太阳",
  "moon-window": "窗边看月亮",
  "rain-window": "窗边听雨",
  "garden-window": "窗边看花",
  "snow-window": "窗边看雪",
  "sea-window": "窗边看海",
});

export function timedInteractionLabel(itemId, fallback = "互动中") {
  return TIMED_INTERACTION_LABELS[itemId] || fallback;
}

export function timedInteractionProgress(startedAt, endsAt, now = Date.now()) {
  const start = Number(startedAt) || 0;
  const end = Math.max(Number(endsAt) || start, start);
  const current = Math.min(Math.max(Number(now) || start, start), end);
  const duration = Math.max(end - start, 1);
  const remainingMs = Math.max(end - current, 0);
  return {
    progress: Math.min(Math.max((current - start) / duration, 0), 1),
    remainingMs,
    remainingSeconds: Math.ceil(remainingMs / 1000),
  };
}

export function catFloorDropPosition(pointer = {}, world = {}) {
  const worldWidth = Math.max(Number(world.width) || 100, 100);
  const floorTop = Number(world.floorTop) || 0;
  const floorBottom = Math.max(Number(world.floorBottom) || floorTop + 120, floorTop + 120);
  const minX = Math.max(Number(world.minX) || 38, 0);
  const maxX = Math.max(worldWidth - (Number(world.rightSpace) || 132), minX);
  const minY = floorTop + (Number(world.topSpace) || 42);
  const maxY = Math.max(floorBottom - (Number(world.bottomSpace) || 70), minY);
  return {
    x: Math.min(Math.max((Number(pointer.x) || 0) - 45, minX), maxX),
    y: Math.min(Math.max((Number(pointer.y) || 0) - 36, minY), maxY),
  };
}

export function catDecorDropPosition(interaction = {}, position = {}, spec = {}, world = {}) {
  const worldWidth = Math.max(Number(world.width) || Number(spec.width) || 100, 100);
  const floorBottom = Math.max(Number(world.floorBottom) || 520, 120);
  const minX = Math.max(Number(world.minX) || 38, 0);
  const maxX = Math.max(worldWidth - (Number(world.rightSpace) || 132), minX);
  const minY = Math.max(Number(world.minY) || 54, 0);
  const maxY = Math.max(floorBottom - (Number(world.bottomSpace) || 70), minY);
  const anchorX = Number.isFinite(Number(interaction.anchorX)) ? Number(interaction.anchorX) : 0.5;
  const anchorY = Number.isFinite(Number(interaction.anchorY)) ? Number(interaction.anchorY) : 0.5;
  return {
    x: Math.min(
      Math.max(
        Number(position.x || 0) + Number(spec.width || 0) * anchorX + Number(interaction.offsetX || 0),
        minX,
      ),
      maxX,
    ),
    y: Math.min(
      Math.max(
        Number(position.y || 0) + Number(spec.height || 0) * anchorY + Number(interaction.offsetY || 0),
        minY,
      ),
      maxY,
    ),
  };
}

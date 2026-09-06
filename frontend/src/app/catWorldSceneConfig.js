const DEFAULT_WORLD = {
  width: 1600,
  height: 560,
  viewportWidth: 1280,
  viewportHeight: 560,
  floorTop: 260,
  floorBottom: 522,
};

const DEFAULT_PALETTE = {
  wallTopLeft: "#cff7ee",
  wallTopRight: "#fff0d0",
  wallBottomLeft: "#9be4ff",
  wallBottomRight: "#ffd7e7",
  floor: "#c29258",
  trim: "#6bc579",
  grid: "#2c2f3a",
};

function finiteNumber(value, fallback, min, max) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(Math.max(parsed, min), max);
}

function stringList(value) {
  return Array.isArray(value) ? value.map((item) => String(item || "").trim()).filter(Boolean) : [];
}

export function normalizeCatWorldScene(scene = {}) {
  const world = scene?.world || {};
  const width = finiteNumber(world.width, DEFAULT_WORLD.width, 960, 6000);
  const height = finiteNumber(world.height, DEFAULT_WORLD.height, 420, 1600);
  const viewportWidth = finiteNumber(world.viewportWidth, DEFAULT_WORLD.viewportWidth, 720, width);
  const viewportHeight = finiteNumber(world.viewportHeight, DEFAULT_WORLD.viewportHeight, 420, height);
  const floorTop = finiteNumber(world.floorTop, DEFAULT_WORLD.floorTop, 100, height - 140);
  const floorBottom = finiteNumber(world.floorBottom, DEFAULT_WORLD.floorBottom, floorTop + 120, height - 20);
  const itemRules = scene?.itemRules || {};
  const camera = scene?.camera || {};
  const pageWidth = finiteNumber(camera.pageWidth, viewportWidth, 320, width);
  const initialPage = Math.max(Math.floor(Number(camera.initialPage) || 0), 0);

  return {
    id: String(scene?.id || "main-room"),
    label: String(scene?.label || "一楼活动室"),
    englishName: String(scene?.englishName || "Main Room"),
    type: String(scene?.type || "indoor"),
    description: String(scene?.description || ""),
    enabled: scene?.enabled !== false,
    available: scene?.available !== false,
    unlocked: scene?.unlocked !== false,
    purchasable: Boolean(scene?.purchasable),
    purchaseCost: Math.max(Number(scene?.purchaseCost) || 0, 0),
    world: { width, height, viewportWidth, viewportHeight, floorTop, floorBottom },
    camera: {
      pageWidth,
      initialPage,
      snapPaging: camera.snapPaging !== false,
    },
    palette: { ...DEFAULT_PALETTE, ...(scene?.palette || {}) },
    features: {
      cats: scene?.features?.cats !== false,
      food: scene?.features?.food !== false,
      care: scene?.features?.care !== false,
      hygiene: scene?.features?.hygiene !== false,
    },
    itemRules: {
      allowedCategories: stringList(itemRules.allowedCategories),
      allowedItemIds: stringList(itemRules.allowedItemIds),
      excludedItemIds: stringList(itemRules.excludedItemIds),
    },
    spawnPoints: scene?.spawnPoints && typeof scene.spawnPoints === "object" ? scene.spawnPoints : {},
    portals: Array.isArray(scene?.portals) ? scene.portals : [],
  };
}

export function sceneInitialScroll(scene, viewportOverride = 0) {
  const normalized = normalizeCatWorldScene(scene);
  const hasViewportOverride = Number.isFinite(Number(viewportOverride)) && Number(viewportOverride) > 0;
  const viewportWidth = hasViewportOverride
    ? finiteNumber(viewportOverride, normalized.world.viewportWidth, 240, normalized.world.width)
    : normalized.world.viewportWidth;
  const pageWidth = hasViewportOverride ? viewportWidth : normalized.camera.pageWidth;
  const maxScroll = Math.max(normalized.world.width - viewportWidth, 0);
  return Math.min(normalized.camera.initialPage * pageWidth, maxScroll);
}

export function scenePageTarget(scene, currentScroll = 0, direction = 1, viewportOverride = 0) {
  const normalized = normalizeCatWorldScene(scene);
  const hasViewportOverride = Number.isFinite(Number(viewportOverride)) && Number(viewportOverride) > 0;
  const viewportWidth = hasViewportOverride
    ? finiteNumber(viewportOverride, normalized.world.viewportWidth, 240, normalized.world.width)
    : normalized.world.viewportWidth;
  const pageWidth = hasViewportOverride ? viewportWidth : normalized.camera.pageWidth;
  const maxScroll = Math.max(normalized.world.width - viewportWidth, 0);
  const scroll = finiteNumber(currentScroll, 0, 0, maxScroll);
  const currentPage = Math.round(scroll / pageWidth);
  const nextPage = Math.max(currentPage + Math.sign(Number(direction) || 0), 0);
  return Math.min(nextPage * pageWidth, maxScroll);
}

export function catWorldResponsiveViewportWidth(scene, renderedWidth = 0) {
  const configuredWidth = normalizeCatWorldScene(scene).world.viewportWidth;
  const availableWidth = Number(renderedWidth);
  if (!Number.isFinite(availableWidth) || availableWidth <= 0 || availableWidth > 560) {
    return configuredWidth;
  }
  return Math.min(configuredWidth, 480);
}

export function sceneAllowsItem(scene, itemId, category) {
  const normalized = normalizeCatWorldScene(scene);
  const rules = normalized.itemRules;
  if (rules.excludedItemIds.includes(itemId)) return false;
  if (rules.allowedItemIds.length && !rules.allowedItemIds.includes(itemId)) return false;
  return !rules.allowedCategories.length || rules.allowedCategories.includes(category);
}

export function sceneColor(value, fallback) {
  const raw = String(value || "").trim();
  if (!/^#[0-9a-f]{6}$/i.test(raw)) return fallback;
  return Number.parseInt(raw.slice(1), 16);
}

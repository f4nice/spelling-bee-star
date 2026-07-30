const REGION_POSITIONS = Object.freeze({
  "猫咪世界": { x: 12, y: 13, shortLabel: "常驻" },
  中国: { x: 76, y: 43, shortLabel: "中国" },
  日本: { x: 87, y: 42, shortLabel: "日本" },
  土耳其: { x: 58, y: 39, shortLabel: "土耳其" },
});

const FALLBACK_POSITIONS = Object.freeze([
  { x: 26, y: 26 },
  { x: 40, y: 60 },
  { x: 68, y: 66 },
  { x: 84, y: 70 },
]);

export function collectionRegionMeta(section = {}, index = 0) {
  const region = String(section.region || section.label || "新地区");
  const fallback = FALLBACK_POSITIONS[Math.abs(index) % FALLBACK_POSITIONS.length];
  const position = REGION_POSITIONS[region] || fallback;
  return {
    region,
    shortLabel: position.shortLabel || region.slice(0, 4),
    x: position.x,
    y: position.y,
    style: {
      left: `${position.x}%`,
      top: `${position.y}%`,
    },
  };
}

export function resolveCollectionSection(sections = [], selectedKey = "", preferredRegion = "") {
  const rows = Array.isArray(sections) ? sections : [];
  return rows.find((section) => section.key === selectedKey)
    || rows.find((section) => section.region === preferredRegion)
    || rows[0]
    || {};
}

export function resolveCollectionCat(section = {}, selectedCatId = "") {
  const cats = Array.isArray(section.cats) ? section.cats : [];
  return cats.find((cat) => cat.id === selectedCatId) || cats[0] || {};
}

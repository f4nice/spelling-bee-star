const RARITY_BADGES = Object.freeze({
  starter: { label: "伙伴", tone: "starter" },
  "famous cat": { label: "名猫", tone: "famous" },
  r: { label: "R", tone: "r" },
  sr: { label: "SR", tone: "sr" },
  ssr: { label: "SSR", tone: "ssr" },
});

export function catRarityBadge(rarity = "") {
  const key = String(rarity || "").trim().toLowerCase();
  return RARITY_BADGES[key] || {
    label: String(rarity || "伙伴").trim().toUpperCase(),
    tone: "starter",
  };
}

const CAT_PORTRAIT_PALETTES = Object.freeze({
  mimi: { body: "#ffc46b", shade: "#d88a3d", stripe: "#7a4a28", belly: "#ffdf9f" },
  "british-shorthair": { body: "#b9c2c8", shade: "#7e8b95", stripe: "#4d5962", belly: "#dde4e8" },
  ragdoll: { body: "#f4e5cf", shade: "#b88663", stripe: "#79523f", belly: "#fff4df" },
  "maine-coon": { body: "#ae7c4f", shade: "#754926", stripe: "#f1c17f", belly: "#d6a06b" },
  siamese: { body: "#f1ddbd", shade: "#5c433e", stripe: "#382c2d", belly: "#ffefd2" },
  "china-lihua": { body: "#8b765f", shade: "#594739", stripe: "#2f2926", belly: "#c7b59d" },
  "linqing-lion": { body: "#f2eee5", shade: "#aab7c8", stripe: "#6f7f93", belly: "#ffffff" },
  "jianzhou-cat": { body: "#d6a06b", shade: "#79523f", stripe: "#382c2d", belly: "#f4d3a4" },
  "japanese-bobtail": { body: "#fff3dc", shade: "#d98745", stripe: "#3f3430", belly: "#ffffff" },
  "turkish-van": { body: "#fff4dc", shade: "#c96f3f", stripe: "#743c2a", belly: "#ffffff" },
  "turkish-angora": { body: "#f8fbff", shade: "#cad8e6", stripe: "#70849a", belly: "#ffffff" },
});

const PORTRAIT_BACKDROPS = ["#d9f6ff", "#fff0a6", "#ffe0ec", "#d8f5e8"];

function safeToken(value, fallback) {
  return String(value || fallback)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, "-")
    .replace(/^-+|-+$/g, "") || fallback;
}

function stableIndex(value, length) {
  return [...String(value || "")].reduce((total, character) => total + character.codePointAt(0), 0) % length;
}

export function catPortraitModel(cat = {}) {
  const breedId = safeToken(cat.breedId || cat.id, "mimi");
  const palette = CAT_PORTRAIT_PALETTES[breedId] || CAT_PORTRAIT_PALETTES.mimi;
  const identity = cat.profileCode || cat.id || breedId;
  return {
    pattern: safeToken(cat.patternKey, "classic"),
    feature: safeToken(cat.featureKey, "standard"),
    style: {
      "--cat-portrait-body": palette.body,
      "--cat-portrait-shade": palette.shade,
      "--cat-portrait-stripe": palette.stripe,
      "--cat-portrait-belly": palette.belly,
      "--cat-portrait-backdrop": PORTRAIT_BACKDROPS[stableIndex(identity, PORTRAIT_BACKDROPS.length)],
    },
  };
}

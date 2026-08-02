const ITEM_ICON_SPECS = Object.freeze({
  "daily-kibble": { icon: "soup", background: "#fff0ad", accent: "#c98227", detail: "#7a4a28" },
  "chicken-broth": { icon: "cooking-pot", background: "#ffe2bd", accent: "#d98558", detail: "#754926" },
  "egg-yolk-bites": { icon: "egg", background: "#fff5b8", accent: "#e9a51c", detail: "#8a5a16" },
  "salmon-bowl": { icon: "fish", background: "#ffd2c9", accent: "#ed765f", detail: "#8e3f35" },
  "tuna-can": { icon: "fish", background: "#cceeff", accent: "#4aa5cb", detail: "#285f79" },
  "goat-milk": { icon: "milk", background: "#f2dcff", accent: "#a768c4", detail: "#654175" },
  "silver-cod-stew": { icon: "cooking-pot", background: "#e7eef2", accent: "#8797a3", detail: "#4d5962" },
  "chicken-star-bites": { icon: "star", background: "#ffe1ad", accent: "#e78a35", detail: "#874719" },
  "litter-scoop": { icon: "shovel", background: "#c9f5e8", accent: "#238a70", detail: "#155f50" },
  "tofu-cat-litter": { icon: "package", background: "#e7f1d6", accent: "#79a74d", detail: "#46642d" },
  "grooming-brush": { icon: "brush-cleaning", background: "#ffe0ed", accent: "#d86291", detail: "#873955" },
  "care-wipes": { icon: "package-check", background: "#dff3ff", accent: "#3d9ac8", detail: "#285f79" },
  "cat-bath-kit": { icon: "bath", background: "#d9f6ff", accent: "#4aa5cb", detail: "#2b6680" },
  "room-deodorizer": { icon: "spray-can", background: "#e4dcff", accent: "#7d66c7", detail: "#4f4084" },
  "cat-grass-pot": { icon: "sprout", background: "#d9f4c6", accent: "#3b9b56", detail: "#256239" },
  "repair-hammer": { icon: "hammer", background: "#fff0ad", accent: "#d9853f", detail: "#754926" },
  "cat-rename-card": { icon: "contact-round", background: "#cfeeff", accent: "#3d91c3", detail: "#275b7d" },
  "rolling-ball": { icon: "circle-dot", background: "#ffe0ed", accent: "#d86291", detail: "#873955" },
  "feather-wand": { icon: "feather", background: "#e3dcff", accent: "#7d66c7", detail: "#4f4084" },
  "scratch-board": { icon: "rectangle-horizontal", background: "#f5dfbd", accent: "#b8773f", detail: "#754926" },
  "yarn-basket": { icon: "package-open", background: "#ffe2bd", accent: "#d96f78", detail: "#7e3f48" },
  "limited-gift-toy": { icon: "gift", background: "#fff0ad", accent: "#e85b83", detail: "#7e3f48" },
  "cloud-rug": { icon: "cloud", background: "#dff4ff", accent: "#56a9cf", detail: "#2d6882" },
  "sun-window": { icon: "sun", background: "#fff1a8", accent: "#e7a51b", detail: "#855f13" },
  "moon-window": { icon: "moon", background: "#dfe8ff", accent: "#6f82c7", detail: "#435182" },
  "rain-window": { icon: "cloud", background: "#d8ecf5", accent: "#4f91ad", detail: "#315f73" },
  "garden-window": { icon: "sprout", background: "#def4cc", accent: "#4f9d58", detail: "#2f6738" },
  "snow-window": { icon: "star", background: "#e9f7ff", accent: "#75b8d5", detail: "#3c7088" },
  "sea-window": { icon: "waves", background: "#d9f6ff", accent: "#3e9bc8", detail: "#285f79" },
  "book-shelf": { icon: "library", background: "#e9ddff", accent: "#8067bb", detail: "#514079" },
  "study-desk": { icon: "laptop", background: "#ffdce9", accent: "#c95c89", detail: "#7d3854" },
  "reading-lamp": { icon: "lamp-desk", background: "#fff0ad", accent: "#d99424", detail: "#805b13" },
  "word-gallery": { icon: "image", background: "#d9f6ff", accent: "#4a9ec7", detail: "#2d627a" },
  "window-hammock": { icon: "bed", background: "#e9ddff", accent: "#8a6cc6", detail: "#57447e" },
  "felt-cat-bed": { icon: "house", background: "#ffe0ed", accent: "#c95c89", detail: "#7d3854" },
  "moon-cushion": { icon: "moon", background: "#dfe8ff", accent: "#6f82c7", detail: "#435182" },
  "cat-climbing-tree": { icon: "trees", background: "#e6dbbf", accent: "#987047", detail: "#5e452d" },
  "mini-fountain": { icon: "waves", background: "#d9f6ff", accent: "#3e9bc8", detail: "#285f79" },
  "bubble-bathtub": { icon: "bath", background: "#dff5ff", accent: "#e47ca5", detail: "#87465f" },
});

const CATEGORY_ICON_SPECS = Object.freeze({
  food: { icon: "soup", background: "#fff0ad", accent: "#c98227", detail: "#7a4a28" },
  consumable: { icon: "package", background: "#d9f4e8", accent: "#238a70", detail: "#155f50" },
  toy: { icon: "circle-dot", background: "#ffe0ed", accent: "#d86291", detail: "#873955" },
  decor: { icon: "house", background: "#dff4ff", accent: "#4a9ec7", detail: "#2d627a" },
  color: { icon: "palette", background: "#ffe3ef", accent: "#c95c89", detail: "#7d3854" },
  cat: { icon: "cat", background: "#fff0c7", accent: "#b87838", detail: "#754926" },
  "blind-box": { icon: "package-open", background: "#fff0ad", accent: "#c98227", detail: "#7a4a28" },
  handbook: { icon: "book-open", background: "#d9f6ff", accent: "#3d91c3", detail: "#275b7d" },
});

const TONE_ACCENTS = Object.freeze({
  candy: "#ff6f9f",
  sky: "#4aa5cb",
  cherry: "#a94c4c",
  mint: "#3d9b78",
  lavender: "#8067bb",
  sunset: "#e47b55",
  moon: "#6f82c7",
  peach: "#df826a",
});

export function catWorldProductIconSpec(item = {}) {
  const category = String(item.category || "decor");
  const base = ITEM_ICON_SPECS[item.id] || CATEGORY_ICON_SPECS[category] || CATEGORY_ICON_SPECS.decor;
  const accent = category === "color" && item.tone ? TONE_ACCENTS[item.tone] || base.accent : base.accent;
  return {
    ...base,
    accent,
    category,
    itemId: String(item.id || "unknown-item"),
    label: String(item.label || item.englishName || "商品"),
  };
}

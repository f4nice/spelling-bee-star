function numeric(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function foodTypeLabel(item = {}) {
  return item.foodType === "specialty" ? "猫咪特色餐" : "基础口粮";
}

export function foodFavoriteMultiplier(item = {}, catId = "") {
  if (item.category !== "food" || !item.favoriteCatId || item.favoriteCatId !== catId) return 1;
  return Math.min(Math.max(numeric(item.favoriteEnergyMultiplier, 1.18), 1), 2);
}

export function foodEnergyGainForCat(item = {}, cat = {}) {
  const traitMultiplier = Math.max(numeric(cat?.traits?.foodEnergyGain, 1), 0);
  return Math.round(numeric(item.catEnergy) * traitMultiplier * foodFavoriteMultiplier(item, cat?.id));
}

export function foodMoodGainForCat(item = {}, cat = {}) {
  const traitMultiplier = Math.max(numeric(cat?.traits?.foodEnergyGain, 1), 0);
  return Math.round(numeric(item.mood) * traitMultiplier * foodFavoriteMultiplier(item, cat?.id));
}

export function foodFavoriteBonusPercent(item = {}) {
  if (!item.favoriteCatId) return 0;
  return Math.round((foodFavoriteMultiplier(item, item.favoriteCatId) - 1) * 100);
}

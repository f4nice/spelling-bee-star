import assert from "node:assert/strict";
import test from "node:test";

import {
  foodEnergyGainForCat,
  foodFavoriteBonusPercent,
  foodFavoriteMultiplier,
  foodTypeLabel,
} from "../src/app/catWorldFoodRules.js";

const cats = {
  british: { id: "british-shorthair", traits: { foodEnergyGain: 0.95 } },
  siamese: { id: "siamese", traits: { foodEnergyGain: 1.06 } },
};

test("basic food stays low and applies no cat-specific multiplier", () => {
  const food = { category: "food", foodType: "basic", catEnergy: 14 };

  assert.equal(foodTypeLabel(food), "基础口粮");
  assert.equal(foodFavoriteMultiplier(food, cats.british.id), 1);
  assert.equal(foodEnergyGainForCat(food, cats.british), 13);
  assert.equal(foodEnergyGainForCat(food, cats.siamese), 15);
});

test("specialty food boosts only its preferred cat", () => {
  const food = {
    category: "food",
    foodType: "specialty",
    catEnergy: 34,
    favoriteCatId: "british-shorthair",
    favoriteEnergyMultiplier: 1.45,
  };

  assert.equal(foodTypeLabel(food), "猫咪特色餐");
  assert.equal(foodFavoriteMultiplier(food, cats.british.id), 1.45);
  assert.equal(foodFavoriteMultiplier(food, cats.siamese.id), 1);
  assert.equal(foodFavoriteBonusPercent(food), 45);
  assert.equal(foodEnergyGainForCat(food, cats.british), 47);
  assert.equal(foodEnergyGainForCat(food, cats.siamese), 36);
});

import assert from "node:assert/strict";
import test from "node:test";

import { catWorldProductIconSpec } from "../src/app/catWorldProductIcons.js";

test("shop products use recognizable item-specific icons", () => {
  assert.equal(catWorldProductIconSpec({ id: "daily-kibble", category: "food" }).icon, "soup");
  assert.equal(catWorldProductIconSpec({ id: "salmon-bowl", category: "food" }).icon, "fish");
  assert.equal(catWorldProductIconSpec({ id: "repair-hammer", category: "consumable" }).icon, "hammer");
  assert.equal(catWorldProductIconSpec({ id: "litter-scoop", category: "consumable" }).icon, "shovel");
  assert.equal(catWorldProductIconSpec({ id: "cat-rename-card", category: "consumable" }).icon, "contact-round");
  assert.equal(catWorldProductIconSpec({ id: "window-hammock", category: "decor" }).icon, "bed");
  assert.equal(catWorldProductIconSpec({ id: "moon-window", category: "decor" }).icon, "moon");
  assert.equal(catWorldProductIconSpec({ id: "rain-window", category: "decor" }).icon, "cloud");
  assert.equal(catWorldProductIconSpec({ id: "garden-window", category: "decor" }).icon, "sprout");
  assert.equal(catWorldProductIconSpec({ id: "snow-window", category: "decor" }).icon, "star");
  assert.equal(catWorldProductIconSpec({ id: "sea-window", category: "decor" }).icon, "waves");
  assert.equal(catWorldProductIconSpec({ id: "bubble-bathtub", category: "decor" }).icon, "bath");
  assert.equal(catWorldProductIconSpec({ id: "limited-gift-toy", category: "toy" }).icon, "gift");
});

test("color products keep a target category icon with their selected tone", () => {
  const spec = catWorldProductIconSpec({ id: "desk-mint", category: "color", tone: "mint" });
  assert.equal(spec.icon, "palette");
  assert.equal(spec.accent, "#3d9b78");
});

test("new products receive a category fallback instead of the old generic swatch", () => {
  assert.equal(catWorldProductIconSpec({ id: "future-food", category: "food" }).icon, "soup");
  assert.equal(catWorldProductIconSpec({ id: "future-cat", category: "cat" }).icon, "cat");
});

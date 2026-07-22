import test from "node:test";
import assert from "node:assert/strict";

import {
  catLikesItem,
  interactionMoveDuration,
  itemInteractionFor,
} from "../src/app/catWorldItemInteractions.js";

test("interactive room items use the expected controlled behavior", () => {
  assert.equal(itemInteractionFor("reading-lamp", "decor")?.behavior, "toggle-attract");
  assert.equal(itemInteractionFor("study-desk", "decor")?.behavior, "walk-and-jump");
  assert.equal(itemInteractionFor("bubble-bathtub", "decor")?.behavior, "walk-and-bathe");
  assert.equal(itemInteractionFor("feather-wand", "toy")?.behavior, "pointer-follow");
  assert.equal(itemInteractionFor("feather-wand", "decor"), null);
});

test("favorite matching keeps toy and decor preferences separate", () => {
  const cat = {
    favoriteToyIds: ["feather-wand"],
    favoriteDecorIds: ["reading-lamp"],
  };

  assert.equal(catLikesItem(cat, "feather-wand", "toy"), true);
  assert.equal(catLikesItem(cat, "feather-wand", "decor"), false);
  assert.equal(catLikesItem(cat, "reading-lamp", "decor"), true);
});

test("interaction movement stays slow but clamps very short and long trips", () => {
  assert.equal(interactionMoveDuration({ x: 0, y: 0 }, { x: 1, y: 1 }, 1), 2600);
  assert.equal(interactionMoveDuration({ x: 0, y: 0 }, { x: 2000, y: 0 }, 0.2), 9000);
  assert.equal(interactionMoveDuration({ x: 0, y: 0 }, { x: 360, y: 0 }, 1), 5000);
});

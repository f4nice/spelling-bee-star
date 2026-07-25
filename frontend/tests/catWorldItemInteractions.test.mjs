import test from "node:test";
import assert from "node:assert/strict";

import {
  catLikesItem,
  floorDropPosition,
  interactionMoveDuration,
  itemInteractionFor,
  wandChaseJoinDecision,
} from "../src/app/catWorldItemInteractions.js";

test("interactive room items use the expected controlled behavior", () => {
  assert.equal(itemInteractionFor("reading-lamp", "decor")?.behavior, "toggle-attract");
  assert.equal(itemInteractionFor("study-desk", "decor")?.behavior, "walk-and-jump");
  assert.equal(itemInteractionFor("bubble-bathtub", "decor")?.behavior, "walk-and-bathe");
  assert.equal(itemInteractionFor("feather-wand", "toy")?.behavior, "pointer-follow");
  assert.equal(itemInteractionFor("feather-wand", "decor"), null);
});

test("floor drop positions a held toy around the clicked floor point", () => {
  assert.deepEqual(
    floorDropPosition(
      { x: 1500, y: 400 },
      { width: 172, height: 70, focusX: 88, focusY: 52 },
      { width: 2560, floorTop: 260, floorBottom: 522, border: 12 },
    ),
    { x: 1412, y: 348 },
  );
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

test("cats can join an active feather wand chase without duplicate followers", () => {
  assert.equal(wandChaseJoinDecision({ active: false, canWalk: true }), "inactive");
  assert.equal(wandChaseJoinDecision({ active: true, alreadyFollowing: true, canWalk: true }), "following");
  assert.equal(wandChaseJoinDecision({ active: true, alreadyFollowing: false, canWalk: false }), "resting");
  assert.equal(wandChaseJoinDecision({ active: true, alreadyFollowing: false, canWalk: true }), "join");
});

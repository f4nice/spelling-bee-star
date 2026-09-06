import assert from "node:assert/strict";
import test from "node:test";

import { readFile } from "node:fs/promises";
import { catWorldPlacementReactionPlan } from "../src/app/catWorldPlacementReaction.js";

test("placement copy combines each cat's temperament with its daily mood", () => {
  const guardian = catWorldPlacementReactionPlan(
    { id: "cat-guardian-1", traits: { temperament: "guardian" } },
    { temperament: "guardian", dailyMoodKey: "curious" },
    { targetType: "floor" },
  );
  const clingy = catWorldPlacementReactionPlan(
    { id: "cat-clingy-1", traits: { temperament: "clingy" } },
    { temperament: "clingy", dailyMoodKey: "curious" },
    { targetType: "floor" },
  );

  assert.equal(guardian.source, "daily-mood+temperament");
  assert.match(guardian.message, /^我正想探索，/);
  assert.match(guardian.message, /(巡|观察|守)/);
  assert.match(clingy.message, /(等你|离你|跟着)/);
  assert.notEqual(guardian.message, clingy.message);
});

test("favorite furniture changes the same cat's response and landing style", () => {
  const cat = { id: "cat-window-4b3e", traits: { temperament: "gentle" } };
  const target = { targetType: "decor", itemId: "sun-window", itemLabel: "阳光窗台" };
  const neutral = catWorldPlacementReactionPlan(cat, { temperament: "gentle", dailyMoodKey: "bright" }, target);
  const favorite = catWorldPlacementReactionPlan(
    cat,
    { temperament: "gentle", dailyMoodKey: "bright" },
    { ...target, favorite: true },
  );

  assert.equal(neutral.favorite, false);
  assert.equal(favorite.favorite, true);
  assert.equal(favorite.badgeLabel, "最喜欢这里");
  assert.equal(favorite.cueKind, "heart");
  assert.match(favorite.message, /(喜欢|合我心意|安心)/);
  assert.notEqual(favorite.message, neutral.message);
  assert.ok(favorite.motion.hopY > 0);
});

test("placement plans are deterministic per cat and item", () => {
  const cat = { id: "siamese-a81f", traits: { temperament: "chatty" } };
  const target = { targetType: "decor", itemId: "study-desk", itemLabel: "英文书桌" };
  const first = catWorldPlacementReactionPlan(cat, { temperament: "chatty" }, target);
  const replay = catWorldPlacementReactionPlan(cat, { temperament: "chatty" }, target);
  const sibling = catWorldPlacementReactionPlan({ ...cat, id: "siamese-c204" }, { temperament: "chatty" }, target);

  assert.deepEqual(first, replay);
  assert.notEqual(first.identityToken, sibling.identityToken);
  assert.match(first.message, /英文书桌/);
});

test("the Phaser room wires individualized plans into floor and decor drops", async () => {
  const source = await readFile(new URL("../src/app/catWorldGame.js", import.meta.url), "utf8");

  assert.match(source, /catWorldPlacementReactionPlan\(entry\.cat, entry\.behavior/);
  assert.match(source, /itemLabel: interaction\.label,\s+favorite,/);
  assert.match(source, /message: placementPlan\.message/);
  assert.match(source, /this\.playCatPlacementReaction\(entry, action\.placementPlan\)/);
  assert.match(source, /placementPlan\.cueKind \|\| "paw"/);
  assert.match(source, /timedInteractionBubbleOffset\(entry\.container, overlayPosition\)/);
  assert.match(source, /const noBathKit = decorId === "bubble-bathtub"/);
});

import assert from "node:assert/strict";
import test from "node:test";

import { readFile } from "node:fs/promises";
import { catWorldCarryReactionPlan } from "../src/app/catWorldCarryReaction.js";

test("daily mood changes how the same individual reacts to being carried", () => {
  const cat = { id: "cat-4b3e", traits: { temperament: "gentle" } };
  const bright = catWorldCarryReactionPlan(cat, { dailyMoodKey: "bright", temperament: "gentle" });
  const grumpy = catWorldCarryReactionPlan(cat, { dailyMoodKey: "grumpy", temperament: "gentle" });

  assert.equal(bright.source, "daily-mood");
  assert.equal(bright.styleKey, "happy");
  assert.equal(bright.badgeLabel, "开心抱抱");
  assert.equal(grumpy.styleKey, "wiggle");
  assert.equal(grumpy.badgeLabel, "抱稳一点");
  assert.match(grumpy.message, /(闹脾气|不太高兴|不扭来扭去)/);
});

test("carry plans stay deterministic per individual instead of per breed", () => {
  const cat = {
    id: "siamese-a81f",
    breedId: "siamese",
    traits: { temperament: "chatty" },
    individualHabit: { animation: "chirp" },
  };
  const replay = catWorldCarryReactionPlan(cat, { temperament: "chatty" });
  const first = catWorldCarryReactionPlan(cat, { temperament: "chatty" });
  const sibling = catWorldCarryReactionPlan(
    { ...cat, id: "siamese-c204" },
    { temperament: "chatty" },
  );

  assert.deepEqual(first, replay);
  assert.notEqual(first.identityToken, sibling.identityToken);
  assert.equal(first.source, "temperament");
  assert.equal(first.cueKind, "chirp");
  assert.equal(first.styleKey, "happy");
});

test("sleep, wake and individual habits remain visible in the carry pose", () => {
  const cat = {
    id: "cat-window-pause",
    traits: { temperament: "guardian" },
    individualHabit: { animation: "lookout" },
  };
  const sleeping = catWorldCarryReactionPlan(cat, { sleeping: true, temperament: "guardian" });
  const waking = catWorldCarryReactionPlan(cat, { key: "waking", temperament: "guardian" });
  const alert = catWorldCarryReactionPlan(cat, { temperament: "guardian" });

  assert.equal(sleeping.source, "sleep");
  assert.equal(sleeping.styleKey, "sleepy");
  assert.equal(waking.source, "wake");
  assert.equal(waking.styleKey, "lookout");
  assert.equal(alert.badgeLabel, "警觉巡视");
  assert.equal(alert.cueKind, "lookout");
  assert.ok(alert.motion.duration >= 220);
});

test("the Phaser room uses the individualized carry plan for copy and motion", async () => {
  const source = await readFile(new URL("../src/app/catWorldGame.js", import.meta.url), "utf8");
  const page = await readFile(new URL("../src/app/pages/CatWorldPage.vue", import.meta.url), "utf8");

  assert.match(source, /catWorldCarryReactionPlan\(entry\.cat, entry\.behavior\)/);
  assert.match(source, /catMessage: carryPlan\.message/);
  assert.match(source, /carryStyle: carryPlan\.styleKey/);
  assert.match(source, /drawCatCarryCue\(container, carryPlan\)/);
  assert.match(source, /this\.tweens\.killTweensOf\(body\)/);
  assert.match(page, /carryInteraction\.catMessage \|\| "被抱起来啦/);
});

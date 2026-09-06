import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const gameUrl = new URL("../src/app/catWorldGame.js", import.meta.url);
const pageUrl = new URL("../src/app/pages/CatWorldPage.vue", import.meta.url);

test("cat social moments are persisted for both participants near the end of the animation", async () => {
  const [game, page] = await Promise.all([
    readFile(gameUrl, "utf8"),
    readFile(pageUrl, "utf8"),
  ]);

  assert.match(game, /delayedCall\(Math\.max\(holdMs - 240, 1000\)/);
  assert.match(game, /kind:\s*"cat-social"[\s\S]*?partnerCatId:\s*partner\.cat\.id[\s\S]*?socialKind:\s*kind/);
  assert.match(page, /const targetId = event\?\.itemId \|\| event\?\.partnerCatId;/);
  assert.match(page, /partnerCatId:\s*event\.partnerCatId \|\| ""/);
  assert.match(page, /socialKind:\s*event\.socialKind \|\| ""/);
  assert.match(page, /event\.kind === "cat-social"[\s\S]*?notice\.value = nextPayload\.event\.message/);
});

test("resting, waking, and low-energy cats are not selected for social moments", async () => {
  const game = await readFile(gameUrl, "utf8");
  const socialTarget = game.slice(
    game.indexOf("  socialTargetForCat(cat = {}"),
    game.indexOf("  individualHabitTarget(cat = {}"),
  );

  assert.match(socialTarget, /\["resting", "waking"\]\.includes\(behavior\.key\)/);
  assert.match(socialTarget, /\["resting", "waking"\]\.includes\(entry\.behavior\.key\)/);
  assert.match(socialTarget, /entry\.behavior\.energy >= Number\(entry\.behavior\.restThreshold \|\| 34\) \+ 8/);
});

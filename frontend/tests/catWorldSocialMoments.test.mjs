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

test("cat social choices use individual chemistry and expose the favorite companion", async () => {
  const [game, page] = await Promise.all([
    readFile(gameUrl, "utf8"),
    readFile(pageUrl, "utf8"),
  ]);
  const socialTarget = game.slice(
    game.indexOf("  socialTargetForCat(cat = {}"),
    game.indexOf("  individualHabitTarget(cat = {}"),
  );

  assert.match(game, /socialCircle:\s*snapshot\.socialCircle \|\| \{\}/);
  assert.match(socialTarget, /partnerProfiles\[entry\.cat\.id\]/);
  assert.match(socialTarget, /CAT_SOCIAL_PAIR_COOLDOWN_MS/);
  assert.match(socialTarget, /selectionScore = chemistry - Math\.min\(distance \/ 42, 18\)/);
  assert.match(socialTarget, /preferredKind:\s*partner\.relationship\.preferredKind/);
  assert.match(page, /socialCircle:\s*catSocial\.value/);
  assert.match(page, /social\.favoritePartnerLevelLabel/);
  assert.match(page, /<dt>猫咪伙伴<\/dt>/);
  assert.match(page, /同伴 \$\{social\.todayEventCount \|\| 0\}/);
});

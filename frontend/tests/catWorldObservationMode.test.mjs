import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const pageUrl = new URL("../src/app/pages/CatWorldPage.vue", import.meta.url);
const gameUrl = new URL("../src/app/catWorldGame.js", import.meta.url);
const stylesUrl = new URL("../../app/static/styles.css", import.meta.url);

test("expired play time keeps the room visible in observation mode", async () => {
  const [page, styles] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(stylesUrl, "utf8"),
  ]);
  const lockRule = styles.match(/\.cat-world-play-lock\s*\{([^}]*)\}/)?.[1] || "";

  assert.match(page, /Observation Mode/);
  assert.match(page, /:inert="playTimeLocked \? '' : null"/);
  assert.match(page, /aria-label="观察房间下一屏"/);
  assert.doesNotMatch(page, /:aria-hidden="playTimeLocked/);
  assert.match(lockRule, /position:\s*sticky\s*;/);
  assert.doesNotMatch(lockRule, /inset:\s*0\s*;/);
  assert.doesNotMatch(lockRule, /background:\s*rgba\(32, 48, 64/);
});

test("daily learning route stays outside the locked play area", async () => {
  const [page, game] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(gameUrl, "utf8"),
  ]);
  const routeIndex = page.indexOf('class="cat-world-learning-route"');
  const playAreaIndex = page.indexOf('class="cat-world-play-area"');

  assert.ok(routeIndex >= 0);
  assert.ok(playAreaIndex > routeIndex);
  assert.match(page, /class="cat-world-learning-guide-button"/);
  assert.match(page, /@click="showLearningCompanionReaction"/);
  assert.match(page, /const switched = await selectScene\(targetScene\)/);
  assert.match(page, /catWorldGame\.value\?\.focusCat\(cat\.id\)/);
  assert.match(page, /pause: options\.pause !== false/);
  assert.match(page, /}, CAT_BUBBLE_TOTAL_MS\);/);
  assert.match(page, /learningCompanion\.statusLabel/);
  assert.match(page, /:aria-pressed="day\.date === selectedLearningWeekDay\.date"/);
  assert.match(page, /@click="selectLearningWeekDay\(day\)"/);
  assert.match(page, /learningWeekMemory\.catMessage/);
  assert.match(game, /pauseCatForReaction\(container, cat\)/);
  assert.match(game, /container\.setData\("walkTween", walkTween\)/);
});

test("CAT-OS details are collapsed until requested", async () => {
  const page = await readFile(pageUrl, "utf8");

  assert.match(page, /const catOsExpanded = ref\(false\);/);
  assert.match(page, /v-if="catOsExpanded" class="cat-world-ai-panel-details"/);
  assert.match(page, /:aria-expanded="catOsExpanded"/);
});

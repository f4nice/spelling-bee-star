import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const pageUrl = new URL("../src/app/pages/CatWorldPage.vue", import.meta.url);
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
  const page = await readFile(pageUrl, "utf8");
  const routeIndex = page.indexOf('class="cat-world-learning-route"');
  const playAreaIndex = page.indexOf('class="cat-world-play-area"');

  assert.ok(routeIndex >= 0);
  assert.ok(playAreaIndex > routeIndex);
});

test("CAT-OS details are collapsed until requested", async () => {
  const page = await readFile(pageUrl, "utf8");

  assert.match(page, /const catOsExpanded = ref\(false\);/);
  assert.match(page, /v-if="catOsExpanded" class="cat-world-ai-panel-details"/);
  assert.match(page, /:aria-expanded="catOsExpanded"/);
});

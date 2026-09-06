import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const pageUrl = new URL("../src/app/pages/CatWorldPage.vue", import.meta.url);
const gameUrl = new URL("../src/app/catWorldGame.js", import.meta.url);
const stylesUrl = new URL("../../app/static/styles.css", import.meta.url);

test("the Phaser room publishes each cat's current intention", async () => {
  const game = await readFile(gameUrl, "utf8");

  assert.match(game, /catVisitPlanStatus/);
  assert.match(game, /reportCatIntent\(cat, plan = \{\}, phase = "moving"\)/);
  assert.match(game, /this\.owner\.handlers\.onCatIntent\?\.\(cat/);
  assert.match(game, /visitPlan \|\| \{ kind: "wander"/);
  assert.match(game, /kind: behavior\.sleeping \? "sleep" : "idle"/);
});

test("the room shows persistent live activity and can focus the matching cat", async () => {
  const page = await readFile(pageUrl, "utf8");
  const styles = await readFile(stylesUrl, "utf8");

  assert.match(page, /onCatIntent: updateLiveCatIntent/);
  assert.match(page, /const completionIntent = intent\.completionIntent/);
  assert.match(page, /updateLiveCatIntent\(cat, \{ \.\.\.completionIntent, updatedAt: Date\.now\(\) \}\)/);
  assert.match(page, /const roomLiveActivity = computed/);
  assert.match(page, /Number\(right\.id === focusedId\) - Number\(left\.id === focusedId\)/);
  assert.match(page, /aria-label="房间猫咪实时动向"/);
  assert.match(page, /@click="focusLiveCat\(entry\)"/);
  assert.match(page, /catWorldGame\.value\?\.focusCat\?\.\(cat\.id\)/);
  assert.match(page, /'cat-world-context-intent'/);
  assert.match(styles, /\.cat-world-room-live-list > button\.active/);
  assert.match(styles, /\.cat-world-room-live-list > button\.active :where\(strong, small, em, span\)/);
});

test("favorite furniture visits become timed room interactions before roaming resumes", async () => {
  const game = await readFile(gameUrl, "utf8");

  assert.match(game, /startAutonomousFavoriteDecorInteraction/);
  assert.match(game, /kind: "autonomous-decor"/);
  assert.match(game, /this\.startManualDecorAction\(entry, action\)/);
  assert.match(game, /timedInteractionLiveIntent\(action\.itemId, "active"/);
  assert.match(game, /goalKey: goal\.key/);
  assert.match(game, /visitPlan\.target\.goalKey === "favorite-decor"/);
  assert.match(game, /if \(!interactionOwnsSchedule\) this\.scheduleCatWalk/);
  assert.match(game, /\["manual-decor", "autonomous-decor"\]\.includes\(action\.kind\)/);
  assert.match(game, /timedInteractionLiveIntent\(itemId, "active", \{ expiresAt: endsAt \}\)/);
  assert.match(game, /entry\.container\.setData\("timedInteractionLiveActive", true\)/);
  assert.match(game, /const completedTimedInteraction = Boolean\(entry\.container\.getData\("timedInteractionLiveActive"\)\)/);
  assert.match(game, /completedTimedInteraction\s+\? timedInteractionLiveIntent\(itemId, "complete"\)/);
  assert.match(game, /if \(completedIntent\) this\.reportLiveCatIntent\(entry\.cat, completedIntent\)/);
  assert.match(game, /timedInteractionLiveIntent\(action\.itemId, "complete"\)/);
});

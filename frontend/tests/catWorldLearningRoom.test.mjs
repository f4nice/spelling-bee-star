import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const pageUrl = new URL("../src/app/pages/CatWorldPage.vue", import.meta.url);
const gameUrl = new URL("../src/app/catWorldGame.js", import.meta.url);

test("the activity room turns daily English progress into an interactive pixel board", async () => {
  const [page, game] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(gameUrl, "utf8"),
  ]);

  assert.match(page, /buildCatWorldRoomLearningSignal/);
  assert.match(page, /learningSignal:\s*learningRoomSignal\.value/);
  assert.match(page, /observationMode:\s*playTimeLocked\.value/);
  assert.match(page, /onLearningBoardClick:\s*openRoomLearningProgress/);
  assert.match(page, /今日学习灯牌已亮 \$\{learningRoomSignal\.completedCount\}\/3 格/);
  assert.match(game, /drawLearningBoard\(this\.owner\.snapshot\)/);
  assert.match(game, /"TODAY ENGLISH"/);
  assert.match(game, /snapshot\.observationMode \? 126 : 18/);
  assert.match(game, /this\.add\.zone\(x, y, width, height\)/);
  assert.match(game, /\.setScrollFactor\(0\)\s*\n\s*\.setInteractive\(\{ cursor: "pointer" \}\)/);
  assert.match(game, /onLearningBoardClick\?\.\(signal\)/);
});

test("a new learning milestone celebrates once with the companion cat", async () => {
  const game = await readFile(gameUrl, "utf8");

  assert.match(game, /nextLearningCount > previousLearningCount/);
  assert.match(game, /this\.pendingLearningMilestone = nextSnapshot\.learningSignal/);
  assert.match(game, /playPendingLearningMilestone\(\)/);
  assert.match(game, /this\.spawnCatBubble\(guideEntry, cat, message\)/);
  assert.match(game, /spawnLearningSparkles\(guideEntry\.x \+ 44/);
  assert.match(game, /this\.owner\.pendingLearningMilestone = null/);
});

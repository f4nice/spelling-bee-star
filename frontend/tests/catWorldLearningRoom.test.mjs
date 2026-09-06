import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const pageUrl = new URL("../src/app/pages/CatWorldPage.vue", import.meta.url);
const gameUrl = new URL("../src/app/catWorldGame.js", import.meta.url);
const stylesUrl = new URL("../../app/static/styles.css", import.meta.url);

test("the activity room turns daily English progress into an interactive pixel board", async () => {
  const [page, game] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(gameUrl, "utf8"),
  ]);

  assert.match(page, /buildCatWorldRoomLearningSignal/);
  assert.match(page, /learningSignal:\s*learningRoomSignal\.value/);
  assert.match(page, /class="cat-world-energy-garden"/);
  assert.match(page, /observationMode:\s*playTimeLocked\.value/);
  assert.match(page, /onLearningBoardClick:\s*openRoomLearningProgress/);
  assert.match(page, /今日学习灯牌已亮 \$\{learningRoomSignal\.completedCount\}\/3 格/);
  assert.match(game, /drawLearningBoard\(this\.owner\.snapshot\)/);
  assert.match(game, /drawLearningGardenFixture\(this\.owner\.snapshot\)/);
  assert.match(game, /"TODAY ENGLISH"/);
  assert.match(game, /snapshot\.observationMode \? 126 : 18/);
  assert.match(game, /this\.add\.zone\(x, y, width, height\)/);
  assert.match(game, /\.setScrollFactor\(0\)\s*\n\s*\.setInteractive\(\{ cursor: "pointer" \}\)/);
  assert.match(game, /onLearningBoardClick\?\.\(signal\)/);
});

test("a new learning milestone celebrates once with the companion cat", async () => {
  const game = await readFile(gameUrl, "utf8");

  assert.match(game, /function learningMilestoneScore/);
  assert.match(game, /nextLearningScore > previousLearningScore/);
  assert.match(game, /this\.pendingLearningMilestone = nextSnapshot\.learningSignal/);
  assert.match(game, /playPendingLearningMilestone\(\)/);
  assert.match(game, /this\.spawnCatBubble\(guideEntry, cat, message\)/);
  assert.match(game, /spawnLearningSparkles\(guideEntry\.x \+ 44/);
  assert.match(game, /this\.owner\.pendingLearningMilestone = null/);
});

test("the room keeps starter progress and gives the growing word garden a friendly hit area", async () => {
  const [game, styles] = await Promise.all([
    readFile(gameUrl, "utf8"),
    readFile(stylesUrl, "utf8"),
  ]);

  assert.match(game, /starterComplete:\s*Boolean\(signal\.starterComplete\)/);
  assert.match(game, /garden:\s*normalizeLearningGarden\(signal\.garden\)/);
  assert.match(game, /learningGardenFixturePosition\(\)/);
  assert.match(game, /y:\s*VIEW_WIDTH < 900 \? 146 : 92/);
  assert.match(game, /`单词芽 · \$\{garden\.stageLabel \|\| "种子"\}`/);
  assert.match(game, /this\.add\.zone\(position\.x, position\.y \+ 48, 132, 132\)/);
  assert.match(game, /itemId:\s*"learning-garden"/);
  assert.match(game, /单词芽已经长到/);
  assert.match(styles, /\.cat-world-energy-modal \.cat-world-modal-summary\s*\{\s*grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/);
  assert.match(styles, /\.cat-world-energy-modal \.cat-world-energy-list\s*\{\s*grid-template-columns:\s*1fr/);
});

test("recalled words become personal clickable pixel plaques beside the word garden", async () => {
  const [page, game] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(gameUrl, "utf8"),
  ]);

  assert.match(game, /learningMemory:\s*normalizeCatWorldLearningMemory\(signal\.learningMemory\)/);
  assert.match(game, /learningMemory\.recallTreasures\.slice\(0, 3\)/);
  assert.match(game, /WORD TREASURES/);
  assert.match(game, /const treasureHitZone = this\.add\.zone/);
  assert.match(game, /onLearningTreasureClick\?\.\(treasure, signal\)/);
  assert.match(page, /onLearningTreasureClick:\s*openRoomRecallTreasure/);
  assert.match(page, /function openRoomRecallTreasure\(treasure = \{\}, signal = learningRoomSignal\.value\)/);
  assert.match(page, /toggleCatDiary\(cat\)/);
  assert.match(page, /selectedCatRecallTreasureKey\.value = treasureKey/);
  assert.match(page, /catRecallTreasureDetailRef\.value\?\.scrollIntoView\(\{ block: "nearest" \}\)/);
});

test("the daily companion plans a visible visit to the study corner", async () => {
  const game = await readFile(gameUrl, "utf8");

  assert.match(game, /learningCompanionTarget\(cat = \{\}, index = 0, behavior = \{\}\)/);
  assert.match(game, /cat\.id !== guideCatId/);
  assert.match(game, /\.\.\.\(ritual\.targetItemIds \|\| \[\]\)/);
  assert.match(game, /itemId === "learning-garden" \? gardenPoint/);
  assert.match(game, /const selected = studyPoints\[0\]/);
  assert.match(game, /learningStyleKey: ritual\.styleKey/);
  assert.match(game, /animation: ritual\.animation/);
  assert.match(game, /\{ kind: "learning", target: learningTarget \}/);
  assert.match(game, /this\.spawnPlannedActionBubble\(container, cat, visitPlan\)/);
  assert.match(game, /this\.spawnLearningCompanionBubble\(container, cat, visitPlan\.target\)/);
});

test("the guide cat performs each visible study ritual once before ordinary choices", async () => {
  const game = await readFile(gameUrl, "utf8");

  assert.match(game, /this\.learningRitualVisitKey\(cat\.id\)/);
  assert.match(game, /requiredKind: learningRitualPending \? "learning" : ""/);
  assert.match(game, /this\.owner\.learningRitualVisits\.add\(learningVisitKey\)/);
  assert.match(game, /this\.learningRitualVisits = new Set\(\)/);
  assert.match(game, /const delayRange = ritualDue \? \[1800, 3400\]/);
  assert.match(game, /\{ minMs: 6500, maxMs: 26000 \}/);
});

test("each eligible cat can quietly revisit its own learning memory in the room", async () => {
  const [game, styles] = await Promise.all([
    readFile(gameUrl, "utf8"),
    readFile(stylesUrl, "utf8"),
  ]);

  assert.match(game, /catWorldLearningMemoryVisitPlan/);
  assert.match(game, /learningMemoryTarget\(/);
  assert.match(game, /\{ kind: "memory", target: learningMemoryTarget \}/);
  assert.match(game, /this\.owner\.learningMemoryVisits\.add\(visitPlan\.target\.visitKey\)/);
  assert.match(game, /startLearningMemoryMoment/);
  assert.match(game, /spawnLearningMemoryPageCue/);
  assert.match(game, /this\.learningMemoryVisits = new Set\(\)/);
  assert.match(styles, /\.cat-world-context-intent\.tone-memory\s*\{/);
});

test("the room keeps a readable mobile camera instead of squeezing the whole world", async () => {
  const [game, styles] = await Promise.all([
    readFile(gameUrl, "utf8"),
    readFile(stylesUrl, "utf8"),
  ]);

  assert.match(game, /catWorldResponsiveViewportWidth/);
  assert.match(game, /this\.parent\?\.clientWidth/);
  assert.match(game, /scenePageTarget\([\s\S]*?VIEW_WIDTH/);
  assert.match(styles, /\.shell\[data-quant-radar-page-key="cat-world"\] \.cat-world-room\s*\{[^}]*aspect-ratio:\s*16 \/ 7;/);
  assert.match(styles, /\.shell\[data-quant-radar-page-key="cat-world"\] \.cat-world-room\s*\{\s*height:\s*auto;\s*min-height:\s*0;\s*aspect-ratio:\s*6 \/ 7;/);
});

test("the expanded route explains the companion's method without adding another task card", async () => {
  const [page, styles] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(stylesUrl, "utf8"),
  ]);

  assert.match(page, /class="cat-world-learning-ritual"/);
  assert.match(page, /learningRoute\.ritual\.label/);
  assert.match(page, /learningRoute\.ritual\.cue/);
  assert.match(page, /learningRoute\.ritual\.destinationLabel/);
  assert.match(styles, /\.cat-world-learning-ritual\s*\{/);
  assert.match(styles, /grid-template-columns:\s*auto auto minmax\(180px, 1fr\) auto/);
});

test("the compact route shows a humane daily pace without adding another task card", async () => {
  const [page, styles] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(stylesUrl, "utf8"),
  ]);

  assert.match(page, /class=\"\['cat-world-learning-pace', `tone-\$\{learningRoute\.pace\.key\}`\]\"/);
  assert.match(page, /learningRoute\.pace\.detail/);
  assert.match(page, /learningRoute\.pace\.timeLabel/);
  assert.match(styles, /\.cat-world-learning-pace\s*\{/);
  assert.match(styles, /border-left:\s*4px solid var\(--learning-pace-color\)/);
  assert.match(styles, /\.cat-world-learning-pace\.tone-complete\s*\{[^}]*background:\s*#e4f7e4/s);
  assert.match(styles, /@media \(max-width: 560px\)[\s\S]*?\.cat-world-learning-pace\s*\{\s*grid-template-columns:\s*auto minmax\(0, 1fr\) auto/);
});

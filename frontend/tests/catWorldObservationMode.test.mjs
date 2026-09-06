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
  const lockCardRule = styles.match(/\.cat-world-play-lock-card\s*\{([^}]*)\}/)?.[1] || "";

  assert.match(page, /Observation Mode/);
  assert.match(page, /class="cat-world-play-lock-copy"/);
  assert.match(page, /:inert="playTimeLocked \? '' : null"/);
  assert.match(page, /aria-label="观察房间下一屏"/);
  assert.doesNotMatch(page, /:aria-hidden="playTimeLocked/);
  assert.match(lockRule, /position:\s*sticky\s*;/);
  assert.doesNotMatch(lockRule, /inset:\s*0\s*;/);
  assert.doesNotMatch(lockRule, /background:\s*rgba\(32, 48, 64/);
  assert.match(lockCardRule, /padding:\s*7px 10px;/);
  assert.match(styles, /\.cat-world-play-lock-copy\s*\{[\s\S]*?display:\s*flex;[\s\S]*?align-items:\s*center;/);
  assert.match(styles, /@media \(max-width: 560px\)[\s\S]*?\.cat-world-observation-actions\s*\{[\s\S]*?grid-column:\s*1 \/ -1;/);
});

test("daily learning route stays outside the locked play area", async () => {
  const [page, game] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(gameUrl, "utf8"),
  ]);
  const routeIndex = page.indexOf("'cat-world-learning-route'");
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

test("CAT-OS lives in the room assistant and stays collapsed until requested", async () => {
  const page = await readFile(pageUrl, "utf8");
  const roomPanelIndex = page.indexOf('class="cat-world-room-panel panel"');
  const roomStageIndex = page.indexOf("'cat-world-room'", roomPanelIndex);
  const roomAssistantIndex = page.indexOf("'cat-world-owned-panel'");
  const catOsIndex = page.indexOf("'cat-world-context-cat-live'", roomAssistantIndex);

  assert.match(page, /const catOsExpanded = ref\(false\);/);
  assert.doesNotMatch(page, /class="cat-world-ai-panel"/);
  assert.ok(roomPanelIndex >= 0);
  assert.ok(roomStageIndex > roomPanelIndex);
  assert.ok(roomAssistantIndex > roomStageIndex);
  assert.ok(catOsIndex > roomAssistantIndex);
  assert.match(page, /v-if="catOsExpanded"[\s\S]*?class="cat-world-context-cat-live-details"/);
  assert.match(page, /:aria-expanded="catOsExpanded"/);
});

test("the room assistant separates cat, bag, and room context", async () => {
  const [page, styles] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(stylesUrl, "utf8"),
  ]);

  assert.match(page, /const activeRoomPanel = ref\("cat"\);/);
  assert.match(page, /class="cat-world-context-tabs" role="tablist"/);
  assert.match(page, /v-show="activeRoomPanel === 'cat'"/);
  assert.match(page, /v-show="activeRoomPanel === 'bag'"/);
  assert.match(page, /v-show="activeRoomPanel === 'room'"/);
  assert.match(page, /activeRoomPanel\.value = "cat";[\s\S]*?petCat\(cat/);
  assert.match(page, /function focusRoomItem[\s\S]*?activeRoomPanel\.value = "bag";/);
  assert.match(page, /activeRoomPanel\.value = "room";[\s\S]*?notice\.value = nextEnabled \? "维修模式已开启/);
  assert.match(styles, /\.cat-world-context-tabs\s*\{[\s\S]*?grid-template-columns:\s*repeat\(3,/);
  assert.match(styles, /\.cat-world-context-tabs > button\.active,[\s\S]*?color:\s*#fff;[\s\S]*?background:\s*#1d7f5b;/);
});

test("the daily route is compact until its details are requested", async () => {
  const [page, styles] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(stylesUrl, "utf8"),
  ]);

  assert.match(page, /const learningRouteExpanded = ref\(false\);/);
  assert.match(page, /'is-expanded': learningRouteExpanded/);
  assert.match(page, /v-show="learningRouteExpanded"/);
  assert.match(page, /aria-controls="cat-world-learning-route-details"/);
  assert.match(page, /learningRouteExpanded \? "收起" : "展开路线"/);
  assert.match(styles, /\.cat-world-learning-route-details\s*\{\s*display:\s*grid;/);
  assert.match(styles, /\.cat-world-learning-route:not\(\.is-expanded\) \.cat-world-learning-companion-status\s*\{\s*display:\s*none;/);
});

test("the workspace separates play, shopping, and cat management into tabs", async () => {
  const [page, game, styles] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(gameUrl, "utf8"),
    readFile(stylesUrl, "utf8"),
  ]);

  assert.match(page, /const activeWorldView = ref\("room"\);/);
  assert.match(page, /class="cat-world-view-switcher" role="tablist"/);
  assert.match(page, /v-show="activeWorldView === 'room'"/);
  assert.match(page, /v-show="activeWorldView === 'shop'"/);
  assert.match(page, /v-show="activeWorldView === 'cats'"/);
  assert.match(page, /@click="openShopCategory\('cat'\)"/);
  assert.match(page, /if \(!setWorldView\("room"\)\) return;/);
  assert.match(page, /catWorldGame\.value\?\.refreshViewport\?\.\(\)/);
  assert.match(game, /refreshViewport\(\) \{/);
  assert.match(styles, /\.cat-world-view-switcher > button\.active,[\s\S]*?color:\s*#fff;[\s\S]*?background:\s*#1d7f5b;/);
});

test("the weekly learning trail opens on demand", async () => {
  const [page, styles] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(stylesUrl, "utf8"),
  ]);

  assert.match(page, /const learningWeekExpanded = ref\(false\);/);
  assert.match(page, /class="cat-world-learning-week-toggle"/);
  assert.match(page, /:aria-expanded="learningWeekExpanded"/);
  assert.match(page, /v-if="learningWeekExpanded" id="cat-world-learning-week-days"/);
  assert.match(page, /learningWeekExpanded \? "收起记录" : "查看七天"/);
  assert.match(page, /class="cat-world-learning-rhythm-badge"/);
  assert.match(page, /'cat-world-weekly-rhythm'/);
  assert.match(page, /学习触点/);
  assert.match(page, /完整闭环/);
  assert.doesNotMatch(page, /最长连续/);
  assert.match(styles, /\.cat-world-weekly-rhythm\s*\{[\s\S]*?grid-template-columns:\s*repeat\(2,/);
  assert.match(styles, /@media \(max-width: 560px\)[\s\S]*?\.cat-world-weekly-rhythm\s*\{[\s\S]*?grid-template-columns:\s*1fr;/);
});

test("medium and small screens collapse the bag into an on-demand drawer", async () => {
  const [page, styles] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(stylesUrl, "utf8"),
  ]);

  assert.match(page, /const bagExpanded = ref\(false\);/);
  assert.match(page, /class="cat-world-owned-drawer-toggle"/);
  assert.match(page, /aria-controls="cat-world-owned-drawer-body"/);
  assert.match(page, /'is-drawer-open': bagExpanded/);
  assert.match(styles, /@media \(max-width: 1180px\)[\s\S]*?\.cat-world-owned-panel:not\(\.is-drawer-open\) \.cat-world-owned-drawer-body \{\s*display:\s*none;/);
  assert.match(styles, /\.cat-world-owned-panel\.is-drawer-open \.cat-world-owned-drawer-toggle[\s\S]*?color:\s*#fff;[\s\S]*?background:\s*#1d7f5b;/);
});

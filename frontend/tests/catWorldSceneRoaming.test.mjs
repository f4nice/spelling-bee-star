import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const pageUrl = new URL("../src/app/pages/CatWorldPage.vue", import.meta.url);
const stylesUrl = new URL("../../app/static/styles.css", import.meta.url);

test("autonomous room changes are announced without interrupting room controls", async () => {
  const page = await readFile(pageUrl, "utf8");

  assert.match(page, /announceSceneMoves\(payload\.value\)/);
  assert.match(page, /nextPayload\?\.state\?\.sceneMoves/);
  assert.match(page, /normalizeCatWorldSceneMoves/);
  assert.match(page, /sceneMoves: state\.value\.sceneMoves/);
  assert.match(page, /class="cat-world-scene-move-strip"/);
  assert.match(page, /从\{\{ move\.fromSceneLabel \}\}走进来/);
  assert.match(page, /recentSceneMoves\.value = \[\];[\s\S]*?14000/);
  assert.match(page, /moves\.length === 1/);
  assert.match(page, /另外还有 \$\{moves\.length - 1\} 只猫咪去了别的房间/);
  assert.match(page, /class="cat-world-notice" aria-live="polite"/);
});

test("world navigation keeps view selection and the scene map on one desktop row", async () => {
  const [page, styles] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(stylesUrl, "utf8"),
  ]);
  const worldNavigationIndex = page.indexOf("'cat-world-world-navigation'");
  const viewSwitcherIndex = page.indexOf('class="cat-world-view-switcher"');
  const sceneDockIndex = page.indexOf('class="cat-world-scene-dock"');
  const roomPanelIndex = page.indexOf('class="cat-world-room-panel panel"');

  assert.ok(worldNavigationIndex > 0);
  assert.ok(viewSwitcherIndex > worldNavigationIndex);
  assert.ok(sceneDockIndex > viewSwitcherIndex);
  assert.ok(roomPanelIndex > sceneDockIndex);
  assert.match(styles, /\.cat-world-world-navigation\.has-scene-dock \{[\s\S]*?grid-template-columns:/);
  assert.match(styles, /\.cat-world-world-navigation \.cat-world-scene-dock \{[\s\S]*?grid-column: auto;/);
  assert.match(styles, /\.cat-world-scene-dock \.cat-world-scene-tabs \{[\s\S]*?overflow-x: auto;/);
  assert.match(styles, /@media \(max-width: 1180px\)[\s\S]*?\.cat-world-world-navigation\.has-scene-dock,[\s\S]*?grid-template-columns: 1fr;/);
  assert.match(
    styles,
    /\.cat-world-scene-dock \.cat-world-scene-tabs button:not\(:disabled\):hover,[\s\S]*?color: #fff;/,
  );
});

test("timed food and care stay visible only in their own scene", async () => {
  const [page, styles] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(stylesUrl, "utf8"),
  ]);

  assert.match(page, /rawActiveFood\.value\?\.inCurrentScene !== false/);
  assert.match(page, /rawActiveCare\.value\?\.inCurrentScene !== false/);
  assert.match(page, /scene\?\.hasActiveFood \? "进食中"/);
  assert.match(page, /scene\?\.hasActiveCare \? "猫草中"/);
  assert.match(page, /'has-live-activity': scene\.hasActiveFood \|\| scene\.hasActiveCare/);
  assert.match(styles, /button\.has-live-activity \{[\s\S]*?border-color: #9a6317;/);
});

test("cats arriving in the current room use an animated entrance without overwriting saved coordinates", async () => {
  const game = await readFile(new URL("../src/app/catWorldGame.js", import.meta.url), "utf8");

  assert.match(game, /playPendingSceneMoves\(\)/);
  assert.match(game, /if \(this\.isEditMode\(\) \|\| this\.isToolMode\(\)\) return false;[\s\S]*?takePendingSceneMoves/);
  assert.match(game, /catWorldSceneArrivalPlan/);
  assert.match(game, /sceneArrivalTarget/);
  assert.match(game, /this\.updateCatGait\(entry\.container, gait, distance, tween\.progress\)/);
  assert.match(game, /刚走进房间/);
});

test("cat cards expose individual preferences with white text on green interaction states", async () => {
  const [page, styles] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(stylesUrl, "utf8"),
  ]);

  assert.match(page, /class="cat-world-cat-individual-preference"/);
  assert.match(page, /cat\.favoriteItemLabels\.slice\(0, 3\)\.join\("、"\)/);
  assert.match(page, /<dt>个体偏好<\/dt>/);
  assert.match(
    styles,
    /\.cat-world-cat-chip\.active \.cat-world-cat-individual-preference,[\s\S]*?color: #fff;/,
  );
});

test("scene map explains room attraction without weakening active-state contrast", async () => {
  const [page, styles] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(stylesUrl, "utf8"),
  ]);

  assert.match(page, /return \{ \.\.\.configured, \.\.\.catalog \};/);
  assert.match(page, /function sceneAttractionSummary\(scene, limit = 2\)/);
  assert.match(page, /:title="sceneActionTitle\(scene\)"/);
  assert.match(page, /class="cat-world-scene-attraction"/);
  assert.match(page, /\{\{ scene\.attractedCatCount \}\}猫喜欢/);
  assert.match(page, /class="cat-world-room-attraction"/);
  assert.match(page, /<strong>房间吸引力<\/strong>/);
  assert.match(
    styles,
    /button\.active \.cat-world-scene-attraction,[\s\S]*?color: #fff;/,
  );
});

test("scene map makes every cat's current room visible", async () => {
  const [page, styles] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(stylesUrl, "utf8"),
  ]);

  assert.match(page, /const scenePresenceById = computed/);
  assert.match(page, /cat\.currentSceneId === scene\.id/);
  assert.match(page, /class="cat-world-scene-residents"/);
  assert.match(page, /scenePresence\(scene\)\.preview/);
  assert.match(page, /scenePresence\(scene\)\.summary/);
  assert.match(page, /class="cat-world-scene-cat-avatar"/);
  assert.match(page, /cat\.portrait\.style/);
  assert.match(page, /暂无猫咪/);
  assert.match(styles, /\.cat-world-scene-cat-avatar\s*\{[\s\S]*?width:\s*24px;[\s\S]*?height:\s*24px;/);
  assert.match(
    styles,
    /button\.active \.cat-world-scene-residents > b,[\s\S]*?color:\s*#fff;/,
  );
});

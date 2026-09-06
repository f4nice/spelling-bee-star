import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const gameUrl = new URL("../src/app/catWorldGame.js", import.meta.url);
const pageUrl = new URL("../src/app/pages/CatWorldPage.vue", import.meta.url);

test("Phaser applies individual gait motion and fading pixel paw prints", async () => {
  const game = await readFile(gameUrl, "utf8");

  assert.match(game, /import \{ catWorldGaitProfile \} from "\.\/catWorldGait\.js"/);
  assert.match(game, /gait: catWorldGaitProfile\(cat, behavior\)/);
  assert.match(game, /spawnCatPawPrint\(container, gait = \{\}, stepIndex = 0\)/);
  assert.match(game, /updateCatGait\(container, gait = \{\}, distance = 0, progress = 0\)/);
  assert.match(game, /body\.y = -Math\.abs\(Math\.sin\(phase\)\)/);
  assert.match(game, /this\.updateCatGait\(container, gait, distance/);
  assert.match(game, /duration: 1500/);
  assert.match(game, /entry\.container\.setData\("walkTween", null\)/);
  assert.match(game, /this\.resetCatGait\(entry\.container\)/);
  assert.match(game, /!container\.getData\("walkTween"\)/);
});

test("the cat archive names today's gait", async () => {
  const page = await readFile(pageUrl, "utf8");

  assert.match(page, /import \{ catWorldGaitProfile \} from "\.\.\/catWorldGait\.js"/);
  assert.match(page, /const gait = catWorldGaitProfile\(cat/);
  assert.match(page, /<dt>今日步态<\/dt>/);
  assert.match(page, /会留下短暂的像素爪印/);
});

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

const pageUrl = new URL("../src/app/pages/CatWorldPage.vue", import.meta.url);
const gameUrl = new URL("../src/app/catWorldGame.js", import.meta.url);
const routesUrl = new URL("../src/app/routeApiPaths.js", import.meta.url);

test("cat world exposes the bath queue and supply endpoints", async () => {
  const routes = await readFile(routesUrl, "utf8");
  assert.match(routes, /catWorldBathQueue:\s*\(\)\s*=>\s*["']\/api\/vue\/cat-world\/bath\/queue["']/);
  assert.match(routes, /catWorldBathSupply:\s*\(\)\s*=>\s*["']\/api\/vue\/cat-world\/bath\/supply["']/);
});

test("clicking a cat opens care actions and queues bathing through the API", async () => {
  const page = await readFile(pageUrl, "utf8");
  assert.match(page, /onCatClick:\s*\(cat\)\s*=>\s*openCatActionMenu\(cat\)/);
  assert.match(page, /routeApiPaths\.catWorldBathQueue\(\)/);
  assert.match(page, /routeApiPaths\.catWorldBathSupply\(\)/);
  assert.match(page, /举起/);
  assert.match(page, /洗澡排队/);
  assert.match(page, /投入 1 份沐浴露/);
  assert.match(page, /bathQueue:\s*bathQueue\.value/);
});

test("the Phaser room renders bath supply count and restores the active queued cat", async () => {
  const game = await readFile(gameUrl, "utf8");
  assert.match(game, /drawBathtubQueueBadge\(position, spec, snapshot\)/);
  assert.match(game, /snapshot\.bathQueue\?\.active/);
  assert.match(game, /onBathtubSupply/);
  assert.match(game, /onCatBathQueue/);
  assert.match(game, /泡泡沐浴露 ×\$\{supplyCount\}/);
});

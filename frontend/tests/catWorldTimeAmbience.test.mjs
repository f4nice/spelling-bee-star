import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  catWorldTimeAmbience,
  catWorldTimePhase,
} from "../src/app/catWorldTimeAmbience.js";

const gameUrl = new URL("../src/app/catWorldGame.js", import.meta.url);

test("cat world time phases follow the local daily rhythm", () => {
  assert.equal(catWorldTimePhase(4).key, "night");
  assert.equal(catWorldTimePhase(5).key, "dawn");
  assert.equal(catWorldTimePhase(8).key, "dawn");
  assert.equal(catWorldTimePhase(9).key, "day");
  assert.equal(catWorldTimePhase(16).key, "day");
  assert.equal(catWorldTimePhase(17).key, "dusk");
  assert.equal(catWorldTimePhase(19).key, "dusk");
  assert.equal(catWorldTimePhase(20).key, "night");
});

test("cat world ambience exposes a compact local clock label", () => {
  const ambience = catWorldTimeAmbience(new Date(2026, 8, 6, 7, 5));

  assert.equal(ambience.key, "dawn");
  assert.equal(ambience.label, "清晨");
  assert.equal(ambience.clockLabel, "07:05");
  assert.ok(ambience.wallAlpha > ambience.floorAlpha);
});

test("the room renders time tint, pixel atmosphere, and a fixed status badge", async () => {
  const game = await readFile(gameUrl, "utf8");

  assert.match(game, /const ambience = catWorldTimeAmbience\(new Date\(\)\);/);
  assert.match(game, /this\.drawRoomTimeAmbience\(bg, ambience\);/);
  assert.match(game, /this\.drawRoomTimeBadge\(ambience\);/);
  assert.match(game, /if \(ambience\.key === "night"\)/);
  assert.match(game, /\.setScrollFactor\(0\)/);
});


import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

import {
  CAT_SPOT_MEMORY_MAX_STRENGTH,
  catSpotMemoryPriority,
  catSpotMemorySummary,
  nextCatSpotMemory,
  normalizeCatSpotMemory,
} from "../src/app/catWorldSpotMemory.js";

test("spot memory grows only when the same cat is placed on the same furniture", () => {
  const first = nextCatSpotMemory({}, "sun-window");
  const repeated = nextCatSpotMemory({ memoryItemId: first.itemId, memoryStrength: first.strength }, "sun-window");
  const changed = nextCatSpotMemory({ memoryItemId: repeated.itemId, memoryStrength: repeated.strength }, "cloud-rug");

  assert.deepEqual(first, { itemId: "sun-window", strength: 1 });
  assert.deepEqual(repeated, { itemId: "sun-window", strength: 2 });
  assert.deepEqual(changed, { itemId: "cloud-rug", strength: 1 });
});

test("spot memory caps at five and has a visible familiarity label", () => {
  const memory = normalizeCatSpotMemory({ memoryItemId: "study-desk", memoryStrength: 99 });
  const summary = catSpotMemorySummary(
    { memoryItemId: memory.itemId, memoryStrength: memory.strength },
    { "study-desk": { label: "英文书桌" } },
  );

  assert.equal(memory.strength, CAT_SPOT_MEMORY_MAX_STRENGTH);
  assert.deepEqual(summary, {
    itemId: "study-desk",
    strength: 5,
    label: "英文书桌",
    levelLabel: "自己的角落",
  });
});

test("familiar furniture becomes a stronger leisure choice without overriding low energy", () => {
  const cat = {
    scenePosition: { memoryItemId: "sun-window", memoryStrength: 4 },
    traits: { temperament: "gentle" },
  };

  const rested = catSpotMemoryPriority(cat, { mood: 58, energy: 76, temperament: "gentle" });
  const exhausted = catSpotMemoryPriority(cat, { mood: 58, energy: 25, temperament: "gentle" });

  assert.ok(rested >= 70);
  assert.ok(exhausted < rested);
  assert.ok(exhausted < 70);
});

test("manual placement is persisted and later feeds the autonomous furniture target", async () => {
  const [gameSource, pageSource] = await Promise.all([
    readFile(new URL("../src/app/catWorldGame.js", import.meta.url), "utf8"),
    readFile(new URL("../src/app/pages/CatWorldPage.vue", import.meta.url), "utf8"),
  ]);

  assert.match(gameSource, /action\.kind === "manual-decor" && !action\.spotMemoryRecorded/);
  assert.match(gameSource, /placedItemId: shouldRememberSpot \? action\.itemId : ""/);
  assert.match(gameSource, /rememberedDecorTarget\(cat = \{\}\)/);
  assert.match(gameSource, /kind: "remembered-decor"/);
  assert.match(pageSource, /placedItemId: pending\.placedItemId/);
  assert.match(pageSource, /<b>熟悉角落<\/b>/);
});

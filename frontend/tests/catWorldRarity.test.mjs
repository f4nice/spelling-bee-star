import assert from "node:assert/strict";
import test from "node:test";

import { catRarityBadge } from "../src/app/catWorldRarity.js";

test("limited cat rarities keep their compact collection labels", () => {
  assert.deepEqual(catRarityBadge("SSR"), { label: "SSR", tone: "ssr" });
  assert.deepEqual(catRarityBadge("SR"), { label: "SR", tone: "sr" });
  assert.deepEqual(catRarityBadge("R"), { label: "R", tone: "r" });
});

test("resident cat rarities use short Chinese badges", () => {
  assert.deepEqual(catRarityBadge("Famous Cat"), { label: "名猫", tone: "famous" });
  assert.deepEqual(catRarityBadge("Starter"), { label: "伙伴", tone: "starter" });
});

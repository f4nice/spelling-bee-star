import test from "node:test";
import assert from "node:assert/strict";

import {
  CAT_BUBBLE_TOTAL_MS,
  createCatBubbleReaction,
  resolveCatBubbleTiming,
} from "../src/app/catWorldBubbleState.js";

test("cat bubble keeps its original lifetime after a scene refresh", () => {
  const startedAt = 1000;
  const reaction = createCatBubbleReaction("测试气泡", startedAt);

  assert.equal(reaction.expiresAt, startedAt + CAT_BUBBLE_TOTAL_MS);
  assert.deepEqual(resolveCatBubbleTiming(reaction, startedAt + 400), {
    active: true,
    remainingMs: 6600,
    holdDelay: 4100,
    fadeDuration: 2500,
    initialAlpha: 1,
  });
});

test("cat bubble resumes the remaining fade instead of disappearing", () => {
  const reaction = createCatBubbleReaction("测试气泡", 1000);

  assert.deepEqual(resolveCatBubbleTiming(reaction, 6000), {
    active: true,
    remainingMs: 2000,
    holdDelay: 0,
    fadeDuration: 2000,
    initialAlpha: 0.8,
  });
  assert.equal(resolveCatBubbleTiming(reaction, 8001).active, false);
});

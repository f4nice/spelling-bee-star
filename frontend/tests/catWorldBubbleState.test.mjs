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
    remainingMs: 10600,
    holdDelay: 7600,
    fadeDuration: 3000,
    initialAlpha: 1,
  });
});

test("cat bubble resumes the remaining fade instead of disappearing", () => {
  const reaction = createCatBubbleReaction("测试气泡", 1000);

  assert.deepEqual(resolveCatBubbleTiming(reaction, 10000), {
    active: true,
    remainingMs: 2000,
    holdDelay: 0,
    fadeDuration: 2000,
    initialAlpha: 2 / 3,
  });
  assert.equal(resolveCatBubbleTiming(reaction, 12001).active, false);
});

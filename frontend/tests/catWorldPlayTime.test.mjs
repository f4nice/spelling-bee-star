import test from "node:test";
import assert from "node:assert/strict";

import {
  formatCatWorldPlayTime,
  formatCatWorldPlayTimeProgress,
  formatCatWorldPlayTimeTiers,
  isCatWorldPlayTimeLocked,
  projectCatWorldPlayTime,
} from "../src/app/catWorldPlayTime.js";

test("cat world play time renders a stable minute and second clock", () => {
  assert.equal(formatCatWorldPlayTime(0), "00:00");
  assert.equal(formatCatWorldPlayTime(600), "10:00");
  assert.equal(formatCatWorldPlayTime(1199), "19:59");
});

test("cat world play time only counts down during an active visible session", () => {
  const playTime = { remainingSeconds: 600 };

  assert.equal(projectCatWorldPlayTime(playTime, 1000, 9500, true), 592);
  assert.equal(projectCatWorldPlayTime(playTime, 1000, 9500, false), 600);
  assert.equal(projectCatWorldPlayTime({ remainingSeconds: 3 }, 1000, 9000, true), 0);
});

test("cat world play area locks exactly when companion time reaches zero", () => {
  assert.equal(isCatWorldPlayTimeLocked(1), false);
  assert.equal(isCatWorldPlayTimeLocked(0), true);
  assert.equal(isCatWorldPlayTimeLocked(-20), true);
});

test("play time guidance follows the gradual tiers returned by the server", () => {
  const tiers = [
    { target: 20, minutes: 3 },
    { target: 50, minutes: 6 },
    { target: 100, minutes: 12 },
    { target: 200, minutes: 20 },
  ];

  assert.equal(
    formatCatWorldPlayTimeTiers({ tiers }),
    "20 词 3 分钟 · 50 词 6 分钟 · 100 词 12 分钟 · 200 词 20 分钟",
  );
  assert.equal(
    formatCatWorldPlayTimeProgress({
      spellingCount: 12,
      baseEarnedSeconds: 0,
      nextTarget: 20,
      nextRewardMinutes: 3,
    }),
    "再拼 8 词解锁 3 分钟",
  );
  assert.equal(
    formatCatWorldPlayTimeProgress({
      spellingCount: 50,
      baseEarnedSeconds: 360,
      nextTarget: 100,
      nextRewardMinutes: 12,
      rewardMinutes: 5,
    }),
    "已解锁 6 分钟 · 再拼 50 词升至 12 分钟 · 奖励 +5 分钟",
  );
});

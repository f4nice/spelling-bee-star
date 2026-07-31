import test from "node:test";
import assert from "node:assert/strict";

import {
  formatCatWorldPlayTime,
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

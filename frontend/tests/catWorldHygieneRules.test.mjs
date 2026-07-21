import test from "node:test";
import assert from "node:assert/strict";

import {
  bathStatusLabel,
  litterMoodPenalty,
  litterUseHint,
  neglectCountdownLabel,
} from "../src/app/catWorldHygieneRules.js";

test("litter mood penalty grows per pile and is capped", () => {
  assert.equal(litterMoodPenalty(0), 0);
  assert.equal(litterMoodPenalty(2), 4);
  assert.equal(litterMoodPenalty(4), 8);
  assert.equal(litterMoodPenalty(99), 8);
});

test("litter supplies explain automatic and click use", () => {
  assert.equal(litterUseHint({ useType: "litter-prevent" }), "猫咪拉屎时自动使用");
  assert.equal(litterUseHint({ useType: "litter-clean" }, 1), "点击房间里的猫屎清理");
  assert.equal(litterUseHint({ useType: "cat-care" }), "点击背包使用");
});

test("bath status distinguishes clean fur from overdue frazzled fur", () => {
  assert.equal(bathStatusLabel({ needsBath: true, daysSinceBath: 5 }), "5 天没洗 · 已炸毛");
  assert.equal(bathStatusLabel({ needsBath: false, daysSinceBath: 1, daysUntilBath: 2 }), "1 天前洗过 · 2 天后再洗");
});

test("neglect countdown explains warning and escape timing", () => {
  assert.equal(neglectCountdownLabel({ isWarning: false }), "体力和心情均安全");
  assert.equal(
    neglectCountdownLabel({ isWarning: true, statusLabel: "濒临死亡", remainingHours: 47 }),
    "濒临死亡 · 约 1 天 23 小时 后可能离家",
  );
  assert.equal(neglectCountdownLabel({ escaped: true, escapeLabel: "连续 3 天挨饿" }), "连续 3 天挨饿");
});

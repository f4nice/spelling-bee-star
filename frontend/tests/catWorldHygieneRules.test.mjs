import test from "node:test";
import assert from "node:assert/strict";

import {
  litterMoodPenalty,
  litterUseHint,
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

import assert from "node:assert/strict";
import test from "node:test";

import {
  catVisitPlanMessage,
  catVisitPlanStatus,
  chooseCatVisitPlan,
  rankCatVisitPlans,
} from "../src/app/catWorldBehaviorPlanner.js";

const target = (priority, extra = {}) => ({ x: 100, y: 320, priority, ...extra });

test("urgent care wins before personality-driven choices", () => {
  const plan = chooseCatVisitPlan([
    { kind: "social", target: target(100, { partnerLabel: "小伙伴" }) },
    { kind: "food", target: target(90, { label: "猫粮" }) },
  ], {
    catId: "cat-alpha",
    cycle: 1,
    behavior: { energy: 20, restThreshold: 34, socialNeed: 100, activityBias: 90 },
  });

  assert.equal(plan.kind, "food");
});

test("individual traits alter the same room choices", () => {
  const candidates = [
    { kind: "learning", target: target(66, { label: "英文书桌" }) },
    { kind: "social", target: target(66, { partnerLabel: "伙伴", chemistryScore: 70 }) },
    { kind: "habit", target: target(66, { label: "窗台" }) },
  ];
  const focused = rankCatVisitPlans(candidates, {
    catId: "cat-focused",
    cycle: 2,
    behavior: { attention: 95, curiosity: 20, socialNeed: 20 },
  });
  const outgoing = rankCatVisitPlans(candidates, {
    catId: "cat-outgoing",
    cycle: 2,
    behavior: { attention: 20, curiosity: 40, socialNeed: 95 },
  });

  assert.equal(focused[0].kind, "learning");
  assert.equal(outgoing[0].kind, "social");
});

test("repeating an ordinary action lowers its score without weakening urgent needs", () => {
  const ordinary = [{ kind: "favorite", target: target(70, { label: "窗台" }) }];
  const firstScore = rankCatVisitPlans(ordinary, { catId: "cat-repeat", cycle: 3 })[0].score;
  const repeatScore = rankCatVisitPlans(ordinary, {
    catId: "cat-repeat",
    cycle: 3,
    lastKind: "favorite",
    repeatCount: 2,
  })[0].score;
  const urgent = [{ kind: "care", target: target(96, { label: "洗澡" }) }];
  const urgentFirst = rankCatVisitPlans(urgent, { catId: "cat-repeat", cycle: 3 })[0].score;
  const urgentRepeat = rankCatVisitPlans(urgent, {
    catId: "cat-repeat",
    cycle: 3,
    lastKind: "care",
    repeatCount: 4,
  })[0].score;

  assert.ok(repeatScore < firstScore);
  assert.equal(urgentRepeat, urgentFirst);
});

test("plans are deterministic per cat and cycle and explain the next move", () => {
  const candidates = [
    { kind: "learning", target: target(72, { label: "英文书架", message: "我先陪你完成 20 词热身。" }) },
    { kind: "favorite", target: target(68, { label: "阳光窗台" }) },
  ];
  const context = { catId: "cat-stable", cycle: 7, behavior: { attention: 76, activityBias: 55 } };
  const first = chooseCatVisitPlan(candidates, context);
  const second = chooseCatVisitPlan(candidates, context);

  assert.deepEqual(second, first);
  assert.match(catVisitPlanMessage(first), /20 词热身|阳光窗台/);
});

test("a plan exposes stable live status for the room interface", () => {
  const plan = {
    kind: "learning",
    target: target(74, { label: "英文书桌", message: "我先在英文书桌旁等你。" }),
  };

  assert.deepEqual(catVisitPlanStatus(plan, "moving"), {
    kind: "learning",
    phase: "moving",
    statusLabel: "去学习角等你",
    targetLabel: "英文书桌",
    message: "我先在英文书桌旁等你。",
    tone: "learning",
  });
  assert.equal(catVisitPlanStatus(plan, "arrived").statusLabel, "正在陪你学习");
  const sleeping = catVisitPlanStatus({ kind: "sleep", target: { label: "睡眠时间" } }, "arrived");
  assert.equal(sleeping.tone, "rest");
  assert.match(sleeping.message, /梦里也要陪你记一个单词/);
});

import assert from "node:assert/strict";
import test from "node:test";

import {
  buildCatWorldLearningRoute,
  buildCatWorldWeekTrail,
  catWorldLearningCompanionGrowthLabel,
  catWorldLearningCompanionToken,
} from "../src/app/catWorldLearningRoute.js";

test("weekly trail distinguishes starts, input, output, and completed loops", () => {
  const trail = buildCatWorldWeekTrail({
    recentDays: [
      { date: "2026-09-01", weekdayLabel: "周二", dayLabel: "9/1", statusKey: "unavailable", statusLabel: "未记录" },
      { date: "2026-09-02", weekdayLabel: "周三", dayLabel: "9/2", statusKey: "rest", statusLabel: "休息" },
      { date: "2026-09-03", weekdayLabel: "周四", dayLabel: "9/3", statusKey: "started", statusLabel: "已开始", active: true },
      { date: "2026-09-04", weekdayLabel: "周五", dayLabel: "9/4", statusKey: "input", statusLabel: "练词", active: true },
      { date: "2026-09-05", weekdayLabel: "周六", dayLabel: "9/5", statusKey: "output", statusLabel: "表达", active: true },
      { date: "2026-09-06", weekdayLabel: "周日", dayLabel: "9/6", statusKey: "rest", statusLabel: "休息" },
      { date: "2026-09-07", weekdayLabel: "周一", dayLabel: "9/7", statusKey: "loop", statusLabel: "闭环", active: true, loopComplete: true, today: true },
    ],
  });

  assert.equal(trail.days.length, 7);
  assert.equal(trail.activeDays, 4);
  assert.equal(trail.loopDays, 1);
  assert.equal(trail.todayMessage, "今天闭环完成");
  assert.match(trail.summary, /4 天有学习/);
});

test("learning route starts with a gentle spelling target", () => {
  const route = buildCatWorldLearningRoute(
    { todaySpellingCount: 8, currentStreak: 0, nextAction: "再完成 12 词" },
    { label: "咪咪", displayLabel: "咪咪 · E36D" },
  );

  assert.equal(route.title, "咪咪的今日陪学路线");
  assert.equal(route.completedCount, 0);
  assert.equal(route.steps[0].active, true);
  assert.match(route.steps[0].detail, /8\/20/);
  assert.equal(route.steps[1].alternateHref, "/debate");
});

test("learning route recognizes input, output, and a returning learner", () => {
  const route = buildCatWorldLearningRoute({
    todaySpellingCount: 50,
    todayHasEssay: true,
    todayHasDebate: true,
    currentStreak: 4,
    nextAction: "今日学习闭环已完成",
  });

  assert.equal(route.completedCount, 3);
  assert.equal(route.steps.every((step) => step.completed), true);
  assert.equal(route.steps[2].label, "完成今日闭环");
  assert.equal(route.steps[2].actionKind, "energy");
  assert.match(route.steps[2].detail, /连续学习 4 天/);
});

test("learning companion milestone tokens are stable and skip the starting state", () => {
  assert.equal(
    catWorldLearningCompanionToken({ date: "2026-09-06", catId: "cat-123", statusKey: "loop" }),
    "2026-09-06:cat-123:loop",
  );
  assert.equal(
    catWorldLearningCompanionToken({ date: "2026-09-06", catId: "cat-123", statusKey: "starting" }),
    "",
  );
  assert.equal(catWorldLearningCompanionToken({ statusKey: "loop" }), "");
});

test("learning companion growth summarizes the cat-specific reward", () => {
  assert.equal(
    catWorldLearningCompanionGrowthLabel({ earnedMoodGain: 7, earnedBondGain: 3 }),
    "心情 +7 · 信任 +3",
  );
  assert.equal(catWorldLearningCompanionGrowthLabel({}), "等待今天的第一步");
});

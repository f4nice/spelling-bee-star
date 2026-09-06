import assert from "node:assert/strict";
import test from "node:test";

import {
  buildCatWorldHabitGarden,
  buildCatWorldLearningRoute,
  buildCatWorldRoomLearningSignal,
  buildCatWorldWeekTrail,
  catWorldLearningCompanionGrowthLabel,
  catWorldLearningCompanionToken,
  catWorldWeekMemory,
} from "../src/app/catWorldLearningRoute.js";

test("the word garden grows from persistent learning days and rewards completed loops visually", () => {
  const seed = buildCatWorldHabitGarden({ totalActiveDays: 0, totalLoopDays: 0 });
  const leaves = buildCatWorldHabitGarden({ totalActiveDays: 3, totalLoopDays: 1, bestStreak: 2 });
  const crown = buildCatWorldHabitGarden({ totalActiveDays: 11, totalLoopDays: 5, bestStreak: 6 });
  const recentFallback = buildCatWorldHabitGarden({
    recentDays: [
      { active: true, loopComplete: false },
      { active: true, loopComplete: true },
    ],
  });

  assert.equal(seed.key, "seed");
  assert.equal(seed.nextRemaining, 1);
  assert.equal(leaves.key, "leaves");
  assert.equal(leaves.growthPoints, 4);
  assert.equal(leaves.bestStreak, 2);
  assert.equal(crown.key, "crown");
  assert.equal(crown.nextRemaining, 0);
  assert.equal(recentFallback.growthPoints, 3);
});

test("weekly trail distinguishes starts, input, output, and completed loops", () => {
  const trail = buildCatWorldWeekTrail({
    recentDays: [
      { date: "2026-09-01", weekdayLabel: "周二", dayLabel: "9/1", statusKey: "unavailable", statusLabel: "未记录" },
      { date: "2026-09-02", weekdayLabel: "周三", dayLabel: "9/2", statusKey: "rest", statusLabel: "休息" },
      { date: "2026-09-03", weekdayLabel: "周四", dayLabel: "9/3", statusKey: "started", statusLabel: "已开始", active: true },
      { date: "2026-09-04", weekdayLabel: "周五", dayLabel: "9/4", statusKey: "input", statusLabel: "练词", active: true },
      { date: "2026-09-05", weekdayLabel: "周六", dayLabel: "9/5", statusKey: "output", statusLabel: "表达", active: true },
      { date: "2026-09-06", weekdayLabel: "周日", dayLabel: "9/6", statusKey: "rest", statusLabel: "休息" },
      { date: "2026-09-07", weekdayLabel: "周一", dayLabel: "9/7", statusKey: "loop", statusLabel: "闭环", detail: "50 词 · 作文 · 完成闭环", spellingCount: 50, hasEssay: true, active: true, loopComplete: true, today: true },
    ],
  });

  assert.equal(trail.days.length, 7);
  assert.equal(trail.activeDays, 4);
  assert.equal(trail.loopDays, 1);
  assert.equal(trail.days.at(-1).spellingCount, 50);
  assert.equal(trail.days.at(-1).hasEssay, true);
  assert.equal(trail.todayMessage, "今天闭环完成");
  assert.match(trail.summary, /4 天有学习/);
});

test("weekly memories keep day detail and follow the individual cat temperament", () => {
  const day = {
    date: "2026-09-07",
    weekdayLabel: "周一",
    dayLabel: "9/7",
    statusKey: "loop",
    detail: "50 词 · 作文 · 完成闭环",
  };
  const calm = catWorldWeekMemory(day, {
    id: "cat-calm",
    nickname: "小静",
    traits: { temperament: "calm" },
  });
  const chatty = catWorldWeekMemory(day, {
    id: "cat-chatty",
    nickname: "话话",
    traits: { temperament: "chatty" },
  });

  assert.equal(calm.dateLabel, "周一 9/7");
  assert.equal(calm.detail, day.detail);
  assert.equal(calm.catName, "小静");
  assert.match(calm.catMessage, /输入和表达都完成/);
  assert.notEqual(calm.catMessage, chatty.catMessage);
  assert.match(
    catWorldWeekMemory({ statusKey: "unavailable" }, calm).catMessage,
    /从现在开始.*新的脚印/,
  );
});

test("learning route starts with a gentle spelling target", () => {
  const route = buildCatWorldLearningRoute(
    { todaySpellingCount: 8, currentStreak: 0, nextAction: "再完成 12 词" },
    { label: "咪咪", displayLabel: "咪咪 · E36D" },
  );

  assert.equal(route.title, "咪咪的今日陪学路线");
  assert.equal(route.completedCount, 0);
  assert.equal(route.starterComplete, true);
  assert.equal(route.starterCount, 5);
  assert.equal(route.steps[0].active, true);
  assert.match(route.steps[0].detail, /起步爪印/);
  assert.match(route.steps[0].detail, /8\/20/);
  assert.equal(route.steps[1].alternateHref, "/debate");
});

test("the first five words form a visible low-pressure starting step", () => {
  const waiting = buildCatWorldLearningRoute({ todaySpellingCount: 3 });
  const started = buildCatWorldLearningRoute({ todaySpellingCount: 5 });

  assert.equal(waiting.starterComplete, false);
  assert.equal(waiting.starterCount, 3);
  assert.equal(waiting.starterRemaining, 2);
  assert.match(waiting.steps[0].detail, /3\/5/);
  assert.equal(started.starterComplete, true);
  assert.match(started.steps[0].detail, /5\/20/);
});

test("a cat learning style changes guidance order without changing the balanced goal", () => {
  const route = buildCatWorldLearningRoute(
    { todaySpellingCount: 20, currentStreak: 2 },
    {
      nickname: "话话",
      learningStyle: {
        label: "观点表达搭档",
        focusLabel: "用 AI Debate 说观点",
        preferredOutput: "debate",
        description: "鼓励清楚表达观点。",
      },
    },
  );

  assert.equal(route.learningStyleLabel, "观点表达搭档");
  assert.equal(route.learningFocusLabel, "用 AI Debate 说观点");
  assert.equal(route.preferredOutput, "debate");
  assert.equal(route.steps[1].href, "/debate");
  assert.equal(route.steps[1].alternateHref, "/essays");
  assert.match(route.steps[1].detail, /先完成一次 AI Debate/);
  assert.equal(route.steps[2].completed, false);
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

test("room learning signal lights input, output, and the completed loop independently", () => {
  const starting = buildCatWorldRoomLearningSignal(
    { todaySpellingCount: 6, recentDays: [{ date: "2026-09-07", today: true }] },
    { id: "cat-calm", nickname: "小静" },
    { catId: "cat-calm" },
  );
  const outputFirst = buildCatWorldRoomLearningSignal({
    todaySpellingCount: 6,
    todayHasDebate: true,
  });
  const complete = buildCatWorldRoomLearningSignal(
    {
      todaySpellingCount: 50,
      todayHasEssay: true,
      todayBalanceComplete: true,
      recentDays: [{ date: "2026-09-07", today: true }],
    },
    { id: "cat-calm", nickname: "小静" },
    { catId: "cat-calm", message: "三格都亮啦。" },
  );

  assert.equal(starting.completedCount, 0);
  assert.equal(starting.steps[0].active, true);
  assert.equal(starting.starterComplete, true);
  assert.equal(starting.stageKey, "started");
  assert.equal(starting.statusLabel, "5 词起步完成");
  assert.equal(starting.token, "2026-09-07:cat-calm:1:started:0");
  assert.equal(outputFirst.completedCount, 1);
  assert.equal(outputFirst.stageKey, "output");
  assert.equal(outputFirst.steps[1].completed, true);
  assert.equal(complete.completedCount, 3);
  assert.equal(complete.steps.every((step) => step.completed), true);
  assert.equal(complete.statusLabel, "今日闭环");
  assert.equal(complete.celebrationMessage, "三格都亮啦。");
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
  assert.equal(
    catWorldLearningCompanionToken({ date: "2026-09-06", catId: "cat-123", statusKey: "started" }),
    "2026-09-06:cat-123:started",
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

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { buildCatWorldRoomLearningSignal } from "../src/app/catWorldLearningRoute.js";
import {
  catWorldLearningMemoryLine,
  catWorldLearningMemoryNextLine,
  catWorldLearningMemoryRoomCue,
  catWorldLearningMemoryVisitPlan,
  formatCatWorldLearningMemoryDate,
  normalizeCatWorldLearningMemory,
} from "../src/app/catWorldLearningMemory.js";

test("cat learning memory keeps humane per-cat progress and readable titles", () => {
  const memory = normalizeCatWorldLearningMemory({
    hasMemory: true,
    companionDays: 3,
    startedDays: 2,
    warmupDays: 1,
    outputDays: 2,
    loopDays: 1,
    memoryPoints: 4,
    levelKey: "familiar",
    levelLabel: "熟悉节奏",
    levelIndex: 2,
    levelCount: 5,
    progressPercent: 0,
    nextLevelLabel: "稳定陪学",
    nextRemaining: 6,
    latestDate: "2026-09-07",
    stages: [
      { key: "starter", label: "起步搭子", threshold: 1, unlocked: true },
      { key: "familiar", label: "熟悉节奏", threshold: 4, unlocked: true, current: true },
      { key: "steady", label: "稳定陪学", threshold: 10, unlocked: false },
      { key: "guardian", label: "英语守护猫", threshold: 24, unlocked: false },
    ],
    recentDays: [
      { date: "2026-09-07", dayLabel: "9/7", statusKey: "loop", statusLabel: "完成学习闭环" },
    ],
  });

  assert.equal(memory.companionDays, 3);
  assert.equal(memory.loopDays, 1);
  assert.equal(catWorldLearningMemoryLine(memory), "熟悉节奏 · 陪学 3 天 · 闭环 1 次");
  assert.equal(catWorldLearningMemoryNextLine(memory), "再积累 6 点陪学记忆，成为稳定陪学");
  assert.deepEqual(memory.stages.filter((stage) => stage.unlocked).map((stage) => stage.key), ["starter", "familiar"]);
  assert.equal(memory.recentDays[0].statusLabel, "完成学习闭环");
  assert.equal(formatCatWorldLearningMemoryDate(memory.latestDate), "9月7日");
  assert.match(catWorldLearningMemoryRoomCue(memory), /最新一页写在 9月7日/);
  assert.match(catWorldLearningMemoryRoomCue(memory, true), /完成 1 次英语闭环/);
});

test("opening cat world without learning does not create a false memory", () => {
  const memory = normalizeCatWorldLearningMemory({
    hasMemory: false,
    companionDays: 0,
    loopDays: 0,
    levelLabel: "等待初次陪学",
    nextLevelLabel: "起步搭子",
    nextRemaining: 1,
  });

  assert.equal(memory.hasMemory, false);
  assert.equal(catWorldLearningMemoryLine(memory), "还没有一起留下学习记忆");
  assert.match(catWorldLearningMemoryRoomCue(memory), /第一次/);
});

test("the room signal carries the selected cat's own learning memory", () => {
  const signal = buildCatWorldRoomLearningSignal(
    { todaySpellingCount: 8 },
    {
      id: "cat-a",
      nickname: "小静",
      learningMemory: {
        hasMemory: true,
        companionDays: 4,
        loopDays: 2,
        levelLabel: "熟悉节奏",
      },
    },
    { catId: "cat-a" },
  );

  assert.equal(signal.guideCatId, "cat-a");
  assert.equal(signal.learningMemory.companionDays, 4);
  assert.equal(signal.learningMemory.loopDays, 2);
});

test("cat cards, profile and room expose the same personal learning history", async () => {
  const [page, game, styles] = await Promise.all([
    readFile(new URL("../src/app/pages/CatWorldPage.vue", import.meta.url), "utf8"),
    readFile(new URL("../src/app/catWorldGame.js", import.meta.url), "utf8"),
    readFile(new URL("../../app/static/styles.css", import.meta.url), "utf8"),
  ]);

  assert.match(page, /class="cat-world-learning-memory-badge"/);
  assert.match(page, /class="cat-world-cat-learning-memory"/);
  assert.match(page, /class="cat-world-learning-scrapbook"/);
  assert.match(page, /class="cat-world-learning-stamp-track"/);
  assert.match(page, /class="cat-world-learning-memory-days"/);
  assert.match(page, /<dt>陪学记忆<\/dt>/);
  assert.match(game, /catWorldLearningMemoryRoomCue\(signal\.learningMemory/);
  assert.match(styles, /\.cat-world-cat-learning-memory\s*\{[^}]*background:\s*#ffe6c7/s);
  assert.match(styles, /\.cat-world-learning-stamp-track\s*\{[^}]*grid-template-columns:\s*repeat\(4,/s);
  assert.match(styles, /\.cat-world-learning-memory-days\s*\{[^}]*overflow-x:\s*auto/s);
  assert.match(
    styles,
    /\.cat-world-cat-chip\.active \.cat-world-cat-learning-memory,[\s\S]*?background:\s*rgba\(255, 255, 255, 0\.16\)/,
  );
});

test("a cat revisits real learning memories at a low deterministic cadence", () => {
  const cat = {
    id: "cat-story",
    learningStyle: { key: "story-builder" },
    learningMemory: {
      hasMemory: true,
      companionDays: 5,
      loopDays: 2,
      memoryPoints: 7,
      levelKey: "familiar",
      levelLabel: "熟悉节奏",
      levelIndex: 2,
      levelCount: 5,
      latestDate: "2026-09-07",
      recentDays: [{ date: "2026-09-07", dayLabel: "9月7日", statusKey: "loop" }],
    },
  };
  const behavior = { canWalk: true, energy: 78, restThreshold: 34, attention: 72 };
  const plans = [1, 2, 3, 4].map((cycle) => catWorldLearningMemoryVisitPlan(cat, behavior, {
    cycle,
    sceneId: "main-room",
  })).filter(Boolean);

  assert.equal(plans.length, 1);
  assert.deepEqual(plans[0].targetItemIds, ["study-desk", "word-gallery", "book-shelf"]);
  assert.match(plans[0].message, /9月7日.*词汇和表达/);
  assert.equal(plans[0].animation, "book");
});

test("memory visits yield to recovery and urgent care", () => {
  const cat = {
    id: "cat-rest",
    learningMemory: { hasMemory: true, companionDays: 8, levelIndex: 2, levelCount: 5 },
  };
  const eligibleCycle = [1, 2, 3, 4].find((cycle) => catWorldLearningMemoryVisitPlan(
    cat,
    { canWalk: true, energy: 80, restThreshold: 34, attention: 60 },
    { cycle, sceneId: "main-room" },
  ));

  assert.ok(eligibleCycle);
  assert.equal(catWorldLearningMemoryVisitPlan(
    cat,
    { canWalk: false, sleeping: true, energy: 80, restThreshold: 34 },
    { cycle: eligibleCycle, sceneId: "main-room" },
  ), null);
  assert.equal(catWorldLearningMemoryVisitPlan(
    cat,
    { canWalk: true, key: "waking", energy: 80, restThreshold: 34 },
    { cycle: eligibleCycle, sceneId: "main-room" },
  ), null);
  assert.equal(catWorldLearningMemoryVisitPlan(
    cat,
    { canWalk: true, energy: 80, restThreshold: 34 },
    { cycle: eligibleCycle, sceneId: "main-room", carePriority: 82 },
  ), null);
});

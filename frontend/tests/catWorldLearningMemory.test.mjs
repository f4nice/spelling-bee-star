import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { buildCatWorldRoomLearningSignal } from "../src/app/catWorldLearningRoute.js";
import {
  catWorldLearningMemoryLine,
  catWorldLearningMemoryNextLine,
  catWorldLearningMemoryRoomCue,
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
  });

  assert.equal(memory.companionDays, 3);
  assert.equal(memory.loopDays, 1);
  assert.equal(catWorldLearningMemoryLine(memory), "熟悉节奏 · 陪学 3 天 · 闭环 1 次");
  assert.equal(catWorldLearningMemoryNextLine(memory), "再积累 6 点陪学记忆，成为稳定陪学");
  assert.match(catWorldLearningMemoryRoomCue(memory), /一起学过 3 天/);
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
  assert.match(page, /<dt>陪学记忆<\/dt>/);
  assert.match(game, /catWorldLearningMemoryRoomCue\(signal\.learningMemory/);
  assert.match(styles, /\.cat-world-cat-learning-memory\s*\{[^}]*background:\s*#ffe6c7/s);
  assert.match(
    styles,
    /\.cat-world-cat-chip\.active \.cat-world-cat-learning-memory,[\s\S]*?background:\s*rgba\(255, 255, 255, 0\.16\)/,
  );
});

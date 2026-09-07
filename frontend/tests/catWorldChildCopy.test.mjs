import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  friendlyCatWorldData,
  friendlyCatWorldText,
} from "../src/app/catWorldChildCopy.js";

const CHILD_UNFRIENDLY_COPY = /闭环|产能|触点|学习节奏|行动节奏|玩耍节奏|输入输出|运营活动|复盘|主动回想|隔日回想|三日巩固|今日参数|独立状态|AI Debate|去做 Debate|CAT-OS|Room Pulse|Agent Diary|Learning Scrapbook|Active Recall|WEEKLY RHYTHM|Cat Quest/;

test("old cat-world records are shown in child-friendly words", () => {
  const oldCopy = "完整英语闭环 · 学习触点 · 学习产能 · 运营活动 · 学习节奏 · 三日巩固";
  const friendlyCopy = friendlyCatWorldText(oldCopy);

  assert.equal(
    friendlyCopy,
    "一次完整学习 · 学习记录 · 学习能量 · 特别奖励 · 学习习惯 · 三天后再想",
  );
  assert.doesNotMatch(friendlyCopy, CHILD_UNFRIENDLY_COPY);
});

test("nested cat-world payloads keep their shape while copy is made friendly", () => {
  const source = {
    energy: 42,
    enabled: true,
    cats: [{ message: "今日学习闭环已完成", review: "隔日回想" }],
  };
  const result = friendlyCatWorldData(source);

  assert.deepEqual(result, {
    energy: 42,
    enabled: true,
    cats: [{ message: "今天的学习全部完成", review: "隔天想一想" }],
  });
  assert.notEqual(result, source);
  assert.notEqual(result.cats, source.cats);
});

test("visible cat-world source copy avoids adult product jargon", async () => {
  const sourceUrls = [
    new URL("../src/app/pages/CatWorldPage.vue", import.meta.url),
    new URL("../src/app/catWorldGame.js", import.meta.url),
    new URL("../src/app/catWorldLearningRoute.js", import.meta.url),
    new URL("../src/app/catWorldLearningMemory.js", import.meta.url),
    new URL("../../app/main.py", import.meta.url),
  ];
  const sources = await Promise.all(sourceUrls.map((url) => readFile(url, "utf8")));

  for (const source of sources) assert.doesNotMatch(source, CHILD_UNFRIENDLY_COPY);
  assert.doesNotMatch(sources[0], />STEP\s*0/);
});

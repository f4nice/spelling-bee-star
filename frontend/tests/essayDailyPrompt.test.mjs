import test from "node:test";
import assert from "node:assert/strict";

import { essayDailyPromptForDate, essayDailyPromptsForDate } from "../src/app/essayDailyPrompt.js";

test("daily essay prompt stays stable for the same local date", () => {
  const morning = essayDailyPromptForDate(new Date(2026, 7, 1, 8, 0));
  const evening = essayDailyPromptForDate(new Date(2026, 7, 1, 22, 30));

  assert.deepEqual(morning, evening);
  assert.equal(morning.dateKey, "2026-08-01");
});

test("daily essay prompts rotate between Gaokao and PET styles", () => {
  const dailyPairs = Array.from({ length: 8 }, (_, offset) => essayDailyPromptsForDate(new Date(2026, 7, 1 + offset)));

  for (const prompts of dailyPairs) {
    assert.deepEqual(prompts.map((prompt) => prompt.sourceKey), ["gaokao", "pet"]);
    assert.deepEqual(prompts.map((prompt) => prompt.sourceLabel), ["高考英语作文", "PET Writing"]);
  }
  assert.equal(new Set(dailyPairs.map((prompts) => prompts[0].title)).size, 4);
  assert.equal(new Set(dailyPairs.map((prompts) => prompts[1].title)).size, 4);
});

test("daily essay instructions are written in English", () => {
  const prompts = Array.from({ length: 8 }, (_, offset) => essayDailyPromptsForDate(new Date(2026, 7, 1 + offset))).flat();

  for (const prompt of prompts) {
    assert.doesNotMatch(prompt.typeLabel, /[\u3400-\u9fff]/);
    assert.doesNotMatch(prompt.prompt, /[\u3400-\u9fff]/);
    assert.match(prompt.wordRange, /words/);
  }
});

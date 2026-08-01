import test from "node:test";
import assert from "node:assert/strict";

import { essayDailyPromptForDate } from "../src/app/essayDailyPrompt.js";

test("daily essay prompt stays stable for the same local date", () => {
  const morning = essayDailyPromptForDate(new Date(2026, 7, 1, 8, 0));
  const evening = essayDailyPromptForDate(new Date(2026, 7, 1, 22, 30));

  assert.deepEqual(morning, evening);
  assert.equal(morning.dateKey, "2026-08-01");
});

test("daily essay prompts rotate between Gaokao and PET styles", () => {
  const sources = new Set(
    Array.from({ length: 8 }, (_, offset) => essayDailyPromptForDate(new Date(2026, 7, 1 + offset)).sourceLabel),
  );

  assert.deepEqual([...sources].sort(), ["PET Writing", "高考英语作文"].sort());
});

import assert from "node:assert/strict";
import test from "node:test";

import {
  countDiaryCharacters,
  diaryCharactersRemaining,
  diaryWritingProgress,
} from "../src/app/diaryWriting.js";

test("diary completion counts Chinese characters only", () => {
  assert.equal(countDiaryCharacters("Today I'm happy. 今天很好。 2026"), 4);
  assert.equal(countDiaryCharacters("春风，细雨！"), 4);
});

test("diary progress reaches completion at one hundred Chinese characters", () => {
  const ninetyNineCharacters = "今".repeat(99);
  const oneHundredCharacters = `${ninetyNineCharacters}天`;

  assert.equal(diaryCharactersRemaining(ninetyNineCharacters, 100), 1);
  assert.equal(diaryWritingProgress(ninetyNineCharacters, 100), 0.99);
  assert.equal(diaryCharactersRemaining(oneHundredCharacters, 100), 0);
  assert.equal(diaryWritingProgress(oneHundredCharacters, 100), 1);
});

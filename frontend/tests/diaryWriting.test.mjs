import assert from "node:assert/strict";
import test from "node:test";

import {
  countDiaryWords,
  diaryWordsRemaining,
  diaryWritingProgress,
} from "../src/app/diaryWriting.js";

test("diary completion counts English words only", () => {
  assert.equal(countDiaryWords("Today I'm happy. 今天很好。 2026"), 3);
  assert.equal(countDiaryWords("well-written can't stop"), 3);
});

test("diary progress reaches completion at one hundred words", () => {
  const ninetyNineWords = Array.from({ length: 99 }, (_, index) => `word${index}`).join(" ");
  const oneHundredWords = `${ninetyNineWords} finished`;

  assert.equal(diaryWordsRemaining(ninetyNineWords, 100), 1);
  assert.equal(diaryWritingProgress(ninetyNineWords, 100), 0.99);
  assert.equal(diaryWordsRemaining(oneHundredWords, 100), 0);
  assert.equal(diaryWritingProgress(oneHundredWords, 100), 1);
});

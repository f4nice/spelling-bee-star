import assert from "node:assert/strict";
import test from "node:test";
import { countEssayWords, essayEnergyLimit, essaySubmissionError } from "../src/app/essayRules.js";
import { createWordEditSnapshot } from "../src/app/wordEditingActions.js";

const body = (words) => Array(words).fill("word").join(" ");

test("exam writing requires 100 English words; ordinary writing can be shorter", () => {
  for (const type of ["gaokao", "pet"]) {
    assert.match(essaySubmissionError(body(99) + " 中文 123", type), /还差 1 词/);
    assert.equal(essaySubmissionError(body(100), type), "");
  }
  assert.equal(essaySubmissionError(body(10), "free"), "");
  assert.equal(countEssayWords("I'm well-known. Don’t café cafe\u0301 中文 123"), 5);
});

test("energy budget changes at 100 words", () => {
  for (const words of [1, 49, 50, 51, 99]) assert.equal(essayEnergyLimit(body(words)), 200);
  for (const words of [100, 101, 200]) assert.equal(essayEnergyLimit(body(words)), 500);
});

test("part of speech editing starts with the saved value", () => {
  assert.equal(createWordEditSnapshot({ part_of_speech: "n.; v." }).part_of_speech, "n.; v.");
});

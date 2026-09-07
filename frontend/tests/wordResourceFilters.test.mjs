import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  countWordResources,
  isWordIncomplete,
  wordMatchesResourceFilter,
} from "../src/app/wordResourceFilters.js";

const completeWord = {
  phonetic: "/wɜːd/",
  part_of_speech: "n.",
  english_definition: "A unit of language.",
  chinese_definition: "单词",
  english_example: "This is a word.",
  image_url: "/uploads/word.jpg",
  has_playable_audio: true,
  has_audio: false,
  image_issue: false,
  audio_issue: false,
};

const textFields = [
  "phonetic", "part_of_speech", "english_definition", "chinese_definition", "english_example",
];

test("complete dictionary text is not incomplete", () => {
  assert.equal(isWordIncomplete(completeWord), false);
  assert.equal(wordMatchesResourceFilter(completeWord, "incomplete"), false);
});

for (const field of textFields) {
  test(`incomplete includes absent, null, empty, and whitespace ${field}`, () => {
    const missing = { ...completeWord };
    delete missing[field];
    assert.equal(isWordIncomplete(missing), true);
    for (const value of [undefined, null, "", " \t\n\u3000 "]) {
      const word = { ...completeWord, [field]: value };
      assert.equal(isWordIncomplete(word), true);
      assert.equal(wordMatchesResourceFilter(word, "incomplete"), true);
    }
  });
}

test("surrounding whitespace does not make real text incomplete", () => {
  const word = { ...completeWord };
  for (const field of textFields) word[field] = `  ${word[field]} \n`;
  assert.equal(isWordIncomplete(word), false);
});

test("enrichment status does not replace actual field checks", () => {
  for (const enrichment_status of ["failed", "pending", "partial", "done", null]) {
    assert.equal(isWordIncomplete({ ...completeWord, enrichment_status }), false);
    assert.equal(isWordIncomplete({ ...completeWord, enrichment_status, phonetic: "" }), true);
  }
});

test("locked empty dictionary fields still count as incomplete", () => {
  for (const field of textFields) {
    assert.equal(isWordIncomplete({
      ...completeWord,
      [field]: "",
      [`${field}_locked`]: true,
    }), true);
  }
});

test("missing or broken media does not make complete text incomplete", () => {
  const word = {
    ...completeWord,
    image_url: null,
    has_playable_audio: false,
    has_audio: false,
    image_issue: true,
    audio_issue: true,
  };
  assert.equal(isWordIncomplete(word), false);
  for (const key of ["missingImage", "missingAudio", "imageIssue", "audioIssue", "missingAny"]) {
    assert.equal(wordMatchesResourceFilter(word, key), true);
  }
});

test("missing text alone does not change media filter semantics", () => {
  const word = { ...completeWord, english_example: null };
  assert.equal(isWordIncomplete(word), true);
  for (const key of ["missingImage", "missingAudio", "imageIssue", "audioIssue", "missingAny"]) {
    assert.equal(wordMatchesResourceFilter(word, key), false);
  }
});

test("either audio availability flag satisfies the existing audio filter", () => {
  for (const [has_playable_audio, has_audio, missing] of [
    [true, false, false],
    [false, true, false],
    [true, true, false],
    [false, false, true],
    [undefined, undefined, true],
  ]) {
    const word = { ...completeWord, has_playable_audio, has_audio };
    assert.equal(wordMatchesResourceFilter(word, "missingAudio"), missing);
    assert.equal(wordMatchesResourceFilter(word, "missingAny"), missing);
  }
});

test("each missing or broken media condition independently matches missingAny", () => {
  for (const patch of [
    { image_url: "" },
    { has_playable_audio: false, has_audio: false },
    { image_issue: true },
    { audio_issue: true },
  ]) {
    assert.equal(wordMatchesResourceFilter({ ...completeWord, ...patch }, "missingAny"), true);
  }
  assert.equal(wordMatchesResourceFilter(completeWord, "missingAny"), false);
});

test("all and unknown filters include every word", () => {
  for (const key of ["all", "unknown", "toString", "constructor", "__proto__", undefined, null]) {
    assert.equal(wordMatchesResourceFilter(completeWord, key), true);
    assert.equal(wordMatchesResourceFilter({}, key), true);
  }
});

test("counts always match each filter's actual result", () => {
  const words = [
    completeWord,
    { ...completeWord, phonetic: null },
    { ...completeWord, image_url: "" },
    { ...completeWord, has_playable_audio: false },
    { ...completeWord, image_issue: true },
    { ...completeWord, audio_issue: true },
    { ...completeWord, english_example: " ", image_url: null, audio_issue: true },
  ];
  const counts = countWordResources(words);
  assert.deepEqual(counts, {
    all: 7,
    incomplete: 2,
    missingImage: 2,
    missingAudio: 1,
    imageIssue: 1,
    audioIssue: 2,
    missingAny: 5,
  });
  for (const [key, count] of Object.entries(counts)) {
    assert.equal(count, words.filter((word) => wordMatchesResourceFilter(word, key)).length);
  }
});

test("empty lists have a complete set of zero counters", () => {
  const expected = {
    all: 0, incomplete: 0, missingImage: 0, missingAudio: 0,
    imageIssue: 0, audioIssue: 0, missingAny: 0,
  };
  assert.deepEqual(countWordResources([]), expected);
  assert.deepEqual(countWordResources(), expected);
  assert.deepEqual(countWordResources(null), expected);
});

test("counts update immediately after missing fields are filled", () => {
  const word = { ...completeWord, english_definition: "" };
  assert.equal(countWordResources([word]).incomplete, 1);
  word.english_definition = completeWord.english_definition;
  assert.equal(countWordResources([word]).incomplete, 0);
});

test("list grid shares filter/count rules and preserves original card numbering", () => {
  const source = readFileSync(new URL("../src/app/components/ListDetailWordGrid.vue", import.meta.url), "utf8");
  assert.match(source, /import\s*\{\s*countWordResources,\s*wordMatchesResourceFilter\s*\}\s*from\s*"\.\.\/wordResourceFilters\.js"/);
  assert.match(source, /const resourceCounts\s*=\s*computed\(\(\)\s*=>\s*countWordResources\(props\.data\.words\s*\|\|\s*\[\]\)\)/);
  assert.match(source, /indexedWords\.value\.filter\(\(\{\s*word\s*\}\)\s*=>\s*wordMatchesResourceFilter\(word,\s*activeFilter\.value\)\)/);
  assert.match(source, /key:\s*"all"[^}]*\},\s*\{\s*key:\s*"incomplete",\s*label:\s*"未补全",\s*count:\s*resourceCounts\.value\.incomplete/);
  assert.match(source, /:aria-pressed="activeFilter === option\.key"/);
  assert.match(source, /:title="option\.title"/);
  assert.match(source, /index:\s*Number\(word\.display_index\s*\|\|\s*index\s*\+\s*1\)\s*-\s*1/);
  assert.match(source, /<WordCard\s+v-for="item in filteredWords"[^>]*:key="item\.word\.id"[^>]*:index="item\.index"/);
  assert.match(source, /@media\s*\(max-width:\s*1100px\)\s*\{\s*\.word-resource-filter-top\s*\{[^}]*flex-direction:\s*column;[^}]*align-items:\s*stretch;/);
});

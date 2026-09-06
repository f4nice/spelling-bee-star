import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { buildCatWorldRoomLearningSignal } from "../src/app/catWorldLearningRoute.js";
import {
  catWorldLearningRecallDraft,
  catWorldLearningMemoryDefaultDate,
  catWorldLearningMemoryLine,
  catWorldLearningMemoryNextLine,
  catWorldLearningMemoryReflection,
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
    reviewCount: 2,
    recallTreasureCount: 2,
    recallTreasures: [
      {
        key: "steady",
        word: "steady",
        sentence: "I can make steady progress.",
        sourceDate: "2026-09-06",
        reviewDate: "2026-09-07",
        reviewCount: 2,
      },
      {
        word: "resilient",
        sentence: "I can stay resilient.",
        sourceDate: "2026-09-05",
        reviewDate: "2026-09-06",
        reviewCount: 1,
      },
    ],
    reviewedToday: true,
    todayRecallWord: "steady",
    todayRecallSentence: "I can make steady progress.",
    todayReviewSourceDate: "2026-09-06",
    lastReviewDate: "2026-09-07",
    lastReviewSourceDate: "2026-09-06",
    reviewDueToday: true,
    suggestedReviewDate: "2026-09-06",
    suggestedReviewStageLabel: "三日巩固",
    nextReviewDate: "2026-09-10",
    stages: [
      { key: "starter", label: "起步搭子", threshold: 1, unlocked: true },
      { key: "familiar", label: "熟悉节奏", threshold: 4, unlocked: true, current: true },
      { key: "steady", label: "稳定陪学", threshold: 10, unlocked: false },
      { key: "guardian", label: "英语守护猫", threshold: 24, unlocked: false },
    ],
    recentDays: [
      {
        date: "2026-09-07",
        dayLabel: "9/7",
        statusKey: "loop",
        statusLabel: "完成学习闭环",
        latestRecallWord: "steady",
        latestRecallSentence: "I can make steady progress.",
      },
    ],
  });

  assert.equal(memory.companionDays, 3);
  assert.equal(memory.loopDays, 1);
  assert.equal(catWorldLearningMemoryLine(memory), "熟悉节奏 · 陪学 3 天 · 闭环 1 次");
  assert.equal(catWorldLearningMemoryNextLine(memory), "再积累 6 点陪学记忆，成为稳定陪学");
  assert.deepEqual(memory.stages.filter((stage) => stage.unlocked).map((stage) => stage.key), ["starter", "familiar"]);
  assert.equal(memory.recentDays[0].statusLabel, "完成学习闭环");
  assert.equal(memory.reviewCount, 2);
  assert.equal(memory.recallTreasureCount, 2);
  assert.equal(memory.recallTreasures[0].reviewCount, 2);
  assert.equal(memory.recallTreasures[1].key, "resilient");
  assert.equal(memory.reviewedToday, true);
  assert.equal(memory.todayRecallWord, "steady");
  assert.equal(memory.todayReviewSourceDate, "2026-09-06");
  assert.equal(memory.reviewDueToday, true);
  assert.equal(memory.suggestedReviewStageLabel, "三日巩固");
  assert.equal(memory.recentDays[0].latestRecallWord, "steady");
  assert.equal(memory.recentDays[0].latestRecallSentence, "I can make steady progress.");
  assert.equal(formatCatWorldLearningMemoryDate(memory.latestDate), "9月7日");
  assert.match(catWorldLearningMemoryRoomCue(memory), /最新一页写在 9月7日/);
  assert.match(catWorldLearningMemoryRoomCue(memory), /珍藏着 2 个回想词/);
  assert.match(catWorldLearningMemoryRoomCue(memory, true), /完成 1 次英语闭环/);
});

test("active recall needs one English word and a short original sentence", () => {
  const ready = catWorldLearningRecallDraft(
    "  resilient  ",
    "  I   can stay resilient.  ",
  );
  assert.equal(ready.word, "resilient");
  assert.equal(ready.sentence, "I can stay resilient.");
  assert.equal(ready.sentenceWordCount, 4);
  assert.equal(ready.ready, true);

  assert.equal(catWorldLearningRecallDraft("two words", "I keep learning.").wordReady, false);
  assert.equal(catWorldLearningRecallDraft("steady", "Too short").sentenceReady, false);
  assert.equal(catWorldLearningRecallDraft("don't", "I don't give up.").ready, true);
  assert.equal(catWorldLearningRecallDraft("steady", "word ".repeat(61)).sentenceReady, false);
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

test("each cat reflects on the same learning page in its own voice", () => {
  const day = {
    date: "2026-09-07",
    dayLabel: "9/7",
    statusKey: "loop",
    statusLabel: "完成学习闭环",
  };
  const quietCat = catWorldLearningMemoryReflection(day, {
    id: "cat-quiet",
    nickname: "小静",
    traits: { temperament: "calm" },
    learningStyle: { label: "遮答主动回想", preferredOutput: "essay" },
  });
  const chattyCat = catWorldLearningMemoryReflection(day, {
    id: "cat-chatty",
    nickname: "话话",
    traits: { temperament: "chatty" },
    learningStyle: { label: "观点理由法", preferredOutput: "debate" },
  });

  assert.equal(quietCat.dateLabel, "9/7");
  assert.match(quietCat.achievement, /完整英语闭环/);
  assert.match(quietCat.reviewPrompt, /1 个词和 1 句话/);
  assert.equal(quietCat.actionLabel, "写一句新表达");
  assert.equal(quietCat.href, "/essays");
  assert.equal(chattyCat.actionLabel, "说一个新理由");
  assert.equal(chattyCat.href, "/debate");
  assert.notEqual(quietCat.catMessage, chattyCat.catMessage);
  assert.match(quietCat.catMessage, /遮答主动回想/);
});

test("a partial memory suggests the missing half of the English loop", () => {
  const warmup = catWorldLearningMemoryReflection({
    date: "2026-09-06",
    statusKey: "warmup",
    statusLabel: "完成 20 词热身",
  });
  const output = catWorldLearningMemoryReflection({
    date: "2026-09-05",
    statusKey: "output",
    statusLabel: "完成英语表达",
  });

  assert.equal(warmup.href, "/lists");
  assert.match(warmup.reviewPrompt, /主动回想/);
  assert.equal(output.href, "/lists");
  assert.match(output.reviewPrompt, /补 5 个词/);
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

test("a cat opens the due page and names its gentle two-step review rhythm", () => {
  const dueMemory = {
    hasMemory: true,
    companionDays: 4,
    memoryPoints: 5,
    levelIndex: 2,
    levelCount: 5,
    reviewDueToday: true,
    suggestedReviewDate: "2026-09-06",
    suggestedReviewStageLabel: "三日巩固",
    recallTreasureCount: 1,
    recallTreasures: [{
      key: "steady",
      word: "steady",
      sentence: "I can make steady progress.",
      sourceDate: "2026-09-06",
      reviewDate: "2026-09-07",
      reviewCount: 1,
    }],
    recentDays: [
      { date: "2026-09-07", dayLabel: "9/7", statusKey: "loop" },
      {
        date: "2026-09-06",
        dayLabel: "9/6",
        statusKey: "warmup",
        reviewCount: 1,
        reviewStageKey: "strengthen",
        reviewStageLabel: "三日巩固",
        reviewProgressLabel: "1/2",
        reviewDue: true,
      },
    ],
  };

  assert.equal(catWorldLearningMemoryDefaultDate(dueMemory), "2026-09-06");
  const cat = { id: "cat-review", learningMemory: dueMemory };
  const behavior = { canWalk: true, energy: 82, restThreshold: 34, attention: 70 };
  const plan = [1, 2, 3].map((cycle) => catWorldLearningMemoryVisitPlan(
    cat,
    behavior,
    { cycle, sceneId: "main-room" },
  )).find(Boolean);
  assert.ok(plan);
  assert.match(plan.message, /9\/6.*三日巩固/);
  assert.doesNotMatch(plan.message, /steady/);
  assert.equal(plan.dayLabel, "9/6");
  assert.ok(plan.priority >= 42);

  assert.equal(catWorldLearningMemoryDefaultDate({
    ...dueMemory,
    reviewedToday: true,
    todayReviewSourceDate: "2026-09-07",
  }), "2026-09-07");

  const reviewedCat = {
    ...cat,
    learningMemory: {
      ...dueMemory,
      reviewDueToday: false,
      reviewedToday: true,
      todayRecallWord: "steady",
      todayRecallSentence: "I can make steady progress.",
    },
  };
  const reviewedPlan = [1, 2, 3, 4].map((cycle) => catWorldLearningMemoryVisitPlan(
    reviewedCat,
    behavior,
    { cycle, sceneId: "main-room" },
  )).find(Boolean);
  assert.ok(reviewedPlan);
  assert.match(reviewedPlan.message, /今天刚找回的 steady/);
  assert.match(reviewedPlan.message, /I can make steady progress/);
  assert.equal(reviewedPlan.treasure.word, "steady");
  assert.equal(reviewedPlan.selectionLabel, "今日新记");
  assert.equal(reviewedPlan.statusLabel, "正在再看一遍 steady");
});

test("a due review never reveals its answer through a room treasure", () => {
  const memory = {
    hasMemory: true,
    companionDays: 6,
    memoryPoints: 8,
    levelIndex: 2,
    levelCount: 5,
    latestDate: "2026-09-07",
    reviewDueToday: true,
    suggestedReviewDate: "2026-09-06",
    recallTreasures: [
      {
        key: "steady",
        word: "steady",
        sentence: "I can make steady progress every day.",
        sourceDate: "2026-09-06",
        reviewDate: "2026-09-07",
        reviewCount: 1,
      },
      {
        key: "curious",
        word: "curious",
        sentence: "A curious learner keeps asking useful questions.",
        sourceDate: "2026-09-03",
        reviewDate: "2026-09-04",
        reviewCount: 2,
      },
    ],
    recentDays: [{
      date: "2026-09-06",
      dayLabel: "9/6",
      statusKey: "warmup",
      reviewStageLabel: "三日巩固",
    }],
  };
  const cat = { id: "cat-safe", learningMemory: memory };
  const behavior = { canWalk: true, energy: 82, restThreshold: 34, attention: 70 };
  const plans = [1, 2, 3].map((cycle) => catWorldLearningMemoryVisitPlan(
    cat,
    behavior,
    { cycle, sceneId: "main-room" },
  )).filter(Boolean);

  assert.equal(plans.length, 1);
  assert.equal(plans[0].treasure.word, "curious");
  assert.match(plans[0].message, /A curious learner/);
  assert.doesNotMatch(plans[0].message, /steady/);

  const hiddenOnlyCat = {
    ...cat,
    learningMemory: { ...memory, recallTreasures: memory.recallTreasures.slice(0, 1) },
  };
  const hiddenOnlyPlan = [1, 2, 3].map((cycle) => catWorldLearningMemoryVisitPlan(
    hiddenOnlyCat,
    behavior,
    { cycle, sceneId: "main-room" },
  )).find(Boolean);
  assert.ok(hiddenOnlyPlan);
  assert.equal(hiddenOnlyPlan.treasure, null);
  assert.match(hiddenOnlyPlan.message, /9\/6.*三日巩固/);
  assert.doesNotMatch(hiddenOnlyPlan.message, /steady/);
});

test("a cat chooses the same personal word treasure for the same memory visit", () => {
  const cat = {
    id: "cat-deterministic",
    learningMemory: {
      hasMemory: true,
      companionDays: 7,
      memoryPoints: 9,
      levelIndex: 2,
      levelCount: 5,
      latestDate: "2026-09-07",
      recallTreasures: [
        { key: "curious", word: "curious", sentence: "I stay curious about new words.", sourceDate: "2026-09-07" },
        { key: "resilient", word: "resilient", sentence: "Practice makes me resilient.", sourceDate: "2026-09-05" },
        { key: "steady", word: "steady", sentence: "I keep a steady learning rhythm.", sourceDate: "2026-09-03" },
      ],
    },
  };
  const behavior = { canWalk: true, energy: 80, restThreshold: 34, attention: 68 };
  const plan = [1, 2, 3, 4].map((cycle) => catWorldLearningMemoryVisitPlan(
    cat,
    behavior,
    { cycle, sceneId: "main-room" },
  )).find(Boolean);
  const repeatedPlan = [5, 6, 7, 8].map((cycle) => catWorldLearningMemoryVisitPlan(
    cat,
    behavior,
    { cycle, sceneId: "main-room" },
  )).find(Boolean);

  assert.ok(plan);
  assert.ok(repeatedPlan);
  assert.deepEqual(repeatedPlan.treasure, plan.treasure);
  assert.equal(repeatedPlan.targetLabel, plan.targetLabel);
});

test("each learning style chooses a word that supports its own study method", () => {
  const learningMemory = {
    hasMemory: true,
    companionDays: 8,
    memoryPoints: 12,
    levelIndex: 2,
    levelCount: 5,
    latestDate: "2026-09-07",
    recallTreasures: [
      {
        key: "cat",
        word: "cat",
        sentence: "I know this cat.",
        sourceDate: "2026-09-06",
        reviewDate: "2026-09-06",
        reviewCount: 1,
      },
      {
        key: "journey",
        word: "journey",
        sentence: "Every careful English sentence can carry a vivid story forward.",
        sourceDate: "2026-09-05",
        reviewDate: "2026-09-05",
        reviewCount: 2,
      },
      {
        key: "perspective",
        word: "perspective",
        sentence: "A new perspective can change my answer.",
        sourceDate: "2026-09-04",
        reviewDate: "2026-09-04",
        reviewCount: 1,
      },
      {
        key: "steady",
        word: "steady",
        sentence: "I learn at a steady pace.",
        sourceDate: "2026-08-01",
        reviewDate: "2026-09-06",
        reviewCount: 1,
      },
      {
        key: "routine",
        word: "routine",
        sentence: "My routine keeps me learning.",
        sourceDate: "2026-09-01",
        reviewDate: "2026-09-06",
        reviewCount: 5,
      },
      {
        key: "fragile",
        word: "fragile",
        sentence: "I can strengthen a fragile memory.",
        sourceDate: "2026-08-20",
        reviewDate: "2026-08-21",
        reviewCount: 1,
      },
    ],
  };
  const behavior = { canWalk: true, energy: 82, restThreshold: 34, attention: 72 };
  const expected = {
    "gentle-starter": ["cat", "短句起步"],
    "story-builder": ["journey", "长句续写"],
    "idea-sparring": ["perspective", "生词试用"],
    "loop-keeper": ["steady", "旧词接力"],
    "streak-keeper": ["routine", "熟词守护"],
    "review-organizer": ["fragile", "薄弱词整理"],
  };

  for (const [styleKey, [word, selectionLabel]] of Object.entries(expected)) {
    const plan = [1, 2, 3, 4].map((cycle) => catWorldLearningMemoryVisitPlan({
      id: `method-cat-${styleKey}`,
      breedKey: "mimi",
      traits: { temperament: "balanced" },
      learningStyle: { key: styleKey },
      learningMemory,
    }, behavior, { cycle, sceneId: "main-room" })).find(Boolean);

    assert.ok(plan);
    assert.equal(plan.treasure.word, word);
    assert.equal(plan.selectionLabel, selectionLabel);
    assert.equal(plan.styleKey, styleKey);
    assert.match(plan.message, new RegExp(`^${selectionLabel}。`));
    assert.equal(plan.targetLabel, `珍藏词 ${word} · ${selectionLabel}`);
  }
});

test("word treasure visits follow each cat's own learning ritual instead of its breed", () => {
  const memory = {
    hasMemory: true,
    companionDays: 7,
    memoryPoints: 10,
    levelIndex: 2,
    levelCount: 5,
    latestDate: "2026-09-07",
    recallTreasures: [{
      key: "curious",
      word: "curious",
      sentence: "A curious learner keeps asking useful questions.",
      sourceDate: "2026-09-07",
    }],
  };
  const behavior = { canWalk: true, energy: 82, restThreshold: 34, attention: 72 };
  const expectations = [
    ["gentle-starter", "轻声复述", "正在轻声复述", "blink"],
    ["story-builder", "句子续写", "正在把词放回句子", "book"],
    ["idea-sparring", "试新用法", "正在试一个新用法", "chirp"],
    ["loop-keeper", "遮答回想", "正在遮答回想", "paw"],
    ["streak-keeper", "守住熟练", "正在守住熟练爪印", "heart"],
    ["review-organizer", "整理复习页", "正在整理复习页", "book"],
    ["balanced", "再看一遍", "正在再看一遍", "book"],
  ];

  const plans = expectations.map(([styleKey]) => [1, 2, 3, 4]
    .map((cycle) => catWorldLearningMemoryVisitPlan({
      id: `same-breed-${styleKey}`,
      breedKey: "british-shorthair",
      traits: { temperament: "calm" },
      learningStyle: { key: styleKey },
      learningMemory: memory,
    }, behavior, { cycle, sceneId: "main-room" }))
    .find(Boolean));

  plans.forEach((plan, index) => {
    const [, ritualLabel, statusVerb, animation] = expectations[index];
    assert.ok(plan);
    assert.equal(plan.ritualLabel, ritualLabel);
    assert.equal(plan.styleKey, expectations[index][0]);
    assert.equal(plan.statusLabel, `${statusVerb} curious`);
    assert.equal(plan.animation, animation);
    assert.match(plan.message, /A curious learner keeps asking useful questions/);
  });
  assert.equal(new Set(plans.map((plan) => plan.message)).size, expectations.length);
});

test("cats sharing a learning style still keep stable individual memory tones", () => {
  const memory = {
    hasMemory: true,
    companionDays: 7,
    memoryPoints: 10,
    levelIndex: 2,
    levelCount: 5,
    latestDate: "2026-09-07",
    recallTreasures: [{
      key: "steady",
      word: "steady",
      sentence: "I keep a steady learning rhythm.",
      sourceDate: "2026-09-07",
    }],
  };
  const behavior = { canWalk: true, energy: 82, restThreshold: 34, attention: 72 };
  const planFor = (id) => [1, 2, 3, 4]
    .map((cycle) => catWorldLearningMemoryVisitPlan({
      id,
      breedKey: "siamese",
      traits: { temperament: "chatty" },
      learningStyle: { key: "idea-sparring" },
      learningMemory: memory,
    }, behavior, { cycle, sceneId: "main-room" }))
    .find(Boolean);
  const first = planFor("same-style-cat-1");
  const replay = planFor("same-style-cat-1");
  const individualMessages = Array.from({ length: 12 }, (_, index) => planFor(`same-style-cat-${index + 1}`).message);

  assert.equal(replay.message, first.message);
  assert.equal(new Set(individualMessages).size, 2);
  assert.ok(individualMessages.every((message) => message.includes("steady")));
});

test("cat cards, profile and room expose the same personal learning history", async () => {
  const [page, game, styles, routes] = await Promise.all([
    readFile(new URL("../src/app/pages/CatWorldPage.vue", import.meta.url), "utf8"),
    readFile(new URL("../src/app/catWorldGame.js", import.meta.url), "utf8"),
    readFile(new URL("../../app/static/styles.css", import.meta.url), "utf8"),
    readFile(new URL("../src/app/routeApiPaths.js", import.meta.url), "utf8"),
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
  assert.match(page, /@click="selectCatMemoryDay\(day\)"/);
  assert.match(page, /class="cat-world-learning-memory-reflection"/);
  assert.match(page, /class="cat-world-recall-treasures"/);
  assert.match(page, /@click="selectCatRecallTreasure\(treasure\)"/);
  assert.match(page, /catRecallTreasureDetailRef\.value\?\.scrollIntoView\(\{ block: "nearest" \}\)/);
  assert.match(page, /珍藏 \{\{ cat\.learningMemory\.recallTreasureCount \}\} 词/);
  assert.match(page, /@click="focusSelectedCatMemory"/);
  assert.match(page, /CAT_MEMORY_REVIEW_SECONDS = 30/);
  assert.match(page, /@click="handleCatMemoryReviewAction"/);
  assert.match(page, /selectedCatMemoryReviewState\.reviewedToday/);
  assert.match(page, /catWorldLearningMemoryDefaultDate\(cat\.learningMemory\)/);
  assert.match(page, /day\.reviewStageKey === 'settled'/);
  assert.match(page, /今日\{\{ day\.reviewStageLabel \}\}/);
  assert.match(page, /class="cat-world-memory-recall-form"/);
  assert.match(page, /v-model="catMemoryReview\.word"/);
  assert.match(page, /v-model="catMemoryReview\.sentence"/);
  assert.match(page, /recalledWord:\s*draft\.word/);
  assert.match(page, /recalledSentence:\s*draft\.sentence/);
  assert.doesNotMatch(page, /void saveCatMemoryReview\(cat\.id, sourceDate\)/);
  assert.match(routes, /catWorldLearningMemoryReview: \(\) => "\/api\/vue\/cat-world\/learning-memory\/review"/);
  assert.match(page, /:aria-pressed="day\.date === selectedCatMemoryDay\.date"/);
  assert.match(styles, /\.cat-world-learning-memory-days > button\.active\s*\{[^}]*color:\s*#fff;[^}]*background:\s*#1d7f5b;/s);
  assert.match(styles, /\.cat-world-learning-memory-actions button:hover,[\s\S]*?color:\s*#fff;\s*background:\s*#1d7f5b;/);
  assert.match(styles, /\.cat-world-memory-review > button:not\(:disabled\):hover,[\s\S]*?color:\s*#fff;\s*background:\s*#1d7f5b;/);
  assert.match(styles, /\.cat-world-memory-review\.complete > button\s*\{[^}]*color:\s*#fff;[^}]*background:\s*#1d7f5b;/s);
  assert.match(styles, /\.cat-world-memory-recall-form\s*\{[^}]*grid-template-columns:/s);
  assert.match(styles, /\.cat-world-memory-recall-form input:focus,[\s\S]*?border-color:\s*#007f67;/);
  assert.match(styles, /\.cat-world-recall-treasure-list\s*\{[^}]*grid-template-columns:\s*repeat\(4,/s);
  assert.match(styles, /\.cat-world-recall-treasure-list > button\.active\s*\{[^}]*color:\s*#fff;[^}]*background:\s*#1d7f5b;/s);
  assert.match(styles, /\.cat-world-recall-treasure-list > button\s*\{[^}]*transition:\s*transform 150ms ease, border-color 150ms ease, box-shadow 150ms ease;/s);
  assert.match(styles, /\.cat-world-learning-memory-days > button\.review-due:not\(\.active\)/);
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

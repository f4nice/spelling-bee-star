import test from "node:test";
import assert from "node:assert/strict";

import {
  catDecorDropPosition,
  catDropInteractionFor,
  catFloorDropPosition,
  catLikesItem,
  floorDropPosition,
  interactionMoveDuration,
  itemInteractionFor,
  timedInteractionLabel,
  timedInteractionProgress,
  wandChaseJoinDecision,
} from "../src/app/catWorldItemInteractions.js";

test("interactive room items use the expected controlled behavior", () => {
  assert.equal(itemInteractionFor("reading-lamp", "decor")?.behavior, "toggle-attract");
  assert.equal(itemInteractionFor("study-desk", "decor")?.behavior, "walk-and-jump");
  assert.equal(itemInteractionFor("bubble-bathtub", "decor")?.behavior, "walk-and-bathe");
  assert.equal(itemInteractionFor("feather-wand", "toy")?.behavior, "pointer-follow");
  assert.equal(itemInteractionFor("feather-wand", "decor"), null);
});

test("timed furniture interactions expose a label and stable countdown progress", () => {
  assert.equal(timedInteractionLabel("bubble-bathtub"), "泡泡洗澡");
  assert.equal(timedInteractionLabel("window-hammock"), "吊床休息");
  assert.equal(timedInteractionLabel("future-item"), "互动中");
  assert.deepEqual(timedInteractionProgress(1000, 5000, 3000), {
    progress: 0.5,
    remainingMs: 2000,
    remainingSeconds: 2,
  });
  assert.equal(timedInteractionProgress(1000, 5000, 9000).progress, 1);
});

test("carried cats recognize furniture drop interactions", () => {
  assert.equal(catDropInteractionFor("bubble-bathtub")?.behavior, "bathe");
  assert.equal(catDropInteractionFor("study-desk")?.behavior, "perch");
  assert.equal(catDropInteractionFor("felt-cat-bed")?.behavior, "nap");
  assert.equal(catDropInteractionFor("word-gallery"), null);
});

test("server duration overrides change only allowlisted furniture timing", () => {
  assert.equal(catDropInteractionFor("study-desk")?.holdMs, 9000);
  assert.equal(catDropInteractionFor("bubble-bathtub")?.holdMs, 12000);
  assert.equal(catDropInteractionFor("study-desk", { "study-desk": 16000 })?.holdMs, 16000);
  assert.equal(catDropInteractionFor("study-desk", { "study-desk": 100 })?.holdMs, 3000);
  assert.equal(catDropInteractionFor("study-desk", { "study-desk": 999999 })?.holdMs, 60000);
  assert.equal(catDropInteractionFor("study-desk", { "study-desk": "bad" })?.holdMs, 9000);
  assert.equal(catDropInteractionFor("word-gallery", { "word-gallery": 16000 }), null);
});

test("all five new window ledges support distinct perch interactions", () => {
  const expected = new Map([
    ["moon-window", "窗边看月亮"],
    ["rain-window", "窗边听雨"],
    ["garden-window", "窗边看花"],
    ["snow-window", "窗边看雪"],
    ["sea-window", "窗边看海"],
  ]);

  for (const [itemId, label] of expected) {
    assert.equal(catDropInteractionFor(itemId)?.behavior, "perch");
    assert.equal(catDropInteractionFor(itemId)?.actionLabel, "放到窗台");
    assert.equal(timedInteractionLabel(itemId), label);
  }
});

test("floor drop positions a held toy around the clicked floor point", () => {
  assert.deepEqual(
    floorDropPosition(
      { x: 1500, y: 400 },
      { width: 172, height: 70, focusX: 88, focusY: 52 },
      { width: 2560, floorTop: 260, floorBottom: 522, border: 12 },
    ),
    { x: 1412, y: 348 },
  );
});

test("carried cats stay inside the walkable floor when dropped", () => {
  assert.deepEqual(
    catFloorDropPosition(
      { x: 4, y: 900 },
      { width: 1600, floorTop: 260, floorBottom: 522 },
    ),
    { x: 38, y: 452 },
  );
});

test("decor drop positions use each furniture interaction anchor", () => {
  assert.deepEqual(
    catDecorDropPosition(
      catDropInteractionFor("bubble-bathtub"),
      { x: 940, y: 332 },
      { width: 180, height: 108 },
      { width: 1600, floorBottom: 522 },
    ),
    { x: 982, y: 398 },
  );
  assert.deepEqual(
    catDecorDropPosition(
      catDropInteractionFor("study-desk"),
      { x: 496, y: 348 },
      { width: 200, height: 96 },
      { width: 1600, floorBottom: 522 },
    ),
    { x: 548, y: 300 },
  );
});

test("favorite matching keeps toy and decor preferences separate", () => {
  const cat = {
    favoriteToyIds: ["feather-wand"],
    favoriteDecorIds: ["reading-lamp"],
  };

  assert.equal(catLikesItem(cat, "feather-wand", "toy"), true);
  assert.equal(catLikesItem(cat, "feather-wand", "decor"), false);
  assert.equal(catLikesItem(cat, "reading-lamp", "decor"), true);
});

test("interaction movement stays slow but clamps very short and long trips", () => {
  assert.equal(interactionMoveDuration({ x: 0, y: 0 }, { x: 1, y: 1 }, 1), 2600);
  assert.equal(interactionMoveDuration({ x: 0, y: 0 }, { x: 2000, y: 0 }, 0.2), 9000);
  assert.equal(interactionMoveDuration({ x: 0, y: 0 }, { x: 360, y: 0 }, 1), 5000);
});

test("cats can join an active feather wand chase without duplicate followers", () => {
  assert.equal(wandChaseJoinDecision({ active: false, canWalk: true }), "inactive");
  assert.equal(wandChaseJoinDecision({ active: true, alreadyFollowing: true, canWalk: true }), "following");
  assert.equal(wandChaseJoinDecision({ active: true, alreadyFollowing: false, canWalk: false }), "resting");
  assert.equal(wandChaseJoinDecision({ active: true, alreadyFollowing: false, canWalk: true }), "join");
});

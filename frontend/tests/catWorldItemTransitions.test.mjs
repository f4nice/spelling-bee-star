import assert from "node:assert/strict";
import test from "node:test";

import {
  catWorldItemArrivalFollower,
  catWorldItemArrivalPlan,
  catWorldNewVisibleItemArrivals,
} from "../src/app/catWorldItemTransitions.js";

const desk = { id: "study-desk", kind: "decor", label: "英文书桌" };
const ball = { id: "rolling-ball", kind: "toy", label: "滚滚球" };

test("only items newly visible in the same interactive room receive arrival effects", () => {
  assert.deepEqual(
    catWorldNewVisibleItemArrivals([desk], [desk, ball], {
      sameScene: true,
      interactionLocked: false,
    }),
    [ball],
  );
  assert.deepEqual(
    catWorldNewVisibleItemArrivals([], [desk], {
      sameScene: false,
      interactionLocked: false,
    }),
    [],
  );
  assert.deepEqual(
    catWorldNewVisibleItemArrivals([], [desk], {
      sameScene: true,
      interactionLocked: true,
    }),
    [],
  );
});

test("arrival plans stay deterministic and preserve restrained pixel motion", () => {
  const first = catWorldItemArrivalPlan("study-desk", 2);
  const second = catWorldItemArrivalPlan("study-desk", 2);

  assert.deepEqual(first, second);
  assert.equal(first.delay, 170);
  assert.ok(first.duration >= 520 && first.duration <= 655);
  assert.ok(first.lift >= 24 && first.lift <= 36);
  assert.ok(first.startScale >= 0.82 && first.startScale <= 0.9);
  assert.ok(Number.isInteger(first.dustColor));
});

test("a newly placed favorite item attracts one healthy individual cat", () => {
  const follower = catWorldItemArrivalFollower([
    {
      id: "sleepy-cat",
      canWalk: true,
      energy: 38,
      restThreshold: 34,
      curiosity: 90,
      activityBias: 90,
      mood: 90,
    },
    {
      id: "urgent-cat",
      canWalk: true,
      energy: 90,
      restThreshold: 34,
      curiosity: 100,
      activityBias: 90,
      mood: 90,
      carePriority: 92,
    },
    {
      id: "calm-cat",
      canWalk: true,
      energy: 78,
      restThreshold: 34,
      curiosity: 58,
      activityBias: 48,
      mood: 82,
    },
    {
      id: "curious-cat",
      canWalk: true,
      energy: 82,
      restThreshold: 34,
      curiosity: 92,
      activityBias: 78,
      mood: 76,
    },
  ], "study-desk");

  assert.equal(follower, "curious-cat");
});

test("busy, carried, sleeping and waking cats keep their current needs", () => {
  const unavailable = [
    { id: "busy", canWalk: true, energy: 90, restThreshold: 34, busy: true },
    { id: "carried", canWalk: true, energy: 90, restThreshold: 34, carried: true },
    { id: "sleeping", canWalk: true, energy: 90, restThreshold: 34, sleeping: true },
    { id: "waking", canWalk: true, energy: 90, restThreshold: 34, behaviorKey: "waking" },
  ];

  assert.equal(catWorldItemArrivalFollower(unavailable, "cloud-rug"), "");
});

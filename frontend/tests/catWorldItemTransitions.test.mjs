import assert from "node:assert/strict";
import test from "node:test";

import {
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

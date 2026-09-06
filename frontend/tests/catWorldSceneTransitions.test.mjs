import assert from "node:assert/strict";
import test from "node:test";

import {
  catWorldSceneArrivalPlan,
  catWorldSceneMoveForScene,
  catWorldSceneMoveToken,
  normalizeCatWorldSceneMoves,
} from "../src/app/catWorldSceneTransitions.js";

const move = {
  catId: "cat-4b3e",
  catLabel: "迟罗",
  fromSceneId: "yard",
  fromSceneLabel: "猫咪外院",
  toSceneId: "main-room",
  toSceneLabel: "一楼活动室",
  period: "evening",
  occurredAt: "2026-09-07T18:12:00Z",
  reason: "听见你在这里，自己找了过来",
  message: "迟罗从猫咪外院去了一楼活动室。",
};

test("scene moves keep a stable event identity and room-relative direction", () => {
  const [normalized] = normalizeCatWorldSceneMoves([move]);

  assert.equal(normalized.occurredAt, move.occurredAt);
  assert.match(catWorldSceneMoveToken(normalized), /2026-09-07T18:12:00Z/);
  assert.equal(catWorldSceneMoveForScene(normalized, "main-room"), "arrival");
  assert.equal(catWorldSceneMoveForScene(normalized, "yard"), "departure");
  assert.equal(catWorldSceneMoveForScene(normalized, "bedroom"), "remote");
});

test("arrival plan walks from a room edge to the saved destination", () => {
  const bounds = { minX: 38, maxX: 1468, minY: 312, maxY: 490 };
  const plan = catWorldSceneArrivalPlan(move, { x: 720, y: 420 }, bounds, 0.8);
  const repeated = catWorldSceneArrivalPlan(move, { x: 720, y: 420 }, bounds, 0.8);

  assert.deepEqual(plan, repeated);
  assert.ok([bounds.minX, bounds.maxX].includes(plan.startX));
  assert.equal(plan.targetX, 720);
  assert.equal(plan.targetY, 420);
  assert.ok(plan.duration >= 1150 && plan.duration <= 2800);
  assert.equal(plan.facing, plan.targetX >= plan.startX ? 1 : -1);
});

test("invalid scene moves are removed before reaching the renderer", () => {
  assert.deepEqual(normalizeCatWorldSceneMoves([{ catId: "cat-only" }, null]), []);
});

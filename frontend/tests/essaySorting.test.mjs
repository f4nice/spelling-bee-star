import assert from "node:assert/strict";
import test from "node:test";

import { sortEssaysNewestFirst } from "../src/app/essaySorting.js";

test("essays are sorted by newest creation time without using update time", () => {
  const sorted = sortEssaysNewestFirst([
    { id: 10, createdAt: "2026-07-22T13:13:00", updatedAt: "2026-07-28T18:00:00" },
    { id: 12, createdAt: "2026-07-24T10:43:00", updatedAt: "2026-07-24T10:43:00" },
    { id: 11, createdAt: "2026-07-23T20:58:00", updatedAt: "2026-07-23T20:58:00" },
  ]);

  assert.deepEqual(sorted.map((essay) => essay.id), [12, 11, 10]);
});

test("essay id keeps newest-first ordering stable when creation times match", () => {
  const createdAt = "2026-07-24T10:43:00";
  const sorted = sortEssaysNewestFirst([
    { id: 3, createdAt },
    { id: 5, createdAt },
    { id: 4, createdAt },
  ]);

  assert.deepEqual(sorted.map((essay) => essay.id), [5, 4, 3]);
});

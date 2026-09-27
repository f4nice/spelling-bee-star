import assert from "node:assert/strict";
import test from "node:test";
import { catWorldSizeProfile } from "../src/app/catWorldSize.js";

test("breed body sizes create visible small, medium, and large groups", () => {
  assert.equal(catWorldSizeProfile({ id: "maine-coon" }).sizeKey, "large");
  assert.equal(catWorldSizeProfile({ id: "japanese-bobtail" }).sizeKey, "small");
  assert.equal(catWorldSizeProfile({ id: "mimi" }).sizeKey, "medium");
});

test("the same individual keeps its body size stable", () => {
  const first = catWorldSizeProfile({ breedId: "ragdoll", profileCode: "A123" });
  const second = catWorldSizeProfile({ breedId: "ragdoll", profileCode: "A123" });
  assert.deepEqual(second, first);
  assert.ok(first.scale >= 0.78 && first.scale <= 1.26);
});

test("two profiles of one breed can have a playful small difference", () => {
  const sizes = ["A", "B", "C", "D"].map((profileCode) =>
    catWorldSizeProfile({ breedId: "mimi", profileCode }).scale,
  );
  assert.ok(new Set(sizes).size > 1);
});


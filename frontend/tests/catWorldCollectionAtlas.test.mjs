import assert from "node:assert/strict";
import test from "node:test";

import {
  collectionRegionMeta,
  resolveCollectionCat,
  resolveCollectionSection,
} from "../src/app/catWorldCollectionAtlas.js";

const sections = [
  { key: "resident-cats", region: "猫咪世界", cats: [{ id: "mimi" }] },
  {
    key: "region-日本",
    region: "日本",
    cats: [{ id: "japanese-bobtail" }],
  },
  {
    key: "region-土耳其",
    region: "土耳其",
    cats: [{ id: "turkish-van" }, { id: "turkish-angora" }],
  },
];

test("collection atlas opens on the current limited region", () => {
  assert.equal(resolveCollectionSection(sections, "", "土耳其").key, "region-土耳其");
});

test("an explicit map selection takes priority over the current limited region", () => {
  assert.equal(resolveCollectionSection(sections, "region-日本", "土耳其").key, "region-日本");
});

test("cat selection falls back to the first cat in the selected region", () => {
  const turkey = resolveCollectionSection(sections, "region-土耳其", "");
  assert.equal(resolveCollectionCat(turkey, "turkish-angora").id, "turkish-angora");
  assert.equal(resolveCollectionCat(turkey, "missing").id, "turkish-van");
});

test("Turkey has a stable geographical marker on the map", () => {
  const meta = collectionRegionMeta(sections[2], 2);
  assert.deepEqual(meta.style, { left: "58%", top: "39%" });
  assert.equal(meta.shortLabel, "土耳其");
});

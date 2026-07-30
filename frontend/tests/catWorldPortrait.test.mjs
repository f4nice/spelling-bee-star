import test from "node:test";
import assert from "node:assert/strict";

import { catPortraitModel } from "../src/app/catWorldPortrait.js";

test("cat portraits keep the individual pattern and feature", () => {
  const portrait = catPortraitModel({
    id: "siamese-4b3e",
    breedId: "siamese",
    profileCode: "4B3E",
    patternKey: "bold-stripes",
    featureKey: "bright-eyes",
  });

  assert.equal(portrait.pattern, "bold-stripes");
  assert.equal(portrait.feature, "bright-eyes");
  assert.equal(portrait.style["--cat-portrait-body"], "#f1ddbd");
  assert.equal(portrait.style["--cat-portrait-stripe"], "#382c2d");
});

test("cat portrait backgrounds are stable per profile", () => {
  const first = catPortraitModel({ id: "cat-a", breedId: "ragdoll", profileCode: "A101" });
  const repeated = catPortraitModel({ id: "cat-a", breedId: "ragdoll", profileCode: "A101" });
  const another = catPortraitModel({ id: "cat-b", breedId: "ragdoll", profileCode: "B202" });

  assert.equal(first.style["--cat-portrait-backdrop"], repeated.style["--cat-portrait-backdrop"]);
  assert.notEqual(first.style["--cat-portrait-backdrop"], another.style["--cat-portrait-backdrop"]);
});

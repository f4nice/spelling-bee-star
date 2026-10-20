import assert from "node:assert/strict";
import test from "node:test";

import { splitImageFiles } from "../src/app/imageUpload.js";

test("batch image uploads are split below the proxy request budget", () => {
  const files = [
    { name: "one.png", size: 400 * 1024 },
    { name: "two.png", size: 250 * 1024 },
    { name: "three.png", size: 500 * 1024 },
  ];
  const batches = splitImageFiles(files, 700 * 1024);
  assert.deepEqual(batches.map((batch) => batch.map((file) => file.name)), [
    ["one.png", "two.png"],
    ["three.png"],
  ]);
});

test("a single large image remains a batch on its own", () => {
  const file = { name: "large.png", size: 2 * 1024 * 1024 };
  assert.deepEqual(splitImageFiles([file], 700 * 1024), [[file]]);
});

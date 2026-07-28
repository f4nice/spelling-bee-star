import assert from "node:assert/strict";
import test from "node:test";

import {
  importPreviewDestination,
  importPreviewJobPercent,
  importPreviewStageLabel,
  isImportPreviewJobActive,
} from "../src/app/importPreviewJob.js";

test("import preview progress is bounded and completes at 100 percent", () => {
  assert.equal(importPreviewJobPercent({ processed: 250, total: 1000 }), 25);
  assert.equal(importPreviewJobPercent({ processed: 1200, total: 1000 }), 100);
  assert.equal(importPreviewJobPercent({ status: "complete", processed: 0, total: 1000 }), 100);
});

test("import preview status and destination describe the active job", () => {
  assert.equal(isImportPreviewJobActive({ status: "running" }), true);
  assert.equal(isImportPreviewJobActive({ status: "failed" }), false);
  assert.equal(importPreviewStageLabel({ stage: "finalizing" }), "完成导入");
  assert.equal(
    importPreviewDestination({
      result: {
        word_list_id: 12,
        split_word_lists: [{ id: 21 }],
      },
    }),
    "/lists/21",
  );
});

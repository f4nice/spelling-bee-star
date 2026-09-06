import assert from "node:assert/strict";
import test from "node:test";
import { wordRefreshFeedback } from "../src/app/wordRefreshFeedback.js";

const completeWord = {
  phonetic: "/test/", english_definition: "A test.",
  chinese_definition: "测试", english_example: "This is a test.",
  enrichment_status: "done",
};

test("no returned fields is a failure even when the server says done", () => {
  const feedback = wordRefreshFeedback({ word: { enrichment_status: "done", phonetic: "  " } });
  assert.equal(feedback.status, "failed");
  assert.equal(feedback.failed, true);
  assert.match(feedback.notice, /未获取到可用/);
  assert.match(feedback.notice, /音标、英文定义、中文定义、英文例句/);
});

test("partial completion confirms saved content and lists only the missing fields", () => {
  const feedback = wordRefreshFeedback({ word: { ...completeWord, phonetic: null } });
  assert.equal(feedback.status, "partial");
  assert.equal(feedback.failed, false);
  assert.match(feedback.notice, /现有内容已保存，仍缺音标/);
  assert.doesNotMatch(feedback.notice, /英文定义|中文定义|英文例句|重试/);
});

test("all text fields returned shows complete success", () => {
  assert.deepEqual(wordRefreshFeedback({ ok: true, word: completeWord }), {
    status: "complete", failed: false, notice: "补全完成，词条已更新。",
  });
});

test("pending snapshots are not reported as a finished success or failure", () => {
  for (const fields of [{}, completeWord]) {
    const feedback = wordRefreshFeedback({ word: { ...fields, enrichment_status: "pending" } });
    assert.equal(feedback.status, "pending");
    assert.equal(feedback.failed, false);
    assert.match(feedback.notice, /后台仍在补全/);
    assert.doesNotMatch(feedback.notice, /补全完成|补全失败/);
  }
});

test("failed provider with saved partial content is a partial result", () => {
  const feedback = wordRefreshFeedback({ word: {
    ...completeWord, phonetic: "", enrichment_status: "failed",
    enrichment_error: "sensitive upstream response",
  } });
  assert.equal(feedback.status, "partial");
  assert.match(feedback.notice, /现有内容已保存/);
  assert.match(feedback.notice, /查询未完全成功/);
  assert.doesNotMatch(feedback.notice, /sensitive upstream response/);
});

test("failed provider with no fields remains a failure", () => {
  const feedback = wordRefreshFeedback({ word: { enrichment_status: "failed" } });
  assert.equal(feedback.status, "failed");
  assert.equal(feedback.failed, true);
});

test("already complete data does not conceal a failed status or optional source error", () => {
  for (const condition of [{ enrichment_status: "failed" }, { enrichment_error: "audio failed" }]) {
    const feedback = wordRefreshFeedback({ word: { ...completeWord, ...condition } });
    assert.equal(feedback.status, "complete");
    assert.equal(feedback.failed, true);
    assert.match(feedback.notice, /主要内容已齐全并保存/);
    assert.match(feedback.notice, /查询未完全成功/);
    assert.doesNotMatch(feedback.notice, /audio failed/);
  }
});

test("missing or explicitly rejected responses cannot be reported as success", () => {
  assert.throws(() => wordRefreshFeedback(undefined), /未收到补全结果/);
  assert.throws(() => wordRefreshFeedback({ ok: false, word: completeWord }), /服务器未能完成/);
});

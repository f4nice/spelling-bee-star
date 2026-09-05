import assert from "node:assert/strict";
import test from "node:test";
import { requestWordRefresh } from "../src/app/wordRefreshRequest.js";

const word = { id: 20100, word: "folate", enrichment_status: "done", english_definition: "A B vitamin" };
function setup(request, options = {}) {
  const events = [];
  return {
    events,
    run: () => requestWordRefresh({
      request, refreshUrl: "/refresh", detailUrl: "/detail", form: {},
      invalidate: () => events.push("invalidate"),
      onWord: (value) => events.push(["word", value]),
      onDetail: (value) => events.push(["detail", value]),
      pause: async () => {}, recoveryAttempts: 3, ...options,
    }),
  };
}

test("saved POST result is displayed even when detail reload fails", async () => {
  const ctx = setup(async (url) => {
    if (url === "/refresh") {
      assert.deepEqual(ctx.events, ["invalidate"]);
      return { ok: true, word };
    }
    assert.deepEqual(ctx.events[1], ["word", word]);
    throw new Error("detail connection lost");
  });
  assert.equal((await ctx.run()).word, word);
});

test("lost POST response recovers committed data without repeating the mutation", async () => {
  let posts = 0;
  let reads = 0;
  const ctx = setup(async (url, options) => {
    if (url === "/refresh") {
      posts += 1;
      throw Object.assign(new Error("gateway timeout"), { status: 504 });
    }
    assert.equal(options.skipCache, true);
    reads += 1;
    return { word: reads === 1 ? { ...word, enrichment_status: "pending" } : word };
  });
  const result = await ctx.run();
  assert.equal(result.recovered, true);
  assert.equal(result.word, word);
  assert.equal(posts, 1);
  assert.equal(reads, 2);
});

test("a hung request is bounded and recovered from an uncached read", async () => {
  let signal;
  const ctx = setup((url, options) => {
    if (url === "/refresh") {
      signal = options.signal;
      return new Promise(() => {});
    }
    return Promise.resolve({ word });
  }, { refreshTimeoutMs: 5 });
  assert.equal((await ctx.run()).recovered, true);
  assert.equal(signal.aborted, true);
});

test("authorization errors are not retried or reported as success", async () => {
  let calls = 0;
  const ctx = setup(async () => {
    calls += 1;
    throw Object.assign(new Error("not authorized"), { status: 403 });
  });
  await assert.rejects(ctx.run(), /not authorized/);
  assert.equal(calls, 1);
});

test("unconfirmed jobs stop polling and preserve the latest partial data", async () => {
  let calls = 0;
  const partial = { word: { ...word, enrichment_status: "pending" } };
  const ctx = setup(async (url) => {
    calls += 1;
    if (url === "/refresh") throw new Error("network error");
    return partial;
  });
  await assert.rejects(ctx.run(), /暂未确认补全结果/);
  assert.equal(calls, 4);
  assert.deepEqual(ctx.events.at(-1), ["detail", partial]);
});

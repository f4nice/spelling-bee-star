import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  COMPLETION_ACTIVE_STATUSES,
  createListCompletionController,
} from "../src/app/listCompletionJob.js";
import { fetchJson } from "../src/app/utils.js";
import { readApiCache, writeApiCache } from "../src/app/apiCache.js";

const flush = () => new Promise(resolve => setImmediate(resolve));
const makeJob = (overrides = {}) => ({ id: "job-1", status: "running", done: 0, total: 5, ...overrides });

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function harness({ onRefresh } = {}) {
  const calls = [];
  const states = [];
  const refreshes = [];
  const timers = new Map();
  const cleared = [];
  let timerId = 0;
  const controller = createListCompletionController({
    request(url, options) {
      const result = deferred();
      calls.push({ url, options, ...result });
      return result.promise;
    },
    schedule(fn, delay) {
      const id = ++timerId;
      timers.set(id, { fn, delay });
      return id;
    },
    unschedule(id) { timers.delete(id); cleared.push(id); },
    onState(state) { states.push(state); },
    onRefresh(id) {
      refreshes.push(id);
      return onRefresh ? onRefresh(id) : Promise.resolve();
    },
  });
  return {
    controller, calls, states, timers, refreshes, cleared,
    state: () => states.at(-1),
    async respond(index, value) { calls[index].resolve(value); await flush(); },
    async fail(index, error = new Error("Network unavailable")) { calls[index].reject(error); await flush(); },
    poll() {
      assert.equal(timers.size, 1, "exactly one polling timer must be pending");
      const [id, entry] = timers.entries().next().value;
      timers.delete(id);
      void entry.fn();
      return entry.delay;
    },
  };
}

test("queued, running and stopping jobs are active; terminal jobs are not", () => {
  assert.deepEqual([...COMPLETION_ACTIVE_STATUSES].sort(), ["queued", "running", "stopping"]);
  for (const status of ["completed", "stopped", "failed", undefined]) {
    assert.equal(COMPLETION_ACTIVE_STATUSES.has(status), false);
  }
});

test("opening a list restores its raw active job and polls without creating a task", async () => {
  const h = harness();
  h.controller.setList(204);
  assert.equal(h.state().busy, true);
  assert.equal(h.calls[0].url, "/api/vue/lists/204/completion");
  assert.deepEqual(h.calls[0].options, { skipCache: true });
  const job = makeJob({ done: 2 });
  await h.respond(0, job);
  assert.equal(h.state().job, job);
  assert.equal(h.state().busy, false);
  assert.deepEqual(h.refreshes, [204]);
  assert.equal(h.poll(), 2200);
  assert.equal(h.calls[1].url, h.calls[0].url);
  assert.equal(h.calls.filter(call => call.options.method === "POST").length, 0);
  h.controller.dispose();
});

test("a null job stops loading without polling or refreshing", async () => {
  const h = harness();
  h.controller.setList(204);
  await h.respond(0, null);
  assert.deepEqual(h.state(), { job: null, busy: false, notice: "" });
  assert.equal(h.timers.size, 0);
  assert.deepEqual(h.refreshes, []);
});

for (const status of ["completed", "stopped", "failed"]) {
  test(`a restored ${status} job refreshes the list but does not poll`, async () => {
    const h = harness();
    h.controller.setList(204);
    await h.respond(0, makeJob({ status, done: 3 }));
    assert.equal(h.state().job.status, status);
    assert.deepEqual(h.refreshes, [204]);
    assert.equal(h.timers.size, 0);
  });
}

test("start waits for initial restore, deduplicates rapid clicks and sends edit authorization", async () => {
  const h = harness();
  h.controller.setList(204);
  await h.controller.start();
  assert.equal(h.calls.length, 1);
  await h.respond(0, null);
  const starting = h.controller.start();
  await h.controller.start();
  assert.equal(h.calls.length, 2);
  const call = h.calls[1];
  assert.equal(call.url, "/api/vue/lists/204/completion/start");
  assert.equal(call.options.method, "POST");
  assert.equal(call.options.skipCache, true);
  assert.equal(call.options.body.get("edit_token"), "1");
  assert.equal(h.state().busy, true);
  await h.respond(1, makeJob({ status: "queued" }));
  await starting;
  await h.controller.start();
  assert.equal(h.calls.length, 2);
  assert.equal(h.timers.size, 1);
  h.controller.dispose();
});

test("ambiguous start failure only retries a safe GET, never the POST", async () => {
  const h = harness();
  h.controller.setList(204);
  await h.respond(0, null);
  const starting = h.controller.start();
  await h.fail(1, new Error("Connection reset after request"));
  await starting;
  assert.match(h.state().notice, /Connection reset/);
  h.poll();
  assert.equal(h.calls[2].options.method, undefined);
  await h.respond(2, makeJob());
  h.poll();
  await h.respond(3, makeJob({ status: "completed", done: 5 }));
  assert.equal(h.calls.filter(call => call.options.method === "POST").length, 1);
  assert.equal(h.timers.size, 0);
});

test("stop targets the active job, cancels pending poll and tracks stopping until stopped", async () => {
  const h = harness();
  h.controller.setList(204);
  await h.respond(0, makeJob({ id: "abc-123", done: 1 }));
  const stopping = h.controller.stop();
  assert.equal(h.timers.size, 0);
  assert.equal(h.calls[1].url, "/api/vue/lists/204/completion/abc-123/stop");
  assert.equal(h.calls[1].options.body.get("edit_token"), "1");
  await h.controller.stop();
  assert.equal(h.calls.length, 2);
  await h.respond(1, makeJob({ id: "abc-123", status: "stopping", done: 1 }));
  await stopping;
  h.poll();
  await h.respond(2, makeJob({ id: "abc-123", status: "stopped", done: 2 }));
  assert.equal(h.timers.size, 0);
  await h.controller.stop();
  assert.equal(h.calls.length, 3);
});

for (const outcome of ["success", "failure"]) {
  test(`a stale in-flight GET ${outcome} cannot overwrite a newer stop response or replace its poll`, async () => {
    const h = harness();
    h.controller.setList(204);
    await h.respond(0, makeJob({ done: 1 }));
    h.poll();
    assert.equal(h.calls[1].options.method, undefined);
    const stopping = h.controller.stop();
    assert.equal(h.calls[2].options.method, "POST");
    await h.respond(2, makeJob({ status: "stopping", done: 2 }));
    await stopping;
    const state = h.state();
    const stateCount = h.states.length;
    const timers = [...h.timers.entries()];
    const refreshCount = h.refreshes.length;
    if (outcome === "success") await h.respond(1, makeJob({ status: "running", done: 1 }));
    else await h.fail(1);
    assert.equal(h.state(), state);
    assert.equal(h.state().job.status, "stopping");
    assert.equal(h.states.length, stateCount);
    assert.equal(h.refreshes.length, refreshCount);
    assert.deepEqual([...h.timers.entries()], timers, "only the new stop response's poll remains");
    assert.equal(h.poll(), 2200);
    await h.respond(3, makeJob({ status: "stopped", done: 2 }));
    assert.equal(h.state().job.status, "stopped");
    assert.equal(h.timers.size, 0);
  });
}

test("stop does not send a request when no job exists", async () => {
  const h = harness();
  await h.controller.stop();
  h.controller.setList(204);
  await h.respond(0, null);
  await h.controller.stop();
  assert.equal(h.calls.length, 1);
});

test("route changes discard stale GET responses and clear old polling", async () => {
  const h = harness();
  h.controller.setList(204);
  h.controller.setList(205);
  await h.respond(1, makeJob({ id: "new-list-job" }));
  await h.respond(0, makeJob({ id: "old-list-job", done: 4 }));
  assert.equal(h.state().job.id, "new-list-job");
  assert.deepEqual(h.refreshes, [205]);
  assert.equal(h.timers.size, 1);
  h.controller.setList(206);
  assert.equal(h.timers.size, 0);
  assert.equal(h.state().job, null);
  assert.equal(h.calls[2].url, "/api/vue/lists/206/completion");
  h.controller.dispose();
});

test("route changes discard late POST success without refreshing or polling the wrong list", async () => {
  const h = harness();
  h.controller.setList(204);
  await h.respond(0, null);
  const starting = h.controller.start();
  h.controller.setList(205);
  await h.respond(2, null);
  await h.respond(1, makeJob());
  await starting;
  assert.deepEqual(h.state(), { job: null, busy: false, notice: "" });
  assert.deepEqual(h.refreshes, []);
  assert.equal(h.timers.size, 0);
});

test("route changes discard late POST failure without overwriting the current list notice", async () => {
  const h = harness();
  h.controller.setList(204);
  await h.respond(0, null);
  const starting = h.controller.start();
  h.controller.setList(205);
  await h.respond(2, null);
  await h.fail(1);
  await starting;
  assert.equal(h.state().notice, "");
  assert.equal(h.timers.size, 0);
});

test("dispose clears polls, ignores pending responses and prevents subsequent mutations", async () => {
  const h = harness();
  h.controller.setList(204);
  await h.respond(0, makeJob());
  assert.equal(h.timers.size, 1);
  h.poll();
  h.controller.dispose();
  const state = h.state();
  await h.respond(1, makeJob({ done: 4 }));
  assert.equal(h.state(), state);
  assert.equal(h.timers.size, 0);
  await h.controller.start();
  await h.controller.stop();
  assert.equal(h.calls.length, 2);
  const other = harness();
  other.controller.setList(204);
  await other.respond(0, makeJob());
  other.controller.dispose();
  assert.equal(other.timers.size, 0);
  assert.ok(other.cleared.length > 0);
});

test("read errors use bounded backoff and successful progress resets retry delay", async () => {
  const h = harness();
  h.controller.setList(204);
  for (let index = 0; index < 11; index += 1) {
    await h.fail(index);
    assert.match(h.state().notice, /正在重连/);
    assert.equal(h.poll(), Math.min(30000, (index + 1) * 3000));
  }
  await h.respond(11, makeJob());
  assert.equal(h.state().notice, "");
  assert.equal(h.poll(), 2200);
  await h.fail(12);
  assert.equal(h.poll(), 3000);
  h.controller.dispose();
});

for (const status of [401, 404]) {
  test(`read status ${status} stops automatic retry`, async () => {
    const h = harness();
    h.controller.setList(204);
    await h.fail(0, Object.assign(new Error("unavailable"), { status }));
    assert.equal(h.state().busy, false);
    assert.equal(h.timers.size, 0);
    if (status === 401) assert.match(h.state().notice, /登录已失效/);
  });
}

test("unauthorized mutations do not retry or repeat POST", async () => {
  const h = harness();
  h.controller.setList(204);
  await h.respond(0, null);
  const starting = h.controller.start();
  await h.fail(1, Object.assign(new Error("Please log in"), { status: 401 }));
  await starting;
  assert.equal(h.timers.size, 0);
  assert.equal(h.calls.length, 2);
});

test("progress refresh is throttled, but terminal progress refreshes immediately", async () => {
  const originalNow = Date.now;
  let now = 100000;
  Date.now = () => now;
  try {
    const h = harness();
    h.controller.setList(204);
    await h.respond(0, makeJob());
    assert.equal(h.refreshes.length, 1);
    now += 2200;
    h.poll();
    await h.respond(1, makeJob({ done: 1 }));
    assert.equal(h.refreshes.length, 1);
    now += 8000;
    h.poll();
    await h.respond(2, makeJob({ done: 2 }));
    assert.equal(h.refreshes.length, 2);
    now += 2200;
    h.poll();
    await h.respond(3, makeJob({ status: "completed", done: 5 }));
    assert.equal(h.refreshes.length, 3);
    assert.equal(h.timers.size, 0);
  } finally {
    Date.now = originalNow;
  }
});

test("a terminal status refreshes once even when its done count matches the preceding active update", async () => {
  const h = harness();
  h.controller.setList(204);
  await h.respond(0, makeJob({ done: 3 }));
  h.poll();
  await h.respond(1, makeJob({ status: "stopped", done: 3 }));
  assert.deepEqual(h.refreshes, [204, 204]);
  assert.equal(h.timers.size, 0);
});

test("a disappeared job reports restart, refreshes persisted data and stops polling", async () => {
  const h = harness();
  h.controller.setList(204);
  await h.respond(0, makeJob({ done: 2 }));
  h.poll();
  await h.respond(1, null);
  assert.equal(h.state().job, null);
  assert.match(h.state().notice, /服务已重启/);
  assert.deepEqual(h.refreshes, [204, 204]);
  assert.equal(h.timers.size, 0);
});

test("failed list refresh keeps polling and retries unchanged progress after the throttle window", async () => {
  const originalNow = Date.now;
  let now = 100000;
  Date.now = () => now;
  try {
    let refreshCalls = 0;
    const h = harness({ onRefresh: () => ++refreshCalls === 1 ? Promise.reject(new Error("refresh failed")) : Promise.resolve() });
    h.controller.setList(204);
    await h.respond(0, makeJob({ done: 2 }));
    assert.match(h.state().notice, /词表暂时刷新失败/);
    assert.equal(h.timers.size, 1);
    now += 8000;
    h.poll();
    await h.respond(1, makeJob({ done: 2 }));
    assert.deepEqual(h.refreshes, [204, 204]);
    h.controller.dispose();
  } finally {
    Date.now = originalNow;
  }
});

test("a terminal list-refresh failure schedules one safe read and retries the refresh", async () => {
  let refreshCalls = 0;
  const h = harness({ onRefresh: () => ++refreshCalls === 1 ? Promise.reject(new Error("refresh failed")) : Promise.resolve() });
  h.controller.setList(204);
  await h.respond(0, makeJob({ status: "completed", done: 5 }));
  assert.match(h.state().notice, /词表暂时刷新失败/);
  assert.equal(h.poll(), 10000);
  await h.respond(1, makeJob({ status: "completed", done: 5 }));
  assert.deepEqual(h.refreshes, [204, 204]);
  assert.equal(h.timers.size, 0);
});

test("refresh retries even after a disappeared job leaves subsequent status reads null", async () => {
  let refreshCalls = 0;
  const h = harness({ onRefresh: () => ++refreshCalls === 2 ? Promise.reject(new Error("refresh failed")) : Promise.resolve() });
  h.controller.setList(204);
  await h.respond(0, makeJob({ done: 2 }));
  h.poll();
  await h.respond(1, null);
  assert.match(h.state().notice, /词表暂时刷新失败/);
  assert.equal(h.poll(), 10000);
  await h.respond(2, null);
  assert.deepEqual(h.refreshes, [204, 204, 204]);
  assert.equal(h.timers.size, 0);
});

test("a stale list-refresh rejection cannot reset the new list's progress or schedule a poll", async () => {
  const oldRefresh = deferred();
  const h = harness({ onRefresh: id => id === 204 ? oldRefresh.promise : Promise.resolve() });
  h.controller.setList(204);
  await h.respond(0, makeJob({ done: 1 }));
  h.controller.setList(205);
  await h.respond(1, makeJob({ status: "completed", done: 5 }));
  const state = h.state();
  oldRefresh.reject(new Error("old route failed"));
  await flush();
  assert.equal(h.state(), state);
  assert.equal(h.timers.size, 0);
  assert.deepEqual(h.refreshes, [204, 205]);
});

test("uncached completion status GET invalidates every shared word/list cache but preserves newspaper", async () => {
  const originalWindow = globalThis.window;
  const originalFetch = globalThis.fetch;
  const entries = new Map();
  const sessionStorage = {
    get length() { return entries.size; },
    key(index) { return [...entries.keys()][index] ?? null; },
    getItem(key) { return entries.get(key) ?? null; },
    setItem(key, value) { entries.set(key, String(value)); },
    removeItem(key) { entries.delete(key); },
  };
  globalThis.window = { sessionStorage };
  let fetchCalls = 0;
  const freshJob = makeJob({ done: 3 });
  globalThis.fetch = async (url, options) => {
    fetchCalls += 1;
    assert.equal(url, "/api/vue/lists/204/completion");
    assert.equal(options.skipCache, undefined, "skipCache is an internal flag, not a fetch option");
    return { ok: true, headers: new Headers({ "content-type": "application/json" }), json: async () => freshJob };
  };
  try {
    const paths = ["/api/vue/words/20101", "/api/vue/words/22043?list_id=211", "/api/vue/lists", "/api/vue/lists/204", "/api/vue/lists/211", "/api/vue/home"];
    for (const path of paths) writeApiCache(path, { stale: path });
    const newspaper = { sections: [{ title: "News" }] };
    writeApiCache("/api/vue/newspaper", newspaper);
    writeApiCache("/api/vue/shell", { username: "test" });
    writeApiCache("/api/vue/lists/204/completion", makeJob({ done: 0 }));
    assert.equal(readApiCache("/api/vue/lists/204/completion").done, 0);
    assert.equal(await fetchJson("/api/vue/lists/204/completion", { skipCache: true }), freshJob);
    assert.equal(fetchCalls, 1);
    for (const path of paths) assert.equal(readApiCache(path), null, `${path} must be invalidated`);
    assert.equal(readApiCache("/api/vue/lists/204/completion"), null);
    assert.deepEqual(readApiCache("/api/vue/newspaper"), newspaper);
    assert.deepEqual(readApiCache("/api/vue/shell"), { username: "test" });
  } finally {
    if (originalWindow === undefined) delete globalThis.window;
    else globalThis.window = originalWindow;
    globalThis.fetch = originalFetch;
  }
});

test("toolbar requires explicit confirmation, shows progress, and disposes its list-scoped controller", () => {
  const source = readFileSync(new URL("../src/app/components/ListCompletionToolbar.vue", import.meta.url), "utf8");
  assert.match(source, /@click="confirming = true"/);
  assert.match(source, /v-if="confirming"/);
  assert.match(source, /@click="start"/);
  assert.match(source, /@click="controller\.stop\(\)"/);
  assert.match(source, /<progress[^>]+:value="job\.done"/);
  assert.match(source, /onUnmounted\(\(\) => controller\.dispose\(\)\)/);
  assert.match(source, /watch\(\(\) => props\.wordListId/);
  assert.match(source, /\["partial", "failed"\]\.includes\(item\.status\)/);
  assert.match(source, /item\.status === "skipped" && item\.missing_fields\?\.length/);
  assert.match(source, /不生成图片/);
});

test("resource panel wires the batch toolbar to the whole list's incomplete count above image generation", () => {
  const source = readFileSync(new URL("../src/app/components/ListDetailWordGrid.vue", import.meta.url), "utf8");
  const toolbar = source.match(/<ListCompletionToolbar[\s\S]*?\/>/)?.[0];
  assert.ok(toolbar);
  assert.match(toolbar, /:word-list-id="Number\(data\.word_list\.id\)"/);
  assert.match(toolbar, /:incomplete-count="resourceCounts\.incomplete"/);
  assert.match(toolbar, /:refresh-list-detail="refreshListDetail"/);
  assert.ok(source.indexOf("<ListCompletionToolbar") < source.indexOf('<div class="list-ai-image-toolbar"'));
});

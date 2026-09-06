import assert from "node:assert/strict";
import test from "node:test";
import { readApiCache, writeApiCache, invalidateApiCacheForMutation } from "../src/app/apiCache.js";
import { routeApiPaths } from "../src/app/routeApiPaths.js";

const values = new Map();
globalThis.window = { sessionStorage: {
  getItem: (key) => values.get(key) ?? null,
  setItem: (key, value) => values.set(key, value),
  removeItem: (key) => values.delete(key),
  key: (index) => [...values.keys()][index],
  get length() { return values.size; },
} };
const url = "/api/vue/newspaper";
const payload = { sections: [{ key: "today", articles: [{ title: "News" }] }], cache: { stale: false, refreshing: false } };

test("newspaper list and articles cache, refresh invalidates both", () => {
  values.clear();
  writeApiCache(url, payload);
  writeApiCache(`${url}/today/0?url=article-a`, { article: { body: "Body" } });
  assert.deepEqual(readApiCache(url), payload);
  assert.equal(readApiCache(`${url}/today/0?url=article-a`).article.body, "Body");
  invalidateApiCacheForMutation(`${url}/refresh`);
  assert.equal(readApiCache(url), null);
  assert.equal(readApiCache(`${url}/today/0?url=article-a`), null);
});

test("loading, stale and error snapshots never get stuck in browser cache", () => {
  for (const cache of [{ refreshing: true }, { stale: true }, { error: "network" }]) {
    values.clear();
    writeApiCache(url, { ...payload, cache });
    assert.equal(readApiCache(url), null);
  }
});

test("newspaper list expires after five minutes and does not cross midnight", () => {
  values.clear();
  values.set(`speakeasy.apiCache:${url}`, JSON.stringify({ createdAt: Date.now() - 301000, payload }));
  assert.equal(readApiCache(url), null);
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  values.set(`speakeasy.apiCache:${url}`, JSON.stringify({ createdAt: yesterday.getTime(), payload }));
  assert.equal(readApiCache(url), null);
});

test("article URLs are pinned independently of a changing index", () => {
  const article = "https://www.chinadaily.com.cn/a/202609/06/content_123.html";
  const path = routeApiPaths.newspaperArticle({ params: { section: "today", index: 0 }, query: { url: article } });
  assert.equal(new URL(path, "https://www.newabby.com").searchParams.get("url"), article);
  assert.equal(routeApiPaths.newspaperArticle({ params: { section: "today", index: 0 } }), `${url}/today/0`);
});

test("word editing invalidates all cached navigation variants", () => {
  values.clear();
  writeApiCache("/api/vue/words/20101?edit=1&list_id=204", { word: { word: "old" } });
  writeApiCache("/api/vue/words/20101?edit=0", { word: { word: "old" } });
  invalidateApiCacheForMutation("/api/vue/words/20101/refresh");
  assert.equal(readApiCache("/api/vue/words/20101?edit=1&list_id=204"), null);
  assert.equal(readApiCache("/api/vue/words/20101?edit=0"), null);
});

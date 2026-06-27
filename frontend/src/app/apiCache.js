const CACHE_PREFIX = "speakeasy.apiCache:";

const CACHE_RULES = [
  { test: (url) => url.startsWith("/api/vue/words/"), ttl: 2 * 60 * 1000 },
  { test: (url) => url.startsWith("/api/vue/lists"), ttl: 60 * 1000 },
  { test: (url) => url === "/api/vue/shell", ttl: 30 * 1000 },
  { test: (url) => url.startsWith("/api/vue/challenge-calendar/"), ttl: 5 * 60 * 1000 },
  { test: (url) => url === "/api/vue/home", ttl: 30 * 1000 },
  { test: (url) => url.startsWith("/booklearner/api/science-daily"), ttl: 30 * 60 * 1000 },
  { test: (url) => /^\/api\/challenge\/\d+\/state\?/.test(url), ttl: 15 * 1000 },
];

function cacheKey(url) {
  return `${CACHE_PREFIX}${url}`;
}

function cacheTtl(url) {
  return CACHE_RULES.find((rule) => rule.test(url))?.ttl || 0;
}

function storage() {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function readApiCache(url) {
  const ttl = cacheTtl(url);
  const store = storage();
  if (!ttl || !store) return null;
  try {
    const item = JSON.parse(store.getItem(cacheKey(url)) || "null");
    if (!item || Date.now() - item.createdAt > ttl) {
      store.removeItem(cacheKey(url));
      return null;
    }
    return item.payload;
  } catch {
    store.removeItem(cacheKey(url));
    return null;
  }
}

export function writeApiCache(url, payload) {
  const ttl = cacheTtl(url);
  const store = storage();
  if (!ttl || !store || payload == null) return;
  try {
    store.setItem(cacheKey(url), JSON.stringify({ createdAt: Date.now(), payload }));
  } catch {
    clearApiCache();
  }
}

export function clearApiCache(predicate = () => true) {
  const store = storage();
  if (!store) return;
  for (let index = store.length - 1; index >= 0; index -= 1) {
    const key = store.key(index);
    if (key?.startsWith(CACHE_PREFIX) && predicate(key.slice(CACHE_PREFIX.length))) {
      store.removeItem(key);
    }
  }
}

export function invalidateApiCacheForMutation(url) {
  if (url.startsWith("/api/vue/words/")) {
    const wordId = url.split("/")[4];
    clearApiCache((key) => key.startsWith(`/api/vue/words/${wordId}`) || key.startsWith("/api/vue/lists"));
    return;
  }
  if (url.startsWith("/api/vue/lists")) {
    clearApiCache((key) => key.startsWith("/api/vue/lists") || key === "/api/vue/home");
    return;
  }
  if (/^\/api\/challenge\/\d+\/answer/.test(url)) {
    const wordListId = url.split("/")[3];
    clearApiCache((key) => key.startsWith(`/api/challenge/${wordListId}/state`));
  }
}

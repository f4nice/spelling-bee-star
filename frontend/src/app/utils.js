import { invalidateApiCacheForMutation, readApiCache, writeApiCache } from "./apiCache.js";

export async function fetchJson(url, options) {
  const method = (options?.method || "GET").toUpperCase();
  const skipCache = Boolean(options?.skipCache);
  const requestOptions = options ? { ...options } : undefined;
  if (requestOptions) delete requestOptions.skipCache;
  if (method === "GET" && !skipCache) {
    const cached = readApiCache(url);
    if (cached) return cached;
  }

  const response = await fetch(url, requestOptions);
  const isJson = response.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await response.json() : null;
  if (!response.ok) throw new Error(payloadErrorMessage(payload));

  if (method === "GET" && !skipCache) {
    writeApiCache(url, payload);
  } else {
    invalidateApiCacheForMutation(url);
  }
  return payload;
}

function payloadErrorMessage(payload) {
  const detail = payload?.detail || payload?.error;
  if (!detail) return "页面数据加载失败";
  if (typeof detail === "string") return detail;
  if (typeof detail.message === "string") return detail.message;
  if (typeof detail.msg === "string") return detail.msg;
  return "页面数据加载失败";
}

export function imageForWord(word) {
  return word?.image_url || "";
}

export function fallbackLetter(word) {
  return (word?.word || "?").slice(0, 1).toUpperCase();
}

export function wordDetailUrl(word, listId = null) {
  const params = new URLSearchParams();
  params.set("edit", "1");
  if (listId) params.set("list_id", listId);
  return `/words/${word.id}?${params.toString()}`;
}

export function articleText(article) {
  return String(article?.body || article?.excerpt || article?.summary || "").split("\n").filter((item) => item.trim());
}

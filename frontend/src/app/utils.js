import { invalidateApiCacheForMutation, readApiCache, writeApiCache } from "./apiCache.js";

export async function fetchJson(url, options) {
  const method = (options?.method || "GET").toUpperCase();
  if (method === "GET") {
    const cached = readApiCache(url);
    if (cached) return cached;
  }

  const response = await fetch(url, options);
  const isJson = response.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await response.json() : null;
  if (!response.ok) throw new Error(payload?.detail || payload?.error || "页面数据加载失败");

  if (method === "GET") {
    writeApiCache(url, payload);
  } else {
    invalidateApiCacheForMutation(url);
  }
  return payload;
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

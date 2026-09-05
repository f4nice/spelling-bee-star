const REQUIRED_TEXT = ["phonetic", "english_definition", "chinese_definition", "english_example"];

async function timedRequest(request, url, options, timeoutMs) {
  const controller = new AbortController();
  let timer;
  try {
    return await Promise.race([
      request(url, { ...options, signal: controller.signal }),
      new Promise((_, reject) => {
        timer = setTimeout(() => {
          controller.abort();
          reject(new Error("补全请求等待较久，正在核对服务器已保存的结果。"));
        }, timeoutMs);
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}

// A slow proxy response is not proof that the database operation failed.
// Never repeat the mutation automatically: recover using uncached reads only.
export async function requestWordRefresh({
  request, refreshUrl, detailUrl, form, onWord, onDetail, invalidate,
  pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
  refreshTimeoutMs = 45000, readTimeoutMs = 8000, recoveryAttempts = 12,
}) {
  invalidate(); // Also clear stale empty entries when the POST never returns.
  let result;
  try {
    result = await timedRequest(request, refreshUrl, { method: "POST", body: form }, refreshTimeoutMs);
    if (!result?.word) throw new Error("未收到补全结果。");
  } catch (error) {
    if (error?.status >= 400 && error.status < 500 && error.status !== 408) throw error;
    for (let attempt = 0; attempt < recoveryAttempts; attempt += 1) {
      if (attempt) await pause(1500);
      let detail;
      try {
        detail = await timedRequest(request, detailUrl, { skipCache: true }, readTimeoutMs);
      } catch (readError) {
        if (readError?.status === 401 || readError?.status === 403) throw readError;
        continue;
      }
      if (!detail?.word) continue;
      onDetail(detail);
      const word = detail.word;
      if (["done", "failed"].includes(word.enrichment_status)
          || (!word.enrichment_status && REQUIRED_TEXT.every((field) => String(word[field] || "").trim()))) {
        invalidate();
        return { ok: true, word, recovered: true };
      }
    }
    throw new Error("暂未确认补全结果，已保留现有内容。后台可能仍在处理，请稍后重试。");
  }

  onWord(result.word); // Show saved text even if the following detail GET fails.
  invalidate();
  try {
    const detail = await timedRequest(request, detailUrl, { skipCache: true }, readTimeoutMs);
    if (detail?.word) onDetail(detail);
  } catch {
    // The POST already succeeded; a failed secondary read must not undo it.
  }
  return result;
}

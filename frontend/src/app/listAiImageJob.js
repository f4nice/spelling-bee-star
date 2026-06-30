import { fetchJson } from "./utils.js";
import { listApiPaths } from "./listApiPaths.js";

const FINAL_STATUSES = new Set(["complete", "failed"]);

function visibleImageCount(job) {
  return Math.max(Number(job?.generated || 0), 0) + Math.max(Number(job?.skipped || 0), 0);
}

async function runOptionalHandler(handler, job) {
  if (!handler) return;
  try {
    await handler(job);
  } catch {
    // Keep polling even if a page refresh is interrupted.
  }
}

export async function runListAiImageJob({ wordListId, setJob, onProgress, onComplete, allowPaid = false }) {
  const job = await fetchJson(listApiPaths.aiImagesStart(wordListId, allowPaid), {
    method: "POST",
    skipCache: true,
  });
  setJob(job);
  let lastVisibleImageCount = visibleImageCount(job);

  if (FINAL_STATUSES.has(job.status)) {
    await runOptionalHandler(onComplete, job);
    return;
  }

  const poll = async () => {
    try {
      const next = await fetchJson(listApiPaths.aiImagesStatus(wordListId, job.id), { skipCache: true });
      setJob(next);
      const nextVisibleImageCount = visibleImageCount(next);
      if (nextVisibleImageCount > lastVisibleImageCount) {
        lastVisibleImageCount = nextVisibleImageCount;
        await runOptionalHandler(onProgress, next);
      }
      if (FINAL_STATUSES.has(next.status)) {
        await runOptionalHandler(onComplete, next);
        return;
      }
      window.setTimeout(poll, 1600);
    } catch (error) {
      setJob({
        ...job,
        status: "failed",
        message: error.message || "批量 AI 生图进度读取失败",
      });
    }
  };

  window.setTimeout(poll, 1600);
}

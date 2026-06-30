import { fetchJson } from "./utils.js";
import { listApiPaths } from "./listApiPaths.js";

const FINAL_STATUSES = new Set(["complete", "failed"]);

export async function runListAiImageJob({ wordListId, setJob, onComplete, allowPaid = false }) {
  const job = await fetchJson(listApiPaths.aiImagesStart(wordListId, allowPaid), {
    method: "POST",
    skipCache: true,
  });
  setJob(job);

  const timer = window.setInterval(async () => {
    try {
      const next = await fetchJson(listApiPaths.aiImagesStatus(wordListId, job.id), { skipCache: true });
      setJob(next);
      if (FINAL_STATUSES.has(next.status)) {
        window.clearInterval(timer);
        await onComplete();
      }
    } catch (error) {
      window.clearInterval(timer);
      setJob({
        ...job,
        status: "failed",
        message: error.message || "批量 AI 生图进度读取失败",
      });
    }
  }, 1600);
}

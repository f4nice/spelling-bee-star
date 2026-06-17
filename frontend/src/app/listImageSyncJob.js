import { fetchJson } from "./utils.js";
import { listApiPaths } from "./listApiPaths.js";

export async function runListImageSyncJob({ wordListId, setJob, onComplete }) {
  const job = await fetchJson(listApiPaths.syncImagesStart(wordListId), { method: "POST" });
  setJob(job);

  const timer = window.setInterval(async () => {
    const next = await fetchJson(listApiPaths.syncImagesStatus(wordListId, job.id));
    setJob(next);
    if (["done", "failed"].includes(next.status)) {
      window.clearInterval(timer);
      await onComplete();
    }
  }, 1200);
}

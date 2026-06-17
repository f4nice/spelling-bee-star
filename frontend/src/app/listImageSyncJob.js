import { fetchJson } from "./utils.js";

export async function runListImageSyncJob({ wordListId, setJob, onComplete }) {
  const job = await fetchJson(`/api/vue/lists/${wordListId}/sync-images/start`, { method: "POST" });
  setJob(job);

  const timer = window.setInterval(async () => {
    const next = await fetchJson(`/api/vue/lists/${wordListId}/sync-images/${job.id}`);
    setJob(next);
    if (["done", "failed"].includes(next.status)) {
      window.clearInterval(timer);
      await onComplete();
    }
  }, 1200);
}

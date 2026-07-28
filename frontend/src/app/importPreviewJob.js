export const activeImportPreviewStatuses = new Set(["queued", "running"]);

export function isImportPreviewJobActive(job) {
  return activeImportPreviewStatuses.has(job?.status);
}

export function importPreviewJobPercent(job) {
  if (job?.status === "complete") return 100;
  const total = Math.max(Number(job?.total) || 0, 0);
  const processed = Math.min(Math.max(Number(job?.processed) || 0, 0), total);
  return total ? Math.round((processed / total) * 100) : 0;
}

export function importPreviewStageLabel(job) {
  const labels = {
    queued: "准备导入",
    importing: "拆分并写入",
    finalizing: "完成导入",
    complete: "导入完成",
    failed: "导入失败",
  };
  return labels[job?.stage] || "导入处理中";
}

export function importPreviewDestination(job) {
  const result = job?.result;
  const firstSplitList = result?.split_word_lists?.[0]?.id;
  const wordListId = firstSplitList || result?.word_list_id;
  return wordListId ? `/lists/${wordListId}` : "";
}

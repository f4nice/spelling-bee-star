import { onBeforeUnmount, ref, watch } from "vue";
import { coreApiPaths } from "../coreApiPaths.js";
import { fetchJson } from "../utils.js";
import { createImportPreviewSubmitForm } from "../forms/importPreviewSubmitForm.js";
import {
  importPreviewDestination,
  isImportPreviewJobActive,
} from "../importPreviewJob.js";

export function useImportPreviewSubmit({ data, route, go, setError, importForm }) {
  const isImporting = ref(false);
  const importJob = ref(null);
  let pollTimer = null;
  let pollFailures = 0;

  function clearPollTimer() {
    if (pollTimer) window.clearTimeout(pollTimer);
    pollTimer = null;
  }

  function finishImport(job) {
    const destination = importPreviewDestination(job);
    if (destination && route.value.name === "preview" && route.value.params.id === job.id) {
      go(destination);
    }
  }

  function applyImportJob(job) {
    importJob.value = job;
    isImporting.value = isImportPreviewJobActive(job);
    if (job?.status === "complete") finishImport(job);
  }

  function schedulePoll(jobId) {
    clearPollTimer();
    pollTimer = window.setTimeout(() => pollImportJob(jobId), 1000);
  }

  async function pollImportJob(jobId, { quietMissing = false } = {}) {
    clearPollTimer();
    try {
      const payload = await fetchJson(coreApiPaths.importPreviewStatus(jobId), { skipCache: true });
      pollFailures = 0;
      applyImportJob(payload.job);
      if (isImportPreviewJobActive(payload.job)) schedulePoll(jobId);
    } catch (error) {
      if (quietMissing && error.status === 404) return;
      if (route.value.name !== "preview" || route.value.params.id !== jobId) return;
      if (error.status === 404 && isImportPreviewJobActive(importJob.value)) {
        applyImportJob({
          ...importJob.value,
          status: "failed",
          stage: "failed",
          message: "导入任务已中断，原文件仍保留，可以重新确认导入。",
        });
        return;
      }
      if (isImportPreviewJobActive(importJob.value) && pollFailures < 3) {
        pollFailures += 1;
        schedulePoll(jobId);
        return;
      }
      setError(error.message || "读取导入进度失败，请刷新页面重试。");
    }
  }

  async function submitImport() {
    if (isImporting.value) return;
    if (!importForm.value.word_columns.length) {
      setError("请至少选择一个英文单词列");
      return;
    }
    setError("");
    isImporting.value = true;
    try {
      const form = createImportPreviewSubmitForm({
        previewId: route.value.params.id,
        preview: data.value.preview,
        importForm: importForm.value,
      });
      const result = await fetchJson(coreApiPaths.importPreview(), { method: "POST", body: form });
      applyImportJob(result.job);
      if (isImportPreviewJobActive(result.job)) schedulePoll(result.job.id);
    } catch (error) {
      isImporting.value = false;
      setError(error.message || "导入失败，请稍后重试。");
    }
  }

  watch(
    () => [route.value.name, route.value.params.id],
    ([routeName, previewId]) => {
      clearPollTimer();
      pollFailures = 0;
      importJob.value = null;
      isImporting.value = false;
      if (routeName === "preview" && previewId) {
        pollImportJob(previewId, { quietMissing: true });
      }
    },
    { immediate: true },
  );

  onBeforeUnmount(clearPollTimer);

  return {
    importJob,
    isImporting,
    submitImport,
  };
}

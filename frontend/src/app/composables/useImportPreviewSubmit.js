import { ref } from "vue";
import { coreApiPaths } from "../coreApiPaths.js";
import { fetchJson } from "../utils.js";
import { createImportPreviewSubmitForm } from "../forms/importPreviewSubmitForm.js";

export function useImportPreviewSubmit({ data, route, go, setError, importForm }) {
  const isImporting = ref(false);

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
      const firstSplitList = result.split_word_lists?.[0]?.id;
      go(`/lists/${firstSplitList || result.word_list_id}`);
    } catch (error) {
      setError(error.message || "导入失败，请稍后重试。");
    } finally {
      isImporting.value = false;
    }
  }

  return {
    isImporting,
    submitImport,
  };
}

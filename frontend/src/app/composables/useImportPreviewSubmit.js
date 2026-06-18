import { coreApiPaths } from "../coreApiPaths.js";
import { fetchJson } from "../utils.js";
import { createImportPreviewSubmitForm } from "../forms/importPreviewSubmitForm.js";

export function useImportPreviewSubmit({ data, route, go, setError, importForm }) {
  async function submitImport() {
    if (!importForm.value.word_columns.length) {
      setError("请至少选择一个英文单词列");
      return;
    }
    const form = createImportPreviewSubmitForm({
      previewId: route.value.params.id,
      preview: data.value.preview,
      importForm: importForm.value,
    });
    const result = await fetchJson(coreApiPaths.importPreview(), { method: "POST", body: form });
    go(`/lists/${result.word_list_id}`);
  }

  return {
    submitImport,
  };
}

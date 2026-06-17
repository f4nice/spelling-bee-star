import { coreApiPaths } from "../coreApiPaths.js";
import { fetchJson } from "../utils.js";

export function useImportPreviewSubmit({ data, route, go, setError, importForm }) {
  async function submitImport() {
    if (!importForm.value.word_columns.length) {
      setError("请至少选择一个英文单词列");
      return;
    }
    const form = new FormData();
    form.append("preview_id", route.value.params.id);
    form.append("word_list_id", data.value.preview.word_list_id || "");
    form.append("word_list_name", importForm.value.word_list_name);
    importForm.value.word_columns.forEach((item) => form.append("word_columns", item));
    importForm.value.selected_rows.forEach((item) => form.append("selected_rows", item));
    importForm.value.selected_columns.forEach((item) => form.append("selected_columns", item));
    importForm.value.image_files.forEach((item) => form.append("image_files", item));
    const result = await fetchJson(coreApiPaths.importPreview(), { method: "POST", body: form });
    go(`/lists/${result.word_list_id}`);
  }

  return {
    submitImport,
  };
}

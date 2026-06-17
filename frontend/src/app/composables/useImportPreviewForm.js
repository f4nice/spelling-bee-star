import { ref } from "vue";

export function useImportPreviewForm({ data, route, loadRoute }) {
  const importForm = ref({ word_list_name: "", word_columns: [], selected_rows: [], selected_columns: [], image_files: [] });

  function resetImportForm() {
    const preview = data.value?.preview;
    if (!preview) return;
    importForm.value = {
      word_list_name: preview.word_list_name || "",
      word_columns: [...(preview.inferred_word_columns || [preview.inferred_word_column].filter(Boolean))],
      selected_rows: preview.rows.map((row) => row.index),
      selected_columns: [...preview.columns],
      image_files: [],
    };
  }

  function setAllRows(checked) {
    importForm.value.selected_rows = checked ? data.value.preview.rows.map((row) => row.index) : [];
  }

  function setAllColumns(checked) {
    importForm.value.selected_columns = checked ? [...data.value.preview.columns] : [];
  }

  async function changePreviewSheet(sheetName) {
    const params = new URLSearchParams({
      sheet_name: sheetName,
      word_list_name: importForm.value.word_list_name || data.value.preview.word_list_name || "",
      word_list_id: data.value.preview.word_list_id || "",
    });
    history.replaceState(null, "", `/upload/preview/${route.value.params.id}?${params.toString()}`);
    await loadRoute();
  }

  return {
    importForm,
    resetImportForm,
    setAllRows,
    setAllColumns,
    changePreviewSheet,
  };
}

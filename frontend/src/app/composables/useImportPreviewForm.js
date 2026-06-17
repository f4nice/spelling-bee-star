import { ref } from "vue";
import {
  buildImportPreviewFormState,
  buildPreviewSheetUrl,
  createImportPreviewFormState,
} from "../forms/importPreviewFormState.js";
import {
  getPreviewColumnSelection,
  getPreviewRowSelection,
} from "../forms/importPreviewSelection.js";

export function useImportPreviewForm({ data, route, loadRoute }) {
  const importForm = ref(createImportPreviewFormState());

  function resetImportForm() {
    const preview = data.value?.preview;
    if (!preview) return;
    importForm.value = buildImportPreviewFormState(preview);
  }

  function setAllRows(checked) {
    importForm.value.selected_rows = getPreviewRowSelection(data.value.preview, checked);
  }

  function setAllColumns(checked) {
    importForm.value.selected_columns = getPreviewColumnSelection(data.value.preview, checked);
  }

  async function changePreviewSheet(sheetName) {
    const url = buildPreviewSheetUrl({
      previewId: route.value.params.id,
      preview: data.value.preview,
      importForm: importForm.value,
      sheetName,
    });
    history.replaceState(null, "", url);
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

import { ref } from "vue";
import {
  buildImportPreviewFormState,
  createImportPreviewFormState,
} from "../forms/importPreviewFormState.js";
import {
  applyAllPreviewColumns,
  applyAllPreviewRows,
  switchPreviewSheet,
} from "../forms/importPreviewFormActions.js";

export function useImportPreviewForm({ data, route, loadRoute }) {
  const importForm = ref(createImportPreviewFormState());

  function resetImportForm() {
    const preview = data.value?.preview;
    if (!preview) return;
    importForm.value = buildImportPreviewFormState(preview);
  }

  function setAllRows(checked) {
    applyAllPreviewRows(importForm.value, data.value.preview, checked);
  }

  function setAllColumns(checked) {
    applyAllPreviewColumns(importForm.value, data.value.preview, checked);
  }

  async function changePreviewSheet(sheetName) {
    await switchPreviewSheet({
      route: route.value,
      data: data.value,
      importForm: importForm.value,
      sheetName,
      loadRoute,
    });
  }

  return {
    importForm,
    resetImportForm,
    setAllRows,
    setAllColumns,
    changePreviewSheet,
  };
}

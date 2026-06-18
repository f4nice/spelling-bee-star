import { buildPreviewSheetUrl } from "./importPreviewFormState.js";
import {
  getPreviewColumnSelection,
  getPreviewRowSelection,
} from "./importPreviewSelection.js";

export function applyAllPreviewRows(importForm, preview, checked) {
  importForm.selected_rows = getPreviewRowSelection(preview, checked);
}

export function applyAllPreviewColumns(importForm, preview, checked) {
  importForm.selected_columns = getPreviewColumnSelection(preview, checked);
}

export async function switchPreviewSheet({ route, data, importForm, sheetName, loadRoute }) {
  const url = buildPreviewSheetUrl({
    previewId: route.params.id,
    preview: data.preview,
    importForm,
    sheetName,
  });
  history.replaceState(null, "", url);
  await loadRoute();
}

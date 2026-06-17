import { importPreviewSheetUrl } from "../appRouteUrls.js";

export function createImportPreviewFormState() {
  return {
    word_list_name: "",
    word_columns: [],
    selected_rows: [],
    selected_columns: [],
    image_files: [],
  };
}

export function buildImportPreviewFormState(preview) {
  if (!preview) return createImportPreviewFormState();
  const inferredColumns = preview.inferred_word_columns || [preview.inferred_word_column].filter(Boolean);
  return {
    word_list_name: preview.word_list_name || "",
    word_columns: [...inferredColumns],
    selected_rows: preview.rows.map((row) => row.index),
    selected_columns: [...preview.columns],
    image_files: [],
  };
}

export function buildPreviewSheetUrl({ previewId, preview, importForm, sheetName }) {
  return importPreviewSheetUrl({
    previewId,
    sheetName,
    wordListName: importForm.word_list_name || preview.word_list_name,
    wordListId: preview.word_list_id,
  });
}

export function createImportPreviewSubmitForm({ previewId, preview, importForm }) {
  const form = new FormData();
  form.append("preview_id", previewId);
  form.append("word_list_id", preview.word_list_id || "");
  form.append("word_list_name", importForm.word_list_name);
  importForm.word_columns.forEach((item) => form.append("word_columns", item));
  importForm.selected_rows.forEach((item) => form.append("selected_rows", item));
  importForm.selected_columns.forEach((item) => form.append("selected_columns", item));
  importForm.image_files.forEach((item) => form.append("image_files", item));
  return form;
}

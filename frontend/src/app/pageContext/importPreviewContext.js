export function buildImportPreviewContext(importPreview) {
  return {
    importForm: importPreview.importForm.value,
    setAllRows: importPreview.setAllRows,
    setAllColumns: importPreview.setAllColumns,
    changePreviewSheet: importPreview.changePreviewSheet,
    submitImport: importPreview.submitImport,
  };
}

export function buildImportPreviewContext(importPreview) {
  return {
    importForm: importPreview.importForm.value,
    setAllRows: importPreview.setAllRows,
    setAllColumns: importPreview.setAllColumns,
    changePreviewSheet: importPreview.changePreviewSheet,
    isImporting: importPreview.isImporting.value,
    submitImport: importPreview.submitImport,
  };
}

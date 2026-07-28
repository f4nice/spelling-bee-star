export function buildImportPreviewContext(importPreview) {
  return {
    importForm: importPreview.importForm.value,
    setAllRows: importPreview.setAllRows,
    setAllColumns: importPreview.setAllColumns,
    changePreviewSheet: importPreview.changePreviewSheet,
    importJob: importPreview.importJob.value,
    isImporting: importPreview.isImporting.value,
    submitImport: importPreview.submitImport,
  };
}

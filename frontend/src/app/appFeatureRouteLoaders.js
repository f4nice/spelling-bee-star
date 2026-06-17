export function buildAppFeatureRouteLoaders({ wordDetail, listTools, importPreview, booklearner }) {
  return {
    resetWordTools: wordDetail.resetWordTools,
    setWordEdit: wordDetail.setWordEdit,
    setUploadOptionsFromCards: listTools.setUploadOptionsFromCards,
    loadUploadOptions: listTools.loadUploadOptions,
    resetImportForm: importPreview.resetImportForm,
    loadBooklearner: booklearner.loadBooklearner,
  };
}

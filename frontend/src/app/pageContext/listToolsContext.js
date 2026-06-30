export function buildListToolsContext(listTools) {
  return {
    uploadOptions: listTools.uploadOptions.value,
    uploadForm: listTools.uploadForm.value,
    batchImageState: listTools.batchImageState.value,
    deleteListState: listTools.deleteListState.value,
    aiImageJob: listTools.aiImageJob.value,
    submitUpload: listTools.submitUpload,
    submitBatchImages: listTools.submitBatchImages,
    renameList: listTools.renameList,
    deleteList: listTools.deleteList,
    syncListImages: listTools.syncListImages,
    generateListAiImages: listTools.generateListAiImages,
  };
}

export function buildImportPreviewContext(importPreview) {
  return {
    importForm: importPreview.importForm.value,
    setAllRows: importPreview.setAllRows,
    setAllColumns: importPreview.setAllColumns,
    changePreviewSheet: importPreview.changePreviewSheet,
    submitImport: importPreview.submitImport,
  };
}

export function buildWordDetailContext(wordDetail) {
  return {
    wordEdit: wordDetail.wordEdit.value,
    imageCandidates: wordDetail.imageCandidates.value,
    audioOptions: wordDetail.audioOptions.value,
    recorderState: wordDetail.recorderState.value,
    saveWordField: wordDetail.saveWordField,
    refreshWord: wordDetail.refreshWord,
    uploadWordImage: wordDetail.uploadWordImage,
    findImages: wordDetail.findImages,
    chooseNetworkImage: wordDetail.chooseNetworkImage,
    playAudio: wordDetail.playAudio,
    fetchAudioOptions: wordDetail.fetchAudioOptions,
    chooseAudio: wordDetail.chooseAudio,
    startRecording: wordDetail.startRecording,
    stopRecording: wordDetail.stopRecording,
    saveRecording: wordDetail.saveRecording,
    wordNavUrl: wordDetail.wordNavUrl,
  };
}

export function buildBooklearnerContext(booklearner) {
  return {
    book: booklearner.book.value,
    analyzeBookQuery: booklearner.analyzeBookQuery,
    analyzeBookText: booklearner.analyzeBookText,
    analyzeBookFile: booklearner.analyzeBookFile,
    saveBookAnalysis: booklearner.saveBookAnalysis,
    createBookWordList: booklearner.createBookWordList,
  };
}

export function buildListToolsContext(listTools) {
  return {
    uploadOptions: listTools.uploadOptions.value,
    uploadForm: listTools.uploadForm.value,
    batchImageState: listTools.batchImageState.value,
    deleteListState: listTools.deleteListState.value,
    submitUpload: listTools.submitUpload,
    submitBatchImages: listTools.submitBatchImages,
    renameList: listTools.renameList,
    deleteList: listTools.deleteList,
    syncListImages: listTools.syncListImages,
  };
}

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
    uploadAudio: wordDetail.uploadAudio,
    generateAiAudio: wordDetail.generateAiAudio,
    startRecording: wordDetail.startRecording,
    stopRecording: wordDetail.stopRecording,
    saveRecording: wordDetail.saveRecording,
    wordNavUrl: wordDetail.wordNavUrl,
  };
}

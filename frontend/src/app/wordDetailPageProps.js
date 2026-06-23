export function buildWordDetailPageProps(ctx) {
  return {
    mediaPanel: {
      data: ctx.data,
      imageCandidates: ctx.imageCandidates,
      imageForWord: ctx.imageForWord,
      uploadWordImage: ctx.uploadWordImage,
      findImages: ctx.findImages,
      chooseNetworkImage: ctx.chooseNetworkImage,
    },
    contentPanel: {
      data: ctx.data,
      wordEdit: ctx.wordEdit,
      audioOptions: ctx.audioOptions,
      recorderState: ctx.recorderState,
      wordNavUrl: ctx.wordNavUrl,
      saveWordField: ctx.saveWordField,
      refreshWord: ctx.refreshWord,
      playAudio: ctx.playAudio,
      fetchAudioOptions: ctx.fetchAudioOptions,
      startRecording: ctx.startRecording,
      chooseAudio: ctx.chooseAudio,
      uploadAudio: ctx.uploadAudio,
      generateAiAudio: ctx.generateAiAudio,
      stopRecording: ctx.stopRecording,
      saveRecording: ctx.saveRecording,
    },
  };
}

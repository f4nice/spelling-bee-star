export function buildWordAudioAccentListProps(props, accents) {
  return {
    data: props.data,
    audioOptions: props.audioOptions,
    accents,
    playAudio: props.playAudio,
    fetchAudioOptions: props.fetchAudioOptions,
    startRecording: props.startRecording,
    chooseAudio: props.chooseAudio,
    uploadAudio: props.uploadAudio,
  };
}

export function buildWordRecorderPanelProps(props) {
  return {
    recorderState: props.recorderState,
    stopRecording: props.stopRecording,
    saveRecording: props.saveRecording,
  };
}

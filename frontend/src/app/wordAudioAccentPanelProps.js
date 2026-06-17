export function buildWordAudioAccentPanelProps(props, accent) {
  return {
    accent,
    data: props.data,
    options: props.audioOptions[accent.key] || [],
    playAudio: props.playAudio,
    fetchAudioOptions: props.fetchAudioOptions,
    startRecording: props.startRecording,
    chooseAudio: props.chooseAudio,
  };
}

export const wordAudioAccentPanelProps = {
  accent: {
    type: Object,
    required: true,
  },
  data: {
    type: Object,
    required: true,
  },
  options: {
    type: Array,
    default: () => [],
  },
  playAudio: {
    type: Function,
    required: true,
  },
  fetchAudioOptions: {
    type: Function,
    required: true,
  },
  startRecording: {
    type: Function,
    required: true,
  },
  chooseAudio: {
    type: Function,
    required: true,
  },
};

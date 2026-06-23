export const wordAudioAccentListProps = {
  data: {
    type: Object,
    required: true,
  },
  audioOptions: {
    type: Object,
    required: true,
  },
  accents: {
    type: Array,
    required: true,
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
  uploadAudio: {
    type: Function,
    required: true,
  },
  generateAiAudio: {
    type: Function,
    required: true,
  },
};

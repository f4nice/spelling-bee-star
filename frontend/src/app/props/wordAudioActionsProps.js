export const wordAudioActionsProps = {
  accent: {
    type: Object,
    required: true,
  },
  audioSrc: {
    type: String,
    default: "",
  },
  canEdit: {
    type: Boolean,
    default: false,
  },
  playAudio: {
    type: Function,
    required: true,
  },
  fetchAudioOptions: {
    type: Function,
    required: true,
  },
};

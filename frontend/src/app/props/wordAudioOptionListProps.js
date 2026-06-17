export const wordAudioOptionListProps = {
  accent: {
    type: Object,
    required: true,
  },
  options: {
    type: Array,
    default: () => [],
  },
  chooseAudio: {
    type: Function,
    required: true,
  },
};

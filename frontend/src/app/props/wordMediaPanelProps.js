export const wordMediaPanelProps = {
  data: {
    type: Object,
    required: true,
  },
  imageCandidates: {
    type: Array,
    required: true,
  },
  imageForWord: {
    type: Function,
    required: true,
  },
  uploadWordImage: {
    type: Function,
    required: true,
  },
  findImages: {
    type: Function,
    required: true,
  },
  chooseNetworkImage: {
    type: Function,
    required: true,
  },
  generateAiImage: {
    type: Function,
    required: true,
  },
  audioOptions: {
    type: Object,
    required: true,
  },
  fetchAudioOptions: {
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
  generateDefinitionAudio: {
    type: Function,
    required: true,
  },
  generateExampleAudio: {
    type: Function,
    required: true,
  },
};

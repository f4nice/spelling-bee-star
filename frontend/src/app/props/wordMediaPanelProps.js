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
};

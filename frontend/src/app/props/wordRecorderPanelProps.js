export const wordRecorderPanelProps = {
  recorderState: {
    type: Object,
    required: true,
  },
  stopRecording: {
    type: Function,
    required: true,
  },
  saveRecording: {
    type: Function,
    required: true,
  },
};

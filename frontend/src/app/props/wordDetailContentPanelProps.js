import { wordAudioPanelProps } from "./wordAudioPanelProps.js";

export const wordDetailContentPanelProps = {
  ...wordAudioPanelProps,
  wordEdit: {
    type: Object,
    required: true,
  },
  wordNavUrl: {
    type: Function,
    required: true,
  },
  navigateWord: {
    type: Function,
    default: null,
  },
  saveWordField: {
    type: Function,
    required: true,
  },
  refreshWord: {
    type: Function,
    required: true,
  },
  generateDefinitionAudio: {
    type: Function,
    required: true,
  },
};

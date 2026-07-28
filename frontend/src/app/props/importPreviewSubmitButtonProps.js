export const importPreviewSubmitButtonProps = {
  submitImport: {
    type: Function,
    required: true,
  },
  importJob: {
    type: Object,
    default: null,
  },
  isImporting: {
    type: Boolean,
    default: false,
  },
};

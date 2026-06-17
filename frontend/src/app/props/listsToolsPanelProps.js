export const listsToolsPanelProps = {
  data: {
    type: Object,
    required: true,
  },
  uploadOptions: {
    type: Object,
    required: true,
  },
  uploadForm: {
    type: Object,
    required: true,
  },
  batchImageState: {
    type: Object,
    required: true,
  },
  submitUpload: {
    type: Function,
    required: true,
  },
  submitBatchImages: {
    type: Function,
    required: true,
  },
};

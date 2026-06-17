export const uploadExcelFormProps = {
  uploadOptions: {
    type: Object,
    required: true,
  },
  uploadForm: {
    type: Object,
    required: true,
  },
  submitUpload: {
    type: Function,
    required: true,
  },
  variant: {
    type: String,
    default: "page",
  },
};

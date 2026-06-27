export const importPreviewToolbarProps = {
  preview: {
    type: Object,
    required: true,
  },
  importForm: {
    type: Object,
    required: true,
  },
  changePreviewSheet: {
    type: Function,
    required: true,
  },
  setAllRows: {
    type: Function,
    required: true,
  },
  setAllColumns: {
    type: Function,
    required: true,
  },
  submitImport: {
    type: Function,
    required: true,
  },
  isImporting: {
    type: Boolean,
    default: false,
  },
};

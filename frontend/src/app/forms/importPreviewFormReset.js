import { buildImportPreviewFormState } from "./importPreviewFormState.js";

export function resetImportPreviewForm(importForm, data) {
  const preview = data.value?.preview;
  if (!preview) return;
  importForm.value = buildImportPreviewFormState(preview);
}

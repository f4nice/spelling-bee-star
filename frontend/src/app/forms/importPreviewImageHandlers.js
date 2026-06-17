export function setImportPreviewImages(importForm, event) {
  importForm.image_files = Array.from(event.target.files || []);
}

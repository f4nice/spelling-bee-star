export function setUploadFormFile(uploadForm, event) {
  uploadForm.file = event.target.files[0];
}

export function createWordEditTokenForm() {
  const form = new FormData();
  form.append("edit_token", "1");
  return form;
}

export function createWordImageUploadForm(file) {
  const form = createWordEditTokenForm();
  form.append("file", file);
  return form;
}

export function createWordNetworkImageForm(url) {
  const form = createWordEditTokenForm();
  form.append("image_url", url);
  return form;
}

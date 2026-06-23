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

export function createWordAiImageForm(option, controls = {}) {
  const form = createWordEditTokenForm();
  form.append("commit", "0");
  form.append("provider", option.provider || "");
  form.append("model", option.model || "");
  form.append("theme", controls.theme || "");
  form.append("style", controls.style || "");
  form.append("meaning", controls.meaning || "");
  return form;
}

export function createRenameListForm(name) {
  const form = new FormData();
  form.append("name", name);
  return form;
}

export function createDeleteListForm(password) {
  const form = new FormData();
  form.append("password", password);
  return form;
}

export function createListUploadForm({ file, wordListId = "", wordListName = "" }) {
  const form = new FormData();
  form.append("file", file);
  form.append("word_list_id", wordListId || "");
  form.append("word_list_name", wordListName || "");
  return form;
}

export function createBatchImageForm({ wordListId, imageFiles }) {
  const form = new FormData();
  form.append("word_list_id", wordListId);
  imageFiles.forEach((file) => form.append("image_files", file));
  return form;
}

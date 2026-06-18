export function createWordFieldForm({ field, value }) {
  const form = new FormData();
  form.append("edit_token", "1");
  form.append("field", field);
  form.append("value", value || "");
  return form;
}

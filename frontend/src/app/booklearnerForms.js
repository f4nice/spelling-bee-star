export function createBooklearnerFileAnalysisForm({ title, author, file }) {
  const form = new FormData();
  form.append("title", title);
  form.append("author", author);
  form.append("file", file);
  return form;
}

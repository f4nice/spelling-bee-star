export function createBooklearnerTextAnalysisRequest({ title, author, text }) {
  return {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ title, author, text }),
  };
}

export function createBooklearnerFileAnalysisForm({ title, author, file }) {
  const form = new FormData();
  form.append("title", title);
  form.append("author", author);
  form.append("file", file);
  return form;
}

export function createBooklearnerTextAnalysisRequest({ title, author, text }) {
  return {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ title, author, text }),
  };
}

export function createBooklearnerSaveAnalysisRequest({ query, result }) {
  return {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query, result }),
  };
}

export function createBooklearnerWordListRequest({ title, vocabulary }) {
  return {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ title, vocabulary }),
  };
}

export function createBooklearnerFileAnalysisForm({ title, author, file }) {
  const form = new FormData();
  form.append("title", title);
  form.append("author", author);
  form.append("file", file);
  return form;
}

export function createBookCoverUploadForm(file) {
  const form = new FormData();
  form.append("file", file);
  return form;
}

export function createBookAiCoverForm({ model, theme, style }) {
  const form = new FormData();
  form.append("model", model || "wan2.7-image-pro");
  form.append("theme", theme || "");
  form.append("style", style || "书籍封面插画");
  return form;
}

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

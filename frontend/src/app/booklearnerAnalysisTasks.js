import { booklearnerApiPaths } from "./booklearnerApiPaths.js";
import { createBooklearnerFileAnalysisForm, createBooklearnerTextAnalysisRequest } from "./booklearnerForms.js";
import { fetchJson } from "./utils.js";

export function createBookQueryAnalysisTask(book) {
  return () => fetchJson(booklearnerApiPaths.analyze(book.value.query));
}

export function createBookTextAnalysisTask(book) {
  return () => fetchJson(
    booklearnerApiPaths.analyzeText(),
    createBooklearnerTextAnalysisRequest({
      title: book.value.title,
      author: book.value.author,
      text: book.value.text,
    }),
  );
}

export function createBookFileAnalysisTask(book) {
  const form = createBooklearnerFileAnalysisForm({
    title: book.value.title,
    author: book.value.author,
    file: book.value.file,
  });
  return () => fetchJson(booklearnerApiPaths.analyzeFile(), { method: "POST", body: form });
}

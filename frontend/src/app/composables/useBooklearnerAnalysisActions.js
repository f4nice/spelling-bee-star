import { fetchJson } from "../utils.js";
import { booklearnerApiPaths } from "../booklearnerApiPaths.js";
import { createBooklearnerFileAnalysisForm, createBooklearnerTextAnalysisRequest } from "../booklearnerForms.js";

export function useBooklearnerAnalysisActions({ book, setNotice }) {
  async function analyzeBookQuery() {
    setNotice("正在分析...");
    book.value.result = await fetchJson(booklearnerApiPaths.analyze(book.value.query));
    setNotice("分析完成");
  }

  async function analyzeBookText() {
    setNotice("正在分析文本...");
    book.value.result = await fetchJson(
      booklearnerApiPaths.analyzeText(),
      createBooklearnerTextAnalysisRequest({
        title: book.value.title,
        author: book.value.author,
        text: book.value.text,
      }),
    );
    setNotice("分析完成");
  }

  async function analyzeBookFile() {
    if (!book.value.file) return;
    const form = createBooklearnerFileAnalysisForm({
      title: book.value.title,
      author: book.value.author,
      file: book.value.file,
    });
    setNotice("正在分析文件...");
    book.value.result = await fetchJson(booklearnerApiPaths.analyzeFile(), { method: "POST", body: form });
    setNotice("分析完成");
  }

  return {
    analyzeBookQuery,
    analyzeBookText,
    analyzeBookFile,
  };
}

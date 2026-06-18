import { fetchJson } from "../utils.js";
import { booklearnerApiPaths } from "../booklearnerApiPaths.js";
import { runBooklearnerAnalysis } from "../booklearnerAnalysisRunner.js";
import { createBooklearnerFileAnalysisForm, createBooklearnerTextAnalysisRequest } from "../booklearnerForms.js";

export function useBooklearnerAnalysisActions({ book, setNotice }) {
  async function analyzeBookQuery() {
    await runBooklearnerAnalysis({
      book,
      setNotice,
      startMessage: "正在分析...",
      task: () => fetchJson(booklearnerApiPaths.analyze(book.value.query)),
    });
  }

  async function analyzeBookText() {
    await runBooklearnerAnalysis({
      book,
      setNotice,
      startMessage: "正在分析文本...",
      task: () => fetchJson(
        booklearnerApiPaths.analyzeText(),
        createBooklearnerTextAnalysisRequest({
          title: book.value.title,
          author: book.value.author,
          text: book.value.text,
        }),
      ),
    });
  }

  async function analyzeBookFile() {
    if (!book.value.file) return;
    const form = createBooklearnerFileAnalysisForm({
      title: book.value.title,
      author: book.value.author,
      file: book.value.file,
    });
    await runBooklearnerAnalysis({
      book,
      setNotice,
      startMessage: "正在分析文件...",
      task: () => fetchJson(booklearnerApiPaths.analyzeFile(), { method: "POST", body: form }),
    });
  }

  return {
    analyzeBookQuery,
    analyzeBookText,
    analyzeBookFile,
  };
}

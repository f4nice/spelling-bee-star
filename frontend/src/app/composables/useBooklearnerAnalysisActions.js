import { fetchJson } from "../utils.js";

export function useBooklearnerAnalysisActions({ book, setNotice }) {
  async function analyzeBookQuery() {
    setNotice("正在分析...");
    book.value.result = await fetchJson(`/booklearner/api/analyze?q=${encodeURIComponent(book.value.query)}`);
    setNotice("分析完成");
  }

  async function analyzeBookText() {
    setNotice("正在分析文本...");
    book.value.result = await fetchJson("/booklearner/api/analyze-text", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title: book.value.title, author: book.value.author, text: book.value.text }),
    });
    setNotice("分析完成");
  }

  async function analyzeBookFile() {
    if (!book.value.file) return;
    const form = new FormData();
    form.append("title", book.value.title);
    form.append("author", book.value.author);
    form.append("file", book.value.file);
    setNotice("正在分析文件...");
    book.value.result = await fetchJson("/booklearner/api/analyze-file", { method: "POST", body: form });
    setNotice("分析完成");
  }

  return {
    analyzeBookQuery,
    analyzeBookText,
    analyzeBookFile,
  };
}

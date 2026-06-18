import { runBooklearnerAnalysis } from "../booklearnerAnalysisRunner.js";
import {
  createBookFileAnalysisTask,
  createBookQueryAnalysisTask,
  createBookTextAnalysisTask,
} from "../booklearnerAnalysisTasks.js";

export function useBooklearnerAnalysisActions({ book, setNotice }) {
  async function analyzeBookQuery() {
    await runBooklearnerAnalysis({
      book,
      setNotice,
      startMessage: "正在分析...",
      task: createBookQueryAnalysisTask(book),
    });
  }

  async function analyzeBookText() {
    await runBooklearnerAnalysis({
      book,
      setNotice,
      startMessage: "正在分析文本...",
      task: createBookTextAnalysisTask(book),
    });
  }

  async function analyzeBookFile() {
    if (!book.value.file) return;
    await runBooklearnerAnalysis({
      book,
      setNotice,
      startMessage: "正在分析文件...",
      task: createBookFileAnalysisTask(book),
    });
  }

  return {
    analyzeBookQuery,
    analyzeBookText,
    analyzeBookFile,
  };
}

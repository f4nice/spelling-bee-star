import { createBooklearnerAnalysisAction } from "../booklearnerAnalysisRunner.js";
import {
  createBookFileAnalysisTask,
  createBookQueryAnalysisTask,
  createBookTextAnalysisTask,
} from "../booklearnerAnalysisTasks.js";

export function useBooklearnerAnalysisActions({ book, setNotice }) {
  const analyzeBookQuery = createBooklearnerAnalysisAction({
    book,
    setNotice,
    startMessage: "正在分析...",
    taskFactory: createBookQueryAnalysisTask,
  });

  const analyzeBookText = createBooklearnerAnalysisAction({
    book,
    setNotice,
    startMessage: "正在分析文本...",
    taskFactory: createBookTextAnalysisTask,
  });

  const analyzeBookFile = createBooklearnerAnalysisAction({
    book,
    setNotice,
    startMessage: "正在分析文件...",
    taskFactory: createBookFileAnalysisTask,
    canRun: () => Boolean(book.value.file),
  });

  return {
    analyzeBookQuery,
    analyzeBookText,
    analyzeBookFile,
  };
}

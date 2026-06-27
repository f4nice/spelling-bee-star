import {
  createBookFileAnalysisTask,
  createBookQueryAnalysisTask,
} from "./booklearnerAnalysisTasks.js";

export const booklearnerAnalysisActionConfigs = [
  {
    key: "analyzeBookQuery",
    startMessage: "正在分析...",
    taskFactory: createBookQueryAnalysisTask,
  },
  {
    key: "analyzeBookFile",
    startMessage: "正在分析文件...",
    taskFactory: createBookFileAnalysisTask,
    canRun: (book) => Boolean(book.value.file),
  },
];

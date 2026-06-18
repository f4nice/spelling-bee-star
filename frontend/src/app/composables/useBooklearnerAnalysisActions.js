import { createBooklearnerAnalysisAction } from "../booklearnerAnalysisRunner.js";
import { booklearnerAnalysisActionConfigs } from "../booklearnerAnalysisActionConfigs.js";

export function useBooklearnerAnalysisActions({ book, setNotice }) {
  return Object.fromEntries(
    booklearnerAnalysisActionConfigs.map((config) => [
      config.key,
      createBooklearnerAnalysisAction({
        book,
        setNotice,
        startMessage: config.startMessage,
        taskFactory: config.taskFactory,
        canRun: config.canRun ? () => config.canRun(book) : undefined,
      }),
    ]),
  );
}

export async function runBooklearnerAnalysis({ book, setNotice, startMessage, task }) {
  setNotice(startMessage);
  book.value.result = await task();
  setNotice("分析完成");
}

export function createBooklearnerAnalysisAction({ book, setNotice, startMessage, taskFactory, canRun = () => true }) {
  return async function runAnalysisAction() {
    if (!canRun()) return;
    await runBooklearnerAnalysis({
      book,
      setNotice,
      startMessage,
      task: taskFactory(book),
    });
  };
}

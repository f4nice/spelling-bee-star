export async function runBooklearnerAnalysis({ book, setNotice, startMessage, task }) {
  try {
    setNotice(startMessage);
    book.value.result = await task();
    setNotice("分析完成");
  } catch (error) {
    setNotice(error?.message || "分析失败，请稍后再试");
  }
}

export function createBooklearnerAnalysisAction({ book, setNotice, startMessage, taskFactory, canRun = () => true }) {
  return async function runAnalysisAction() {
    if (!canRun()) {
      setNotice("请先选择或填写要分析的书籍内容");
      return;
    }
    await runBooklearnerAnalysis({
      book,
      setNotice,
      startMessage,
      task: taskFactory(book),
    });
  };
}

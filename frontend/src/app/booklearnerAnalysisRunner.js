export async function runBooklearnerAnalysis({ book, setNotice, startMessage, task }) {
  setNotice(startMessage);
  book.value.result = await task();
  setNotice("分析完成");
}

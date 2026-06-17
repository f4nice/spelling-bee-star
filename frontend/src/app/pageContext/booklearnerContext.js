export function buildBooklearnerContext(booklearner) {
  return {
    book: booklearner.book.value,
    analyzeBookQuery: booklearner.analyzeBookQuery,
    analyzeBookText: booklearner.analyzeBookText,
    analyzeBookFile: booklearner.analyzeBookFile,
    saveBookAnalysis: booklearner.saveBookAnalysis,
    createBookWordList: booklearner.createBookWordList,
  };
}

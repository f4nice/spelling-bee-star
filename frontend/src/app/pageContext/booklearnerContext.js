export function buildBooklearnerContext(booklearner) {
  return {
    book: booklearner.book.value,
    analyzeBookQuery: booklearner.analyzeBookQuery,
    analyzeBookFile: booklearner.analyzeBookFile,
    saveBookAnalysis: booklearner.saveBookAnalysis,
    createBookWordList: booklearner.createBookWordList,
  };
}

export function buildBooklearnerContext(booklearner) {
  return {
    book: booklearner.book.value,
    analyzeBookQuery: booklearner.analyzeBookQuery,
    analyzeBookFile: booklearner.analyzeBookFile,
    saveBookAnalysis: booklearner.saveBookAnalysis,
    createBookWordList: booklearner.createBookWordList,
    uploadBookCover: booklearner.uploadBookCover,
    generateBookAiCover: booklearner.generateBookAiCover,
    loadScienceDiscoveries: booklearner.loadScienceDiscoveries,
    loadScienceArticle: booklearner.loadScienceArticle,
    loadScienceFullArticle: booklearner.loadScienceFullArticle,
  };
}

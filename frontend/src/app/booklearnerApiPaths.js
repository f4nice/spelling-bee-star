export const booklearnerApiPaths = {
  analyze: (query) => `/booklearner/api/analyze?q=${encodeURIComponent(query)}`,
  analyzeText: () => "/booklearner/api/analyze-text",
  analyzeFile: () => "/booklearner/api/analyze-file",
  featured: ({ limit, analysisId = null }) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (analysisId) params.set("analysis_id", analysisId);
    return `/booklearner/api/featured?${params.toString()}`;
  },
  history: () => "/booklearner/api/history",
  historyDetail: (id) => `/booklearner/api/history/${id}`,
  saveAnalysis: () => "/booklearner/api/save-analysis",
  wordList: () => "/booklearner/api/word-list",
};

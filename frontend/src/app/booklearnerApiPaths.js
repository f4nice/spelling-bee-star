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
  historyCover: (id) => `/booklearner/api/history/${id}/cover`,
  historyAiCover: (id) => `/booklearner/api/history/${id}/ai-cover`,
  scienceDaily: ({ level = "L500-L700", topic = "全部", batch = 0 } = {}) => {
    const params = new URLSearchParams({
      level,
      topic,
      batch: String(batch),
    });
    return `/booklearner/api/science-daily?${params.toString()}`;
  },
  scienceArticle: (slug, { level = "" } = {}) => {
    const params = new URLSearchParams();
    if (level) params.set("level", level);
    const suffix = params.toString() ? `?${params.toString()}` : "";
    return `/booklearner/api/science-daily/${encodeURIComponent(slug)}${suffix}`;
  },
  saveAnalysis: () => "/booklearner/api/save-analysis",
  wordList: () => "/booklearner/api/word-list",
};

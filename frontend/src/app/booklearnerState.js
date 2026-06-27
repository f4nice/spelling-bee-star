export function createBooklearnerState() {
  return {
    query: "",
    title: "",
    author: "",
    text: "",
    file: null,
    result: null,
    history: [],
    featured: [],
    suggestions: [],
    science: {
      level: "L500-L700",
      levelLabel: "L500-L700",
      topic: "全部",
      batch: 0,
      date: "",
      items: [],
      sources: [],
      poolSize: 0,
      filteredPoolSize: 0,
      article: null,
      notice: "",
    },
    notice: "",
  };
}

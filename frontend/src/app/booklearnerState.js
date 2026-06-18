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
    notice: "",
  };
}

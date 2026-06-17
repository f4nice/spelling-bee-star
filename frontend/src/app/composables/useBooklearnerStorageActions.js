import { fetchJson } from "../utils.js";
import { booklearnerApiPaths } from "../booklearnerApiPaths.js";

export function useBooklearnerStorageActions({ book, go, setNotice }) {
  async function saveBookAnalysis() {
    const result = await fetchJson(booklearnerApiPaths.saveAnalysis(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ query: book.value.query || book.value.title, result: book.value.result }),
    });
    setNotice(`已保存 #${result.storage?.id || ""}`);
  }

  async function createBookWordList() {
    const vocabulary = book.value.result?.vocabulary || book.value.result?.words || [];
    const title = book.value.result?.book?.title || book.value.title || "BookLearner 单词表";
    const result = await fetchJson(booklearnerApiPaths.wordList(), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title, vocabulary }),
    });
    go(`/lists/${result.word_list_id}`);
  }

  return {
    saveBookAnalysis,
    createBookWordList,
  };
}

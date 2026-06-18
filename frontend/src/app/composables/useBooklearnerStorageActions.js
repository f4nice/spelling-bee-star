import { fetchJson } from "../utils.js";
import { booklearnerApiPaths } from "../booklearnerApiPaths.js";
import { createBooklearnerSaveAnalysisRequest, createBooklearnerWordListRequest } from "../booklearnerForms.js";

export function useBooklearnerStorageActions({ book, go, setNotice }) {
  async function saveBookAnalysis() {
    const request = createBooklearnerSaveAnalysisRequest({
      query: book.value.query || book.value.title,
      result: book.value.result,
    });
    const result = await fetchJson(booklearnerApiPaths.saveAnalysis(), request);
    setNotice(`已保存 #${result.storage?.id || ""}`);
  }

  async function createBookWordList() {
    const vocabulary = book.value.result?.vocabulary || book.value.result?.words || [];
    const title = book.value.result?.book?.title || book.value.title || "BookLearner 单词表";
    const result = await fetchJson(
      booklearnerApiPaths.wordList(),
      createBooklearnerWordListRequest({ title, vocabulary }),
    );
    go(`/lists/${result.word_list_id}`);
  }

  return {
    saveBookAnalysis,
    createBookWordList,
  };
}

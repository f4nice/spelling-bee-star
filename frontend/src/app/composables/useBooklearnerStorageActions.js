import { fetchJson } from "../utils.js";
import { booklearnerApiPaths } from "../booklearnerApiPaths.js";
import { createBooklearnerSaveAnalysisRequest, createBooklearnerWordListRequest } from "../booklearnerForms.js";

export function useBooklearnerStorageActions({ book, go, setNotice }) {
  async function saveBookAnalysis() {
    try {
      const request = createBooklearnerSaveAnalysisRequest({
        query: book.value.query || book.value.title,
        result: book.value.result,
      });
      const result = await fetchJson(booklearnerApiPaths.saveAnalysis(), request);
      setNotice(`已保存 #${result.storage?.analysisId || result.storage?.id || ""}`);
    } catch (error) {
      setNotice(error?.message || "保存失败，请稍后再试");
    }
  }

  async function createBookWordList() {
    try {
      const vocabulary = book.value.result?.vocabulary || book.value.result?.words || [];
      if (!vocabulary.length) {
        setNotice("这条书摘还没有可生成的单词");
        return;
      }

      const title = book.value.result?.book?.title || book.value.title || "BookLearner 单词表";
      const result = await fetchJson(
        booklearnerApiPaths.wordList(),
        createBooklearnerWordListRequest({ title, vocabulary }),
      );

      setNotice(`已生成 ${result.count || 0} 个单词`);
      go(`/lists/${result.word_list_id}`);
    } catch (error) {
      setNotice(error?.message || "生成单词表失败，请稍后再试");
    }
  }

  return {
    saveBookAnalysis,
    createBookWordList,
  };
}

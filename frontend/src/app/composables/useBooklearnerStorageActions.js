import { fetchJson } from "../utils.js";
import { booklearnerApiPaths } from "../booklearnerApiPaths.js";
import {
  createBookAiCoverForm,
  createBookCoverUploadForm,
  createBooklearnerSaveAnalysisRequest,
  createBooklearnerWordListRequest,
} from "../booklearnerForms.js";

export function useBooklearnerStorageActions({ book, go, setNotice }) {
  function applyBookCoverResult(payload, fallbackNotice) {
    if (payload?.result) {
      book.value.result = payload.result;
    } else if (payload?.coverUrl && book.value.result) {
      const nextBook = { ...(book.value.result.book || {}), coverUrl: payload.coverUrl };
      book.value.result = { ...book.value.result, book: nextBook };
    }
    setNotice(fallbackNotice);
    return payload;
  }

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

  async function uploadBookCover(analysisId, file) {
    if (!analysisId || !file) return null;
    try {
      const payload = await fetchJson(booklearnerApiPaths.historyCover(analysisId), {
        method: "POST",
        body: createBookCoverUploadForm(file),
      });
      return applyBookCoverResult(payload, "封面图片已更新");
    } catch (error) {
      setNotice(error?.message || "封面图片保存失败，请稍后再试");
      throw error;
    }
  }

  async function generateBookAiCover(analysisId, controls = {}) {
    if (!analysisId) return null;
    try {
      const payload = await fetchJson(booklearnerApiPaths.historyAiCover(analysisId), {
        method: "POST",
        body: createBookAiCoverForm(controls),
      });
      return applyBookCoverResult(payload, "AI 封面已生成");
    } catch (error) {
      setNotice(error?.message || "AI 封面生成失败，请稍后再试");
      throw error;
    }
  }

  return {
    saveBookAnalysis,
    createBookWordList,
    uploadBookCover,
    generateBookAiCover,
  };
}

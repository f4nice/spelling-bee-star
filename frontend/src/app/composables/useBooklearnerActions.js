import { useBooklearnerAnalysisActions } from "./useBooklearnerAnalysisActions.js";
import { useBooklearnerStorageActions } from "./useBooklearnerStorageActions.js";

export function useBooklearnerActions({ book, go }) {
  function setNotice(message) {
    book.value.notice = message;
  }

  const analysisActions = useBooklearnerAnalysisActions({ book, setNotice });
  const storageActions = useBooklearnerStorageActions({ book, go, setNotice });

  return {
    ...analysisActions,
    ...storageActions,
  };
}

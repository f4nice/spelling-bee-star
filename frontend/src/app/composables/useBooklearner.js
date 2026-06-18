import { ref } from 'vue';
import { useBooklearnerActions } from './useBooklearnerActions.js';
import { useBooklearnerData } from './useBooklearnerData.js';
import { createBooklearnerState } from '../booklearnerState.js';

export function useBooklearner({ route, go }) {
  const book = ref(createBooklearnerState());

  const { loadBooklearner } = useBooklearnerData({ book, route });
  const {
    analyzeBookQuery,
    analyzeBookText,
    analyzeBookFile,
    saveBookAnalysis,
    createBookWordList,
  } = useBooklearnerActions({ book, go });

  return {
    book,
    loadBooklearner,
    analyzeBookQuery,
    analyzeBookText,
    analyzeBookFile,
    saveBookAnalysis,
    createBookWordList,
  };
}

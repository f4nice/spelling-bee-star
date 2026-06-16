import { ref } from 'vue';
import { useBooklearnerActions } from './useBooklearnerActions.js';
import { useBooklearnerData } from './useBooklearnerData.js';

export function useBooklearner({ route, go }) {
  const book = ref({
    query: '',
    title: '',
    author: '',
    text: '',
    file: null,
    result: null,
    history: [],
    featured: [],
    suggestions: [],
    notice: '',
  });

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

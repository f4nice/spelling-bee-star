import { fetchJson } from '../utils.js';
import { booklearnerApiPaths } from '../booklearnerApiPaths.js';

export function useBooklearnerData({ book, route }) {
  async function loadBooklearner() {
    book.value.result = null;
    book.value.history = (await fetchJson(booklearnerApiPaths.history())).items || [];
    if (route.value.name === 'booklearnerDetail') {
      book.value.result = await fetchJson(booklearnerApiPaths.historyDetail(route.value.params.id));
      book.value.featured = (await fetchJson(booklearnerApiPaths.featured({ limit: 80, analysisId: route.value.params.id }))).items || [];
      return;
    }

    const limit = route.value.name === 'booklearnerQuotes' ? 40 : 12;
    book.value.featured = (await fetchJson(booklearnerApiPaths.featured({ limit }))).items || [];
  }

  return {
    loadBooklearner,
  };
}

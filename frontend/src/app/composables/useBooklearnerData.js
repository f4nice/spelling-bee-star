import { fetchJson } from '../utils.js';

export function useBooklearnerData({ book, route }) {
  async function loadBooklearner() {
    book.value.result = null;
    if (route.value.name === 'booklearnerDetail') {
      book.value.result = await fetchJson(`/booklearner/api/history/${route.value.params.id}`);
      book.value.featured = (await fetchJson(`/booklearner/api/featured?limit=80&analysis_id=${route.value.params.id}`)).items || [];
      return;
    }

    const limit = route.value.name === 'booklearnerQuotes' ? 40 : 12;
    book.value.featured = (await fetchJson(`/booklearner/api/featured?limit=${limit}`)).items || [];
    book.value.history = (await fetchJson('/booklearner/api/history')).items || [];
  }

  return {
    loadBooklearner,
  };
}

import { fetchJson } from '../utils.js';
import { booklearnerApiPaths } from '../booklearnerApiPaths.js';

export function useBooklearnerData({ book, route }) {
  function updateScience(payload = {}) {
    book.value.science = {
      ...(book.value.science || {}),
      ...payload,
      article: payload.article ?? book.value.science?.article ?? null,
      notice: payload.notice || '',
    };
  }

  async function loadScienceDiscoveries(overrides = {}) {
    const current = book.value.science || {};
    const payload = await fetchJson(booklearnerApiPaths.scienceDaily({
      level: overrides.level || current.level || 'L500-L700',
      topic: overrides.topic || current.topic || '全部',
      batch: overrides.batch ?? current.batch ?? 0,
    }));
    updateScience(payload);
  }

  async function loadScienceArticle(slug) {
    const current = book.value.science || {};
    const payload = await fetchJson(booklearnerApiPaths.scienceArticle(slug, {
      level: current.level || 'L500-L700',
    }));
    updateScience({
      article: payload.item,
      sources: payload.sources || current.sources || [],
    });
  }

  async function loadBooklearner() {
    book.value.result = null;
    book.value.history = (await fetchJson(booklearnerApiPaths.history())).items || [];
    if (route.value.name === 'booklearnerScience') {
      await loadScienceArticle(route.value.params.slug);
      return;
    }

    if (route.value.name === 'booklearnerDetail') {
      book.value.result = await fetchJson(booklearnerApiPaths.historyDetail(route.value.params.id));
      book.value.featured = (await fetchJson(booklearnerApiPaths.featured({ limit: 80, analysisId: route.value.params.id }))).items || [];
      return;
    }

    const limit = route.value.name === 'booklearnerQuotes' ? 80 : 40;
    book.value.featured = (await fetchJson(booklearnerApiPaths.featured({ limit }))).items || [];
    if (route.value.name === 'booklearner') {
      await loadScienceDiscoveries();
    }
  }

  return {
    loadBooklearner,
    loadScienceDiscoveries,
    loadScienceArticle,
  };
}

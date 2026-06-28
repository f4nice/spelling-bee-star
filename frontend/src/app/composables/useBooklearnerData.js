import { fetchJson } from '../utils.js';
import { booklearnerApiPaths } from '../booklearnerApiPaths.js';

export function useBooklearnerData({ book, route }) {
  let scienceRequestId = 0;

  function updateScience(payload = {}) {
    const hasArticle = Object.prototype.hasOwnProperty.call(payload, 'article');
    book.value.science = {
      ...(book.value.science || {}),
      ...payload,
      article: hasArticle ? payload.article : book.value.science?.article ?? null,
      notice: payload.notice || '',
    };
  }

  async function loadScienceDiscoveries(overrides = {}) {
    const requestId = scienceRequestId + 1;
    scienceRequestId = requestId;
    const current = book.value.science || {};
    const requested = {
      level: overrides.level || current.level || 'L500-L700',
      topic: overrides.topic || current.topic || '全部',
      batch: overrides.batch ?? current.batch ?? 0,
    };
    updateScience({ ...requested, items: [], article: null });
    const payload = await fetchJson(booklearnerApiPaths.scienceDaily(requested), { skipCache: overrides.force === true });
    if (requestId !== scienceRequestId) return;
    updateScience({ ...payload, article: null });
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

  async function loadScienceFullArticle(slug) {
    const current = book.value.science || {};
    const payload = await fetchJson(booklearnerApiPaths.scienceFullArticle(slug, {
      level: current.level || current.article?.level || 'L500-L700',
    }), { skipCache: true });
    updateScience({
      article: {
        ...(current.article || {}),
        ...payload.item,
      },
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

    if (route.value.name === 'booklearnerScienceHome') {
      await loadScienceDiscoveries();
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
    loadScienceFullArticle,
  };
}

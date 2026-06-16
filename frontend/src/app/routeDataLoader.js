import { fetchJson } from './utils.js';

export async function loadVueRouteData({
  route,
  data,
  resetWordTools,
  setWordEdit,
  setUploadOptionsFromCards,
  loadUploadOptions,
  resetImportForm,
  loadBooklearner,
}) {
  resetWordTools();

  if (route.name === 'home') data.value = await fetchJson('/api/vue/home');
  if (route.name === 'lists') {
    data.value = await fetchJson('/api/vue/lists');
    setUploadOptionsFromCards(data.value.cards);
  }
  if (route.name === 'listDetail') data.value = await fetchJson(`/api/vue/lists/${route.params.id}`);
  if (route.name === 'wrongWords') data.value = await fetchJson('/api/vue/wrong-words');
  if (route.name === 'challengeDay') data.value = await fetchJson(`/api/vue/challenge-calendar/${route.params.day}`);
  if (route.name === 'wordDetail') {
    data.value = await fetchJson(`/api/vue/words/${route.params.id}${window.location.search}`);
    setWordEdit(data.value.word);
  }
  if (route.name === 'upload') {
    await loadUploadOptions();
    data.value = { ok: true };
  }
  if (route.name === 'preview') {
    data.value = await fetchJson(`/api/vue/upload/preview/${route.params.id}${window.location.search}`);
    resetImportForm();
  }
  if (route.name === 'newspaper') data.value = await fetchJson('/api/vue/newspaper');
  if (route.name === 'newspaperArticle') {
    data.value = await fetchJson(`/api/vue/newspaper/${route.params.section}/${route.params.index}`);
  }
  if (route.name.startsWith('booklearner')) {
    data.value = { ok: true };
    await loadBooklearner();
  }
}

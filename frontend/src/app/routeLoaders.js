import { fetchJson } from "./utils.js";

export const routeLoaders = {
  async home({ data }) {
    data.value = await fetchJson("/api/vue/home");
  },

  async lists({ data, setUploadOptionsFromCards }) {
    data.value = await fetchJson("/api/vue/lists");
    setUploadOptionsFromCards(data.value.cards);
  },

  async listDetail({ route, data }) {
    data.value = await fetchJson(`/api/vue/lists/${route.params.id}`);
  },

  async wrongWords({ data }) {
    data.value = await fetchJson("/api/vue/wrong-words");
  },

  async challengeDay({ route, data }) {
    data.value = await fetchJson(`/api/vue/challenge-calendar/${route.params.day}`);
  },

  async wordDetail({ route, data, setWordEdit }) {
    data.value = await fetchJson(`/api/vue/words/${route.params.id}${window.location.search}`);
    setWordEdit(data.value.word);
  },

  async upload({ data, loadUploadOptions }) {
    await loadUploadOptions();
    data.value = { ok: true };
  },

  async preview({ route, data, resetImportForm }) {
    data.value = await fetchJson(`/api/vue/upload/preview/${route.params.id}${window.location.search}`);
    resetImportForm();
  },

  async newspaper({ data }) {
    data.value = await fetchJson("/api/vue/newspaper");
  },

  async newspaperArticle({ route, data }) {
    data.value = await fetchJson(`/api/vue/newspaper/${route.params.section}/${route.params.index}`);
  },
};

export async function loadBooklearnerRoute({ data, loadBooklearner }) {
  data.value = { ok: true };
  await loadBooklearner();
}

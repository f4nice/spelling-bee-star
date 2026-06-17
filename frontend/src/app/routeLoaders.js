import { fetchJson } from "./utils.js";
import { routeApiPaths } from "./routeApiPaths.js";

export const routeLoaders = {
  async home({ data }) {
    data.value = await fetchJson(routeApiPaths.home());
  },

  async lists({ data, setUploadOptionsFromCards }) {
    data.value = await fetchJson(routeApiPaths.lists());
    setUploadOptionsFromCards(data.value.cards);
  },

  async listDetail({ route, data }) {
    data.value = await fetchJson(routeApiPaths.listDetail(route));
  },

  async wrongWords({ data }) {
    data.value = await fetchJson(routeApiPaths.wrongWords());
  },

  async challengeDay({ route, data }) {
    data.value = await fetchJson(routeApiPaths.challengeDay(route));
  },

  async wordDetail({ route, data, setWordEdit }) {
    data.value = await fetchJson(routeApiPaths.wordDetail(route));
    setWordEdit(data.value.word);
  },

  async upload({ data, loadUploadOptions }) {
    await loadUploadOptions();
    data.value = { ok: true };
  },

  async preview({ route, data, resetImportForm }) {
    data.value = await fetchJson(routeApiPaths.preview(route));
    resetImportForm();
  },

  async newspaper({ data }) {
    data.value = await fetchJson(routeApiPaths.newspaper());
  },

  async newspaperArticle({ route, data }) {
    data.value = await fetchJson(routeApiPaths.newspaperArticle(route));
  },
};

export async function loadBooklearnerRoute({ data, loadBooklearner }) {
  data.value = { ok: true };
  await loadBooklearner();
}

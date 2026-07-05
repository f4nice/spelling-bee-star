import { fetchJson } from "../utils.js";
import { routeApiPaths } from "../routeApiPaths.js";

export const coreRouteLoaders = {
  async home({ data }) {
    data.value = await fetchJson(routeApiPaths.home());
  },

  async growth({ data }) {
    data.value = await fetchJson(routeApiPaths.growth());
  },

  async spb({ route, data }) {
    data.value = await fetchJson(routeApiPaths.spb(route));
  },

  async challengeDay({ route, data }) {
    data.value = await fetchJson(routeApiPaths.challengeDay(route));
  },

  async wordDetail({ route, data, setWordEdit }) {
    data.value = await fetchJson(routeApiPaths.wordDetail(route));
    setWordEdit(data.value.word);
  },
};

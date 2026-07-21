import { fetchJson } from "../utils.js";
import { routeApiPaths } from "../routeApiPaths.js";

export const coreRouteLoaders = {
  async home({ data }) {
    data.value = await fetchJson(routeApiPaths.home());
  },

  async growth({ data }) {
    data.value = await fetchJson(routeApiPaths.growth());
  },

  async catWorld({ data }) {
    data.value = await fetchJson(routeApiPaths.catWorld(), { skipCache: true });
  },

  async essays({ data }) {
    data.value = await fetchJson(routeApiPaths.essays(), { skipCache: true });
  },

  async admin({ data }) {
    data.value = await fetchJson(routeApiPaths.admin(), { skipCache: true });
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

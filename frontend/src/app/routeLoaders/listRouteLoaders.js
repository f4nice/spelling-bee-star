import { fetchJson } from "../utils.js";
import { routeApiPaths } from "../routeApiPaths.js";

export const listRouteLoaders = {
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
};

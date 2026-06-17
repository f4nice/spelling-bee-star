import { fetchJson } from "../utils.js";
import { routeApiPaths } from "../routeApiPaths.js";

export const newspaperRouteLoaders = {
  async newspaper({ data }) {
    data.value = await fetchJson(routeApiPaths.newspaper());
  },

  async newspaperArticle({ route, data }) {
    data.value = await fetchJson(routeApiPaths.newspaperArticle(route));
  },
};

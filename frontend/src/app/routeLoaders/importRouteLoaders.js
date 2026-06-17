import { fetchJson } from "../utils.js";
import { routeApiPaths } from "../routeApiPaths.js";

export const importRouteLoaders = {
  async upload({ data, loadUploadOptions }) {
    await loadUploadOptions();
    data.value = { ok: true };
  },

  async preview({ route, data, resetImportForm }) {
    data.value = await fetchJson(routeApiPaths.preview(route));
    resetImportForm();
  },
};

import { coreRouteLoaders } from "./routeLoaders/coreRouteLoaders.js";
import { importRouteLoaders } from "./routeLoaders/importRouteLoaders.js";
import { listRouteLoaders } from "./routeLoaders/listRouteLoaders.js";
import { newspaperRouteLoaders } from "./routeLoaders/newspaperRouteLoaders.js";

export const routeLoaders = {
  ...coreRouteLoaders,
  ...listRouteLoaders,
  ...importRouteLoaders,
  ...newspaperRouteLoaders,
};

export async function loadBooklearnerRoute({ data, loadBooklearner }) {
  data.value = { ok: true };
  await loadBooklearner();
}

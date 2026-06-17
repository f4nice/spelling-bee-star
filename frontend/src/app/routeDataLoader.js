import { loadBooklearnerRoute, routeLoaders } from "./routeLoaders.js";

export async function loadRouteData({
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

  const context = {
    route,
    data,
    setWordEdit,
    setUploadOptionsFromCards,
    loadUploadOptions,
    resetImportForm,
    loadBooklearner,
  };
  const loadRoute = routeLoaders[route.name];
  if (loadRoute) await loadRoute(context);
  if (route.name.startsWith("booklearner")) await loadBooklearnerRoute(context);
}

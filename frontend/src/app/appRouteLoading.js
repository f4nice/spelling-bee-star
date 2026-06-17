import { loadRouteData } from "./routeDataLoader.js";

export async function loadCurrentAppRoute({ route, data, loading, error, refreshShellContext, getRouteLoaders }) {
  if (route.value.name === "challenge") {
    data.value = null;
    error.value = "";
    refreshShellContext();
    return;
  }

  loading.value = true;
  error.value = "";
  try {
    await loadRouteData({
      route: route.value,
      data,
      ...getRouteLoaders(),
    });
  } catch (err) {
    error.value = err.message || "页面数据加载失败";
  } finally {
    loading.value = false;
    refreshShellContext();
  }
}

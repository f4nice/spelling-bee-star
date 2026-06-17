import { ref } from "vue";
import { loadRouteData } from "./routeDataLoader.js";
import { parseRoute } from "./router.js";

export function useAppRouteController({ data, refreshShellContext, getRouteLoaders }) {
  const route = ref(parseRoute());
  const loading = ref(false);
  const error = ref("");

  function setError(message) {
    error.value = message;
  }

  function go(path) {
    history.pushState(null, "", path);
    route.value = parseRoute();
    loadRoute();
  }

  function onPopState() {
    route.value = parseRoute();
    loadRoute();
  }

  async function loadRoute() {
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

  return {
    route,
    loading,
    error,
    setError,
    go,
    loadRoute,
    onPopState,
  };
}

import { ref } from "vue";
import { loadCurrentAppRoute } from "./appRouteLoading.js";
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
    await loadCurrentAppRoute({ route, data, loading, error, refreshShellContext, getRouteLoaders });
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

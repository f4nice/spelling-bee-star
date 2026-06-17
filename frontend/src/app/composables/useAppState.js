import { computed, ref } from "vue";
import { useAppRouteController } from "../appRouteController.js";
import { useAppWindowEvents } from "./useAppWindowEvents.js";
import { useAppFeatureModules } from "./useAppFeatureModules.js";
import { usePageContext } from "../pageContext.js";
import { routeTitle as titleForRoute } from "../routeTitles.js";
import { useShellContext } from "../shellContext.js";

export function useAppState() {
  const data = ref(null);
  const { shellContext, refreshShellContext } = useShellContext();
  let featureModules;
  const { route, loading, error, setError, go, loadRoute, onPopState } = useAppRouteController({
    data,
    refreshShellContext,
    getRouteLoaders: () => featureModules.routeLoaders,
  });

  const routeTitle = computed(() => titleForRoute(route.value, data.value));
  featureModules = useAppFeatureModules({ data, route, go, loadRoute, setError });
  const { importPreview, wordDetail, booklearner, listTools } = featureModules;

  const pageContext = usePageContext({ route, data, go, importPreview, wordDetail, booklearner, listTools });

  function onKeydown(event) {
    featureModules.handleWordKeydown(event, route.value);
  }

  useAppWindowEvents({ onPopState, onKeydown, loadRoute });

  return {
    shellContext,
    route,
    routeTitle,
    loading,
    error,
    go,
    pageContext,
  };
}

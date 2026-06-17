import { computed, ref } from "vue";
import { useAppRouteController } from "../appRouteController.js";
import { useAppWindowEvents } from "./useAppWindowEvents.js";
import { useBooklearner } from "./useBooklearner.js";
import { useImportPreview } from "./useImportPreview.js";
import { useListTools } from "./useListTools.js";
import { useWordDetail } from "./useWordDetail.js";
import { usePageContext } from "../pageContext.js";
import { routeTitle as titleForRoute } from "../routeTitles.js";
import { useShellContext } from "../shellContext.js";

export function useAppState() {
  const data = ref(null);
  const { shellContext, refreshShellContext } = useShellContext();
  const { route, loading, error, setError, go, loadRoute, onPopState } = useAppRouteController({
    data,
    refreshShellContext,
    getRouteLoaders: () => ({
      resetWordTools,
      setWordEdit,
      setUploadOptionsFromCards,
      loadUploadOptions,
      resetImportForm,
      loadBooklearner,
    }),
  });

  const routeTitle = computed(() => titleForRoute(route.value, data.value));

  const importPreview = useImportPreview({ data, route, go, loadRoute, setError });
  const { resetImportForm } = importPreview;

  const wordDetail = useWordDetail({ data, loadRoute });
  const { resetWordTools, setWordEdit, handleWordKeydown } = wordDetail;

  const booklearner = useBooklearner({ route, go });
  const { loadBooklearner } = booklearner;

  const listTools = useListTools({ data, go, loadRoute });
  const { setUploadOptionsFromCards, loadUploadOptions } = listTools;

  const pageContext = usePageContext({ route, data, go, importPreview, wordDetail, booklearner, listTools });

  function onKeydown(event) {
    handleWordKeydown(event, route.value);
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

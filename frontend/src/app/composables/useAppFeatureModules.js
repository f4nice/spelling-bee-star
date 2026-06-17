import { buildAppFeatureRouteLoaders } from "../appFeatureRouteLoaders.js";
import { useBooklearner } from "./useBooklearner.js";
import { useImportPreview } from "./useImportPreview.js";
import { useListTools } from "./useListTools.js";
import { useWordDetail } from "./useWordDetail.js";

export function useAppFeatureModules({ data, route, go, loadRoute, setError }) {
  const importPreview = useImportPreview({ data, route, go, loadRoute, setError });
  const wordDetail = useWordDetail({ data, loadRoute });
  const booklearner = useBooklearner({ route, go });
  const listTools = useListTools({ data, go, loadRoute });

  return {
    importPreview,
    wordDetail,
    booklearner,
    listTools,
    handleWordKeydown: wordDetail.handleWordKeydown,
    routeLoaders: buildAppFeatureRouteLoaders({ wordDetail, listTools, importPreview, booklearner }),
  };
}

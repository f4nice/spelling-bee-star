import { useImportPreviewForm } from "./useImportPreviewForm.js";
import { useImportPreviewSubmit } from "./useImportPreviewSubmit.js";

export function useImportPreview({ data, route, go, loadRoute, setError }) {
  const formTools = useImportPreviewForm({ data, route, loadRoute });
  const submitTools = useImportPreviewSubmit({
    data,
    route,
    go,
    setError,
    importForm: formTools.importForm,
  });

  return {
    ...formTools,
    ...submitTools,
  };
}

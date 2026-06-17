import { useBatchImageTools } from "./useBatchImageTools.js";
import { useListDetailTools } from "./useListDetailTools.js";
import { useListUploadTools } from "./useListUploadTools.js";

export function useListTools({ data, go, loadRoute }) {
  const uploadTools = useListUploadTools({ go });
  const batchImageTools = useBatchImageTools({ loadRoute });
  const listDetailTools = useListDetailTools({ data, go, loadRoute });

  return {
    ...uploadTools,
    ...batchImageTools,
    ...listDetailTools,
  };
}

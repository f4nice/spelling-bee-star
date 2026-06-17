import { ref } from "vue";
import { fetchJson } from "../utils.js";
import { listApiPaths } from "../listApiPaths.js";
import { createBatchImageForm } from "../listForms.js";

export function useBatchImageTools({ loadRoute }) {
  const batchImageState = ref({ word_list_id: "", image_files: [], notice: "" });

  async function submitBatchImages() {
    if (!batchImageState.value.word_list_id || !batchImageState.value.image_files.length) return;
    const form = createBatchImageForm({
      wordListId: batchImageState.value.word_list_id,
      imageFiles: batchImageState.value.image_files,
    });
    const result = await fetchJson(listApiPaths.batchImages(), { method: "POST", body: form });
    batchImageState.value.notice = `已匹配 ${result.matched} 张，未匹配 ${result.unmatched} 张，失败 ${result.failed} 张`;
    await loadRoute();
  }

  return {
    batchImageState,
    submitBatchImages,
  };
}

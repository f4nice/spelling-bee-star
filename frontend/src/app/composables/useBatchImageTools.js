import { ref } from "vue";
import { fetchJson } from "../utils.js";

export function useBatchImageTools({ loadRoute }) {
  const batchImageState = ref({ word_list_id: "", image_files: [], notice: "" });

  async function submitBatchImages() {
    if (!batchImageState.value.word_list_id || !batchImageState.value.image_files.length) return;
    const form = new FormData();
    form.append("word_list_id", batchImageState.value.word_list_id);
    batchImageState.value.image_files.forEach((file) => form.append("image_files", file));
    const result = await fetchJson("/api/vue/lists/batch-images", { method: "POST", body: form });
    batchImageState.value.notice = `已匹配 ${result.matched} 张，未匹配 ${result.unmatched} 张，失败 ${result.failed} 张`;
    await loadRoute();
  }

  return {
    batchImageState,
    submitBatchImages,
  };
}

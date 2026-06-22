import { ref } from "vue";
import { fetchJson } from "../utils.js";
import { listApiPaths } from "../listApiPaths.js";
import { createBatchImageForm } from "../listForms.js";

export function useBatchImageTools({ loadRoute }) {
  const batchImageState = ref({ word_list_id: "", image_files: [], notice: "", isUploading: false });

  async function submitBatchImages() {
    if (batchImageState.value.isUploading) return;
    if (!batchImageState.value.word_list_id) {
      batchImageState.value.notice = "请先选择单词表。";
      return;
    }
    if (!batchImageState.value.image_files.length) {
      batchImageState.value.notice = "请先选择图片文件或文件夹。";
      return;
    }
    batchImageState.value.notice = "";
    batchImageState.value.isUploading = true;
    try {
      const form = createBatchImageForm({
        wordListId: batchImageState.value.word_list_id,
        imageFiles: batchImageState.value.image_files,
      });
      const result = await fetchJson(listApiPaths.batchImages(), { method: "POST", body: form });
      batchImageState.value.notice = `已匹配 ${result.matched} 张，未匹配 ${result.unmatched} 张，失败 ${result.failed} 张`;
      await loadRoute();
    } catch (error) {
      batchImageState.value.notice = error.message || "图片上传失败，请稍后重试。";
    } finally {
      batchImageState.value.isUploading = false;
    }
  }

  return {
    batchImageState,
    submitBatchImages,
  };
}

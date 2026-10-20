import { ref } from "vue";
import { fetchJson } from "../utils.js";
import { listApiPaths } from "../listApiPaths.js";
import { createBatchImageForm } from "../listForms.js";
import { prepareImageUpload, splitImageFiles } from "../imageUpload.js";

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
      const preparedFiles = [];
      for (const file of batchImageState.value.image_files) {
        preparedFiles.push(await prepareImageUpload(file));
      }
      const batches = splitImageFiles(preparedFiles);
      const totals = { matched: 0, unmatched: 0, failed: 0 };
      for (let index = 0; index < batches.length; index += 1) {
        batchImageState.value.notice = `正在上传第 ${index + 1} / ${batches.length} 批图片...`;
        const form = createBatchImageForm({
          wordListId: batchImageState.value.word_list_id,
          imageFiles: batches[index],
        });
        const result = await fetchJson(listApiPaths.batchImages(), { method: "POST", body: form });
        totals.matched += Number(result.matched || 0);
        totals.unmatched += Number(result.unmatched || 0);
        totals.failed += Number(result.failed || 0);
      }
      batchImageState.value.notice = `已匹配 ${totals.matched} 张，未匹配 ${totals.unmatched} 张，失败 ${totals.failed} 张`;
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

import { ref } from "vue";
import { fetchJson } from "../utils.js";
import { listApiPaths } from "../listApiPaths.js";
import { createListUploadForm } from "../listForms.js";

export function useListUploadTools({ go }) {
  const uploadOptions = ref({ word_lists: [] });
  const uploadForm = ref({ word_list_id: "", word_list_name: "", file: null, notice: "", isUploading: false });

  function setUploadOptionsFromCards(cards = []) {
    uploadOptions.value = { word_lists: cards.map((card) => card.list) };
  }

  async function loadUploadOptions() {
    uploadOptions.value = await fetchJson(listApiPaths.uploadOptions());
  }

  async function submitUpload() {
    if (uploadForm.value.isUploading) return;
    if (!uploadForm.value.file) {
      uploadForm.value.notice = "请先选择 Excel 文件。";
      return;
    }
    uploadForm.value.notice = "";
    uploadForm.value.isUploading = true;
    try {
      const form = createListUploadForm({
        file: uploadForm.value.file,
        wordListId: uploadForm.value.word_list_id,
        wordListName: uploadForm.value.word_list_name,
      });
      const result = await fetchJson(listApiPaths.upload(), { method: "POST", body: form });
      go(`/upload/preview/${result.preview_id}`);
    } catch (error) {
      uploadForm.value.notice = error.message || "上传失败，请稍后重试。";
    } finally {
      uploadForm.value.isUploading = false;
    }
  }

  return {
    uploadOptions,
    uploadForm,
    setUploadOptionsFromCards,
    loadUploadOptions,
    submitUpload,
  };
}

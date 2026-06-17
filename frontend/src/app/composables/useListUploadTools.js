import { ref } from "vue";
import { fetchJson } from "../utils.js";

export function useListUploadTools({ go }) {
  const uploadOptions = ref({ word_lists: [] });
  const uploadForm = ref({ word_list_id: "", word_list_name: "", file: null });

  function setUploadOptionsFromCards(cards = []) {
    uploadOptions.value = { word_lists: cards.map((card) => card.list) };
  }

  async function loadUploadOptions() {
    uploadOptions.value = await fetchJson("/api/vue/upload/options");
  }

  async function submitUpload() {
    if (!uploadForm.value.file) return;
    const form = new FormData();
    form.append("file", uploadForm.value.file);
    form.append("word_list_id", uploadForm.value.word_list_id || "");
    form.append("word_list_name", uploadForm.value.word_list_name || "");
    const result = await fetchJson("/api/vue/upload", { method: "POST", body: form });
    go(`/upload/preview/${result.preview_id}`);
  }

  return {
    uploadOptions,
    uploadForm,
    setUploadOptionsFromCards,
    loadUploadOptions,
    submitUpload,
  };
}

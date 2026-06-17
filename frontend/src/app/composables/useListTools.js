import { ref } from "vue";
import { fetchJson } from "../utils.js";

export function useListTools({ data, go, loadRoute }) {
  const uploadOptions = ref({ word_lists: [] });
  const uploadForm = ref({ word_list_id: "", word_list_name: "", file: null });
  const batchImageState = ref({ word_list_id: "", image_files: [], notice: "" });
  const deleteListState = ref({ password: "", notice: "" });

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

  async function submitBatchImages() {
    if (!batchImageState.value.word_list_id || !batchImageState.value.image_files.length) return;
    const form = new FormData();
    form.append("word_list_id", batchImageState.value.word_list_id);
    batchImageState.value.image_files.forEach((file) => form.append("image_files", file));
    const result = await fetchJson("/api/vue/lists/batch-images", { method: "POST", body: form });
    batchImageState.value.notice = `已匹配 ${result.matched} 张，未匹配 ${result.unmatched} 张，失败 ${result.failed} 张`;
    await loadRoute();
  }

  async function renameList() {
    const form = new FormData();
    form.append("name", data.value.word_list.name);
    await fetchJson(`/api/vue/lists/${data.value.word_list.id}/rename`, {
      method: "POST",
      body: form,
      headers: { "x-requested-with": "fetch" },
    });
  }

  async function deleteList() {
    if (!data.value?.word_list?.id || !deleteListState.value.password) return;
    const form = new FormData();
    form.append("password", deleteListState.value.password);
    try {
      await fetchJson(`/api/vue/lists/${data.value.word_list.id}/delete`, { method: "POST", body: form });
      deleteListState.value = { password: "", notice: "" };
      go("/lists");
    } catch (error) {
      deleteListState.value.notice = error.message || "删除失败";
    }
  }

  async function syncListImages() {
    const job = await fetchJson(`/api/vue/lists/${data.value.word_list.id}/sync-images/start`, { method: "POST" });
    data.value.sync_job = job;
    const timer = window.setInterval(async () => {
      const next = await fetchJson(`/api/vue/lists/${data.value.word_list.id}/sync-images/${job.id}`);
      data.value.sync_job = next;
      if (["done", "failed"].includes(next.status)) {
        window.clearInterval(timer);
        await loadRoute();
      }
    }, 1200);
  }

  return {
    uploadOptions,
    uploadForm,
    batchImageState,
    deleteListState,
    setUploadOptionsFromCards,
    loadUploadOptions,
    submitUpload,
    submitBatchImages,
    renameList,
    deleteList,
    syncListImages,
  };
}

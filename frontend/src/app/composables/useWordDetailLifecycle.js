import { fetchJson } from "../utils.js";

export function useWordDetailLifecycle({ data, loadRoute, resetImageTools, resetAudioTools }) {
  function resetWordTools() {
    resetImageTools();
    resetAudioTools();
  }

  async function refreshWord() {
    const form = new FormData();
    form.append("edit_token", "1");
    await fetchJson(`/api/vue/words/${data.value.word.id}/refresh`, { method: "POST", body: form });
    await loadRoute();
  }

  return {
    resetWordTools,
    refreshWord,
  };
}

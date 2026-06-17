import { fetchJson } from "../utils.js";
import { wordApiPaths } from "../wordApiPaths.js";

export function useWordDetailLifecycle({ data, loadRoute, resetImageTools, resetAudioTools }) {
  function resetWordTools() {
    resetImageTools();
    resetAudioTools();
  }

  async function refreshWord() {
    const form = new FormData();
    form.append("edit_token", "1");
    await fetchJson(wordApiPaths.refresh(data.value.word.id), { method: "POST", body: form });
    await loadRoute();
  }

  return {
    resetWordTools,
    refreshWord,
  };
}
